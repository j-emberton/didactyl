import argparse
import collections.abc
import re
import shutil
from pathlib import Path

from didactyl._course import find_course_root, load_course
from didactyl._models import Course, Exercise, Progress, ScaffoldResult
from didactyl._progress import (
    current_exercise,
    exercise_digest,
    is_complete,
    load_progress,
    record_result,
    save_progress,
    select_exercise,
)
from didactyl._runner import check_all, run_exercise, verify_course
from didactyl.scaffold._scaffold import scaffold_exercise, scaffold_tutorial
from didactyl._tui import run_tui
from didactyl._version import __version__


def _slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug or "tutorial"


def _print_scaffold(result: ScaffoldResult, root: Path) -> None:
    for label, paths in (
        ("created", result.written),
        ("updated", result.updated),
        ("skipped", result.skipped),
    ):
        for path in paths:
            try:
                display = path.relative_to(root)
            except ValueError:
                display = path
            print(f"{label:>7}  {display}")


def _resolve_exercise(course: Course, name: str | None) -> Exercise | None:
    progress = load_progress(course)
    if name is not None:
        try:
            return course.exercise(name)
        except KeyError as error:
            raise SystemExit(str(error)) from error
    return current_exercise(course, progress)


def _command_init(arguments: argparse.Namespace) -> int:
    root = Path(arguments.path).expanduser().resolve()
    root.mkdir(parents=True, exist_ok=True)
    title = arguments.title or root.name.replace("-", " ").replace("_", " ").title()
    tutorial_id = arguments.tutorial_id or _slugify(title)
    result = scaffold_tutorial(
        root,
        title=title,
        tutorial_id=tutorial_id,
        force=arguments.force,
        include_vscode=not arguments.no_vscode,
        include_test=not arguments.no_test,
    )
    _print_scaffold(result, root)

    if arguments.example:
        exercise_result = scaffold_exercise(
            root,
            name="intro-example",
            title="Complete the generated example",
            section="00_intro",
            force=arguments.force,
        )
        _print_scaffold(exercise_result, root)

    print("\nNext steps:")
    print('  uv run tutorial-engine add-exercise <name> --title "Exercise title"')
    print("  uv run tutorial-engine verify")
    print("  uv run tutorial-engine")
    return 0


def _command_add_exercise(arguments: argparse.Namespace) -> int:
    root = find_course_root()
    result = scaffold_exercise(
        root,
        name=arguments.name,
        title=arguments.title or arguments.name.replace("-", " ").replace("_", " ").title(),
        section=arguments.section,
        timeout=arguments.timeout,
        force=arguments.force,
    )
    _print_scaffold(result, root)
    return 0


def _command_list(course: Course) -> int:
    progress = load_progress(course)
    print(course.title)
    if not course.exercises:
        print("No exercises have been added yet.")
        return 0
    current = current_exercise(course, progress)
    for exercise in course.exercises:
        marker = "✓" if is_complete(exercise, progress) else ("▶" if exercise == current else "·")
        print(f"{marker} {exercise.name:<24} {exercise.title}")
    return 0


def _command_run(course: Course, name: str | None) -> int:
    progress = load_progress(course)
    exercise = course.exercise(name) if name is not None else current_exercise(course, progress)
    if exercise is None:
        print(course.completion_message.strip() or "All exercises are complete.")
        return 0

    progress = select_exercise(course, progress, exercise)
    result = run_exercise(course, exercise)
    record_result(course, progress, exercise, passed=result.passed)
    print(result.output)
    print(f"\n{'✓' if result.passed else '✗'} {exercise.name}")
    return 0 if result.passed else 1


def _command_hint(course: Course, name: str | None) -> int:
    exercise = _resolve_exercise(course, name)
    if exercise is None:
        print("All exercises are complete.")
        return 0
    print(exercise.hint.strip() or "No hint has been provided.")
    return 0


def _command_solution(course: Course, name: str | None) -> int:
    exercise = _resolve_exercise(course, name)
    if exercise is None:
        print("All exercises are complete.")
        return 0
    if exercise.solution is None:
        print("No reference solution has been provided.")
        return 0
    print(exercise.solution.read_text(), end="")
    return 0


def _command_reset(course: Course, name: str | None) -> int:
    progress = load_progress(course)
    exercise = course.exercise(name) if name is not None else current_exercise(course, progress)
    if exercise is None:
        print("All exercises are complete. Supply an exercise name to reset one.")
        return 0
    shutil.copyfile(exercise.starter, exercise.path)
    completed = dict(progress.completed)
    completed.pop(exercise.name, None)
    updated = Progress(
        course_version=course.version,
        current=exercise.name,
        completed=completed,
    )
    save_progress(course, updated)
    print(f"Reset {exercise.name}.")
    return 0


