from __future__ import annotations

import curses
import queue
import shutil
import textwrap
import threading
import typing
from concurrent.futures import CancelledError, Future, ThreadPoolExecutor
from pathlib import Path

from watchfiles import watch

from didactyl._models import Course, Exercise, ExerciseResult
from didactyl._progress import (
    current_exercise,
    is_complete,
    load_progress,
    record_result,
    select_exercise,
)
from didactyl._runner import check_all, run_exercise

if typing.TYPE_CHECKING:
    from collections.abc import Callable

    from watchfiles import Change


_ESCAPE_KEY = 27
_ENTER_KEYS = (10, 13)
_WATCH_ERROR_PREFIX = "watch-error:"


def _relative(course: Course, path: Path) -> str:
    try:
        return str(path.relative_to(course.root))
    except ValueError:
        return str(path)


def run_tui(course: Course) -> None:
    """Run the full-screen tutorial interface."""

    def wrapped(screen: curses.window) -> None:
        _TutorialTui(course, screen).run()

    curses.wrapper(wrapped)


class _TutorialTui:
    def __init__(self, course: Course, screen: curses.window) -> None:
        self.course = course
        self.screen = screen
        self.progress = load_progress(course)
        current = current_exercise(course, self.progress)
        self.selected = course.exercises.index(current) if current in course.exercises else 0
        self.output = course.welcome_message.strip() or "Select an exercise and press Enter."
        self.status = "Ready"
        self.events: queue.Queue[str] = queue.Queue()
        self.stop_event = threading.Event()
        self.executor = ThreadPoolExecutor(
            max_workers=1,
            thread_name_prefix="tutorial-check",
        )
        self.future: Future[ExerciseResult | tuple[ExerciseResult, ...]] | None = None
        self.future_kind: typing.Literal["exercise", "all"] | None = None
        self.watcher: threading.Thread | None = None

    def run(self) -> None:
        self._configure_terminal()
        self._start_watcher()
        current = current_exercise(self.course, self.progress)
        if current is not None:
            self._schedule_exercise(current)

        try:
            while True:
                self._poll_background_work()
                self._draw()
                key = self.screen.getch()
                if key == -1:
                    curses.napms(50)
                    continue
                if self._handle_key(key):
                    return
        finally:
            self.stop_event.set()
            self.executor.shutdown(wait=False, cancel_futures=True)
            if self.watcher is not None:
                self.watcher.join(timeout=1)

    def _configure_terminal(self) -> None:
        enabled = True
        self.screen.keypad(enabled)
        self.screen.nodelay(enabled)
        curses.curs_set(0)
        if curses.has_colors():
            curses.start_color()
            curses.use_default_colors()
            curses.init_pair(1, curses.COLOR_GREEN, -1)
            curses.init_pair(2, curses.COLOR_RED, -1)
            curses.init_pair(3, curses.COLOR_CYAN, -1)
            curses.init_pair(4, curses.COLOR_YELLOW, -1)

    def _start_watcher(self) -> None:
        exercises_root = self.course.root / "tutorial" / "exercises"
        if not exercises_root.exists():
            return

        self.watcher = threading.Thread(
            target=self._watch_files,
            daemon=True,
        )
        self.watcher.start()

    def _watch_files(self) -> None:
        exercises_root = self.course.root / "tutorial" / "exercises"
        try:
            for changes in watch(exercises_root, stop_event=self.stop_event):
                self._handle_file_changes(changes)
        except (OSError, RuntimeError) as error:  # pragma: no cover - environment dependent
            self.events.put(f"{_WATCH_ERROR_PREFIX}{error}")

    def _handle_file_changes(self, changes: set[tuple[Change, str]]) -> None:
        current = current_exercise(self.course, self.progress)
        if current is None:
            return

        current_path = current.path.resolve()
        if any(Path(changed).resolve() == current_path for _, changed in changes):
            self.events.put("changed")

    def _schedule_exercise(self, exercise: Exercise) -> None:
        if self._check_in_progress():
            return

        self.status = f"Checking {exercise.name}…"
        self.future_kind = "exercise"
        self.future = self.executor.submit(run_exercise, self.course, exercise)

    def _schedule_all(self) -> None:
        if self._check_in_progress():
            return

        self.status = "Checking all exercises…"
        self.future_kind = "all"
        self.future = self.executor.submit(check_all, self.course)

    def _check_in_progress(self) -> bool:
        return self.future is not None and not self.future.done()

    def _poll_background_work(self) -> None:
        self._poll_events()
        self._poll_future()

    def _poll_events(self) -> None:
        while True:
            try:
                event = self.events.get_nowait()
            except queue.Empty:
                return

            self._handle_event(event)

    def _handle_event(self, event: str) -> None:
        if event == "changed":
            self._schedule_current_exercise()
            return

        if event.startswith(_WATCH_ERROR_PREFIX):
            self.status = event.removeprefix(_WATCH_ERROR_PREFIX)

    def _schedule_current_exercise(self) -> None:
        current = current_exercise(self.course, self.progress)
        if current is not None:
            self._schedule_exercise(current)

    def _poll_future(self) -> None:
        future = self.future
        if future is None or not future.done():
            return

        future_kind = self.future_kind
        self._clear_future()

        try:
            error = future.exception()
        except CancelledError:
            self.status = "Check cancelled"
            return

        if error is not None:
            self._show_checker_error(error)
            return

        self._handle_future_value(future_kind, future.result())

    def _handle_future_value(
        self,
        future_kind: typing.Literal["exercise", "all"] | None,
        value: ExerciseResult | tuple[ExerciseResult, ...],
    ) -> None:
        if future_kind == "exercise":
            self._handle_exercise_result(value)
            return

        if future_kind == "all":
            self._handle_all_results(value)
            return

        self._show_unexpected_result("a known check type", future_kind)

    def _handle_exercise_result(
        self,
        value: ExerciseResult | tuple[ExerciseResult, ...],
    ) -> None:
        if not isinstance(value, ExerciseResult):
            self._show_unexpected_result("ExerciseResult", value)
            return

        self.progress = record_result(
            self.course,
            self.progress,
            value.exercise,
            passed=value.passed,
        )
        self.status = "Passed" if value.passed else "Incomplete"
        self.output = value.output or self._default_result_output(value)
        self._advance_after_result(value)

    def _default_result_output(self, result: ExerciseResult) -> str:
        marker = "✓" if result.passed else "✗"
        outcome = "completed" if result.passed else "is incomplete"
        return f"{marker} {result.exercise.name} {outcome}"

    def _advance_after_result(self, result: ExerciseResult) -> None:
        current = current_exercise(self.course, self.progress)
        if current is None:
            if result.passed:
                self.output = self.course.completion_message.strip() or "All exercises complete."
            return

        self.selected = self.course.exercises.index(current)
        if result.passed:
            self._schedule_exercise(current)

    def _handle_all_results(
        self,
        value: ExerciseResult | tuple[ExerciseResult, ...],
    ) -> None:
        if not isinstance(value, tuple):
            self._show_unexpected_result("tuple[ExerciseResult, ...]", value)
            return

        progress = self.progress
        lines: list[str] = []
        for result in value:
            if not isinstance(result, ExerciseResult):
                self._show_unexpected_result("ExerciseResult", result)
                return

            progress = record_result(
                self.course,
                progress,
                result.exercise,
                passed=result.passed,
            )
            marker = "✓" if result.passed else "✗"
            lines.append(f"{marker} {result.exercise.name}")

        self.progress = progress
        self.output = "\n".join(lines) or "The tutorial contains no exercises."
        self.status = "Course check complete"

    def _show_checker_error(self, error: BaseException) -> None:
        self.output = f"Unexpected checker error:\n{error}"
        self.status = "Checker failed"

    def _show_unexpected_result(self, expected: str, value: object) -> None:
        received = type(value).__name__
        self.output = f"Expected {expected}, received {received}."
        self.status = "Checker failed"

    def _clear_future(self) -> None:
        self.future = None
        self.future_kind = None

    def _selected_exercise(self) -> Exercise | None:
        if not self.course.exercises:
            return None

        self.selected = max(0, min(self.selected, len(self.course.exercises) - 1))
        return self.course.exercises[self.selected]

    def _handle_key(self, key: int) -> bool:
        if key in {ord("q"), _ESCAPE_KEY}:
            return True

        handler = self._key_handlers().get(key)
        if handler is not None:
            handler()

        return False

    def _key_handlers(self) -> dict[int, Callable[[], None]]:
        return {
            curses.KEY_UP: self._select_previous,
            ord("k"): self._select_previous,
            curses.KEY_DOWN: self._select_next,
            ord("j"): self._select_next,
            curses.KEY_ENTER: self._open_selected,
            _ENTER_KEYS[0]: self._open_selected,
            _ENTER_KEYS[1]: self._open_selected,
            ord("r"): self._run_current,
            ord("h"): self._show_hint,
            ord("s"): self._show_solution,
            ord("x"): self._reset_selected,
            ord("c"): self._schedule_all,
        }

    def _select_previous(self) -> None:
        self.selected = max(0, self.selected - 1)

    def _select_next(self) -> None:
        final_index = max(0, len(self.course.exercises) - 1)
        self.selected = min(final_index, self.selected + 1)

    def _open_selected(self) -> None:
        exercise = self._selected_exercise()
        if exercise is None:
            return

        self.progress = select_exercise(self.course, self.progress, exercise)
        self._schedule_exercise(exercise)

    def _run_current(self) -> None:
        exercise = current_exercise(self.course, self.progress)
        exercise = exercise or self._selected_exercise()
        if exercise is not None:
            self._schedule_exercise(exercise)

    def _show_hint(self) -> None:
        exercise = self._selected_exercise()
        if exercise is None:
            return

        self.output = exercise.hint.strip() or "No hint has been provided."
        self.status = f"Hint: {exercise.name}"

    def _show_solution(self) -> None:
        exercise = self._selected_exercise()
        if exercise is None:
            return

        if exercise.solution is None:
            self.output = "No reference solution has been provided."
        else:
            self.output = exercise.solution.read_text()

        self.status = f"Solution: {exercise.name}"

    def _reset_selected(self) -> None:
        exercise = self._selected_exercise()
        if exercise is None:
            return

        shutil.copyfile(exercise.starter, exercise.path)
        self.progress = select_exercise(self.course, self.progress, exercise)
        self.status = f"Reset {exercise.name}"
        self._schedule_exercise(exercise)

    def _draw(self) -> None:
        self.screen.erase()
        height, width = self.screen.getmaxyx()
        height_upper_bound = 8
        width_upper_bound = 50
        if height < height_upper_bound or width < width_upper_bound:
            self._safe_add(0, 0, "Terminal too small. Resize or press q to quit.")
            self.screen.refresh()
            return

        sidebar_width = min(42, max(28, width // 3))
        completed_count = sum(
            1 for exercise in self.course.exercises if is_complete(exercise, self.progress)
        )
        header = (
            f" {self.course.title}  "
            f"{completed_count}/{len(self.course.exercises)} complete  "
            f"[{self.status}] "
        )
        self._safe_add(0, 0, header[: width - 1], curses.A_BOLD)
        self._safe_add(1, sidebar_width, "│")

        available_rows = height - 4
        start = max(0, self.selected - available_rows // 2)
        end = min(len(self.course.exercises), start + available_rows)
        for row, index in enumerate(range(start, end), start=2):
            exercise = self.course.exercises[index]
            selected = index == self.selected
            complete = is_complete(exercise, self.progress)
            current = current_exercise(self.course, self.progress) == exercise
            marker = "✓" if complete else ("▶" if current else "·")
            text = f" {marker} {exercise.name}"
            attribute = curses.A_REVERSE if selected else 0
            if complete and curses.has_colors():
                attribute |= curses.color_pair(1)
            elif current and curses.has_colors():
                attribute |= curses.color_pair(3)
            self._safe_add(row, 0, text[: sidebar_width - 1], attribute)

        for row in range(1, height - 2):
            self._safe_add(row, sidebar_width, "│")

        exercise = self._selected_exercise()
        right_x = sidebar_width + 2
        right_width = width - right_x - 1
        if exercise is not None:
            self._safe_add(2, right_x, exercise.title[:right_width], curses.A_BOLD)
            self._safe_add(
                3,
                right_x,
                _relative(self.course, exercise.path)[:right_width],
            )
            output_start = 5
        else:
            self._safe_add(2, right_x, "No exercises yet", curses.A_BOLD)
            output_start = 4

        wrapped: list[str] = []
        for line in self.output.splitlines() or [""]:
            wrapped.extend(textwrap.wrap(line, width=max(10, right_width)) or [""])
        for offset, line in enumerate(wrapped[: max(0, height - output_start - 2)]):
            self._safe_add(output_start + offset, right_x, line[:right_width])

        footer = (
            " ↑/↓ select  Enter run  r rerun  h hint  s solution  x reset  c check all  q quit "
        )
        self._safe_add(height - 1, 0, footer[: width - 1], curses.A_REVERSE)
        self.screen.refresh()

    def _safe_add(
        self,
        row: int,
        column: int,
        text: str,
        attribute: int = 0,
    ) -> None:
        try:
            self.screen.addstr(row, column, text, attribute)
        except curses.error:
            pass