def _command_check_all(course: Course) -> int:
    results = check_all(course)
    progress = load_progress(course)
    completed = dict(progress.completed)
    first_failed: str | None = None

    for result in results:
        marker = "✓" if result.passed else "✗"
        print(f"{marker} {result.exercise.name}")
        if result.passed:
            completed[result.exercise.name] = exercise_digest(result.exercise)
        else:
            completed.pop(result.exercise.name, None)
            first_failed = first_failed or result.exercise.name

    save_progress(
        course,
        Progress(
            course_version=course.version,
            current=first_failed,
            completed=completed,
        ),
    )
    return 0 if all(result.passed for result in results) else 1


def _command_verify(course: Course) -> int:
    report = verify_course(course)
    failed = False
    for warning in report.warnings:
        print(f"warning: {warning}")

    for item in report.items:
        print(f"{item.exercise.name}:")
        if item.starter_failed:
            print("  ✓ starter fails")
        else:
            print("  ✗ starter unexpectedly passes")
            failed = True

        if item.starter_failed_as_expected:
            print("  ✓ starter fails for the expected reason")
        else:
            print("  ✗ starter did not fail for the expected reason")
            if item.starter_output:
                print(item.starter_output)
            failed = True

        if item.solution_passed:
            print("  ✓ solution passes")
        else:
            print("  ✗ solution fails")
            if item.solution_output:
                print(item.solution_output)
            failed = True

    return 1 if failed else 0


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="tutorial-engine",
        description="Create and run repository-based Python tutorials.",
    )
    parser.add_argument("--version", action="version", version=f"tutorial-engine {__version__}")
    subparsers = parser.add_subparsers(dest="command")

    init_parser = subparsers.add_parser("init", help="Add tutorial scaffolding to a repository.")
    init_parser.add_argument("path", nargs="?", default=".")
    init_parser.add_argument("--title")
    init_parser.add_argument("--id", dest="tutorial_id")
    init_parser.add_argument("--force", action="store_true")
    init_parser.add_argument("--no-vscode", action="store_true")
    init_parser.add_argument("--no-test", action="store_true")
    init_parser.add_argument("--example", action="store_true")

    add_parser = subparsers.add_parser("add-exercise", help="Scaffold one exercise.")
    add_parser.add_argument("name")
    add_parser.add_argument("--title")
    add_parser.add_argument("--section", default="00_intro")
    add_parser.add_argument("--timeout", type=float, default=20.0)
    add_parser.add_argument("--force", action="store_true")

    subparsers.add_parser("list", help="List exercises and learner status.")

    run_parser = subparsers.add_parser("run", help="Run one exercise once.")
    run_parser.add_argument("name", nargs="?")

    hint_parser = subparsers.add_parser("hint", help="Show an exercise hint.")
    hint_parser.add_argument("name", nargs="?")

    solution_parser = subparsers.add_parser("solution", help="Show a reference solution.")
    solution_parser.add_argument("name", nargs="?")

    reset_parser = subparsers.add_parser("reset", help="Restore an exercise starter.")
    reset_parser.add_argument("name", nargs="?")

    subparsers.add_parser("check-all", help="Check all learner exercise files.")
    subparsers.add_parser("verify", help="Verify course starters, checks and solutions.")
    subparsers.add_parser("tui", help="Open the interactive terminal interface.")
    return parser


def _run_tui(course: Course) -> int:
    run_tui(course)
    return 0


def _dispatch(
    parser: argparse.ArgumentParser,
    command: str,
    handlers: dict[str, collections.abc.Callable[[], int]],
) -> int:
    try:
        handler = handlers[command]
    except KeyError:
        parser.error(f"Unknown command: {command}")

    return handler()


def _run_tui(course: Course) -> int:
    run_tui(course)
    return 0


def _dispatch(
    parser: argparse.ArgumentParser,
    command: str,
    handlers: dict[str, collections.abc.Callable[[], int]],
) -> int:
    try:
        handler = handlers[command]
    except KeyError:
        parser.error(f"Unknown command: {command}")

    return handler()


def course_main(argv: collections.abc.Sequence[str] | None = None) -> int:
    """Run Tutorial Engine's CLI and return an exit code."""
    parser = _build_parser()
    arguments = parser.parse_args(argv)
    command = arguments.command or "tui"

    setup_handlers: dict[str, collections.abc.Callable[[], int]] = {
        "init": lambda: _command_init(arguments),
        "add-exercise": lambda: _command_add_exercise(arguments),
    }

    if command in setup_handlers:
        return _dispatch(parser, command, setup_handlers)

    try:
        course = load_course()
    except (FileNotFoundError, ValueError) as error:
        parser.error(str(error))

    course_handlers: dict[str, collections.abc.Callable[[], int]] = {
        "list": lambda: _command_list(course),
        "run": lambda: _command_run(course, arguments.name),
        "hint": lambda: _command_hint(course, arguments.name),
        "solution": lambda: _command_solution(course, arguments.name),
        "reset": lambda: _command_reset(course, arguments.name),
        "check-all": lambda: _command_check_all(course),
        "verify": lambda: _command_verify(course),
        "tui": lambda: _run_tui(course),
    }

    return _dispatch(parser, command, course_handlers)


def main() -> None:
    """Console-script entry point."""
    raise SystemExit(course_main())
