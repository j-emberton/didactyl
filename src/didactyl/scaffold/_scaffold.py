from __future__ import annotations

import json
import re
import textwrap
import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import NotRequired, TypedDict, Unpack

from didactyl._course import COURSE_FILE
from didactyl._models import ScaffoldFile, ScaffoldPlan, ScaffoldResult

_NAME_PATTERN = re.compile(r"^[a-z0-9][a-z0-9_-]*$")
_GITIGNORE_MARKER = "# tutorial-engine state"


class _InvalidNameError(ValueError):
    """Raised when a scaffold identifier has an invalid format."""

    def __init__(self, field: str) -> None:
        message = (
            f"{field} must start with a lower-case letter or number and contain only "
            "lower-case letters, numbers, '-' and '_'."
        )
        super().__init__(message)


class _InvalidSectionError(ValueError):
    """Raised when an exercise section is not a valid relative path."""

    def __init__(self) -> None:
        message = "section must be a relative path without '.' or '..' components."
        super().__init__(message)


class _EmptyTitleError(ValueError):
    """Raised when a scaffold title is empty."""

    def __init__(self) -> None:
        message = "title must not be empty."
        super().__init__(message)


class _InvalidTimeoutError(ValueError):
    """Raised when an exercise timeout is not positive."""

    def __init__(self) -> None:
        message = "timeout must be positive."
        super().__init__(message)


class _MissingCourseFileError(FileNotFoundError):
    """Raised when an exercise is added outside a course repository."""

    def __init__(self, course_file: str) -> None:
        message = f"Missing {course_file}. Run `tutorial-engine init` first."
        super().__init__(message)


class _DuplicateExerciseError(ValueError):
    """Raised when an exercise name is already present in the course."""

    def __init__(self, name: str) -> None:
        message = f"Exercise {name!r} already exists."
        super().__init__(message)


class _TutorialScaffoldOptions(TypedDict):
    """Keyword options accepted by :func:`scaffold_tutorial`."""

    title: str
    tutorial_id: str
    force: NotRequired[bool]
    include_vscode: NotRequired[bool]
    include_test: NotRequired[bool]


class _ExerciseScaffoldOptions(TypedDict):
    """Keyword options accepted by :func:`scaffold_exercise`."""

    name: str
    title: str
    section: NotRequired[str]
    timeout: NotRequired[float]
    force: NotRequired[bool]


def _normalise(content: str) -> str:
    return textwrap.dedent(content).lstrip("\n").rstrip() + "\n"


def _validate_name(value: str, *, field: str) -> str:
    if not _NAME_PATTERN.fullmatch(value):
        raise _InvalidNameError(field)
    return value


def _validate_section(value: str) -> str:
    section = Path(value)
    if (
        section.is_absolute()
        or not section.parts
        or any(part in {"", ".", ".."} for part in section.parts)
    ):
        raise _InvalidSectionError
    for part in section.parts:
        _validate_name(part, field="section component")
    return section.as_posix()


def apply_scaffold(plan: ScaffoldPlan, *, force: bool = False) -> ScaffoldResult:
    """Apply a scaffold plan without overwriting existing files by default."""
    written: list[Path] = []
    updated: list[Path] = []
    skipped: list[Path] = []

    for scaffold_file in plan.files:
        path = scaffold_file.path
        path.parent.mkdir(parents=True, exist_ok=True)

        if scaffold_file.mode == "append_once":
            existing = path.read_text() if path.is_file() else ""
            marker = scaffold_file.marker or scaffold_file.content.strip()
            if marker in existing:
                skipped.append(path)
                continue
            separator = "" if not existing or existing.endswith("\n") else "\n"
            path.write_text(existing + separator + scaffold_file.content)
            (updated if existing else written).append(path)
            continue

        if path.exists() and not force:
            skipped.append(path)
            continue

        path.write_text(scaffold_file.content)
        written.append(path)

    return ScaffoldResult(
        written=tuple(written),
        updated=tuple(updated),
        skipped=tuple(skipped),
    )


@dataclass(frozen=True)
class TutorialScaffold:
    """Configuration for the generic tutorial repository scaffold."""

    title: str
    tutorial_id: str
    include_vscode: bool = True
    include_test: bool = True

    def plan(self, root: str | Path) -> ScaffoldPlan:
        """Return the files that would be added to a course repository."""
        destination = Path(root).expanduser().resolve()
        tutorial_id = _validate_name(self.tutorial_id, field="tutorial_id")
        title = self.title.strip()
        if not title:
            raise _EmptyTitleError

        files: list[ScaffoldFile] = [
            ScaffoldFile(
                destination / COURSE_FILE,
                _normalise(
                    f'''\
                    format_version = 1

                    [course]
                    id = {json.dumps(tutorial_id)}
                    title = {json.dumps(title)}
                    version = 1
                    state_directory = ".tutorial-engine"
                    welcome_message = """
                    Welcome to {title}.

                    Edit the current exercise and save it to run the check again.
                    """
                    completion_message = """
                    You have completed {title}.
                    """
                    '''
                ),
            ),
            ScaffoldFile(
                destination / "tutorial" / "README.md",
                _normalise(
                    """\
                    # Tutorial content

                    - `exercises/` contains files edited by learners.
                    - `starters/` contains clean reset copies.
                    - `checks/` contains pytest checks.
                    - `solutions/` contains reference solutions.
                    - `lessons/` contains companion explanations.

                    Add exercises with `uv run tutorial-engine add-exercise` or by
                    editing `tutorial.toml` and these directories directly.
                    """
                ),
            ),
            ScaffoldFile(destination / "tutorial" / "exercises" / ".gitkeep", ""),
            ScaffoldFile(destination / "tutorial" / "starters" / ".gitkeep", ""),
            ScaffoldFile(destination / "tutorial" / "checks" / ".gitkeep", ""),
            ScaffoldFile(destination / "tutorial" / "solutions" / ".gitkeep", ""),
            ScaffoldFile(destination / "tutorial" / "lessons" / ".gitkeep", ""),
            ScaffoldFile(
                destination / ".gitignore",
                _normalise(f"{_GITIGNORE_MARKER}\n.tutorial-engine/"),
                mode="append_once",
                marker=_GITIGNORE_MARKER,
            ),
        ]

        if self.include_vscode:
            files.extend(
                [
                    ScaffoldFile(
                        destination / ".vscode" / "extensions.json",
                        json.dumps(
                            {
                                "recommendations": [
                                    "ms-python.python",
                                    "ms-python.vscode-pylance",
                                ]
                            },
                            indent=2,
                        )
                        + "\n",
                    ),
                    ScaffoldFile(
                        destination / ".vscode" / "settings.json",
                        json.dumps(
                            {
                                "python.analysis.diagnosticMode": "workspace",
                                "problems.decorations.enabled": True,
                                "explorer.decorations.colors": True,
                                "explorer.decorations.badges": True,
                            },
                            indent=2,
                        )
                        + "\n",
                    ),
                ]
            )

        if self.include_test:
            files.append(
                ScaffoldFile(
                    destination / "tests" / "test_tutorial.py",
                    _normalise(
                        """\
                        from didactyl import load_course, verify_course


                        def test_tutorial_starters_and_solutions() -> None:
                            report = verify_course(load_course())
                            failures = [item.exercise.name for item in report.items if not item.passed]
                            assert not failures, f"Invalid tutorial exercises: {failures}"
                        """
                    ),
                )
            )

        return ScaffoldPlan(root=destination, files=tuple(files))


@dataclass(frozen=True)
class ExerciseScaffold:
    """Configuration for adding one exercise to an existing course."""

    name: str
    title: str
    section: str = "00_intro"
    timeout: float = 20.0

    def plan(self, root: str | Path) -> ScaffoldPlan:
        """Return the files and metadata entry for a new exercise."""
        destination = Path(root).expanduser().resolve()
        name = _validate_name(self.name, field="name")
        section = _validate_section(self.section)
        title = self.title.strip()
        if not title:
            raise _EmptyTitleError
        if self.timeout <= 0:
            raise _InvalidTimeoutError

        metadata_path = destination / COURSE_FILE
        if not metadata_path.is_file():
            raise _MissingCourseFileError(COURSE_FILE)
        with metadata_path.open("rb") as stream:
            metadata = tomllib.load(stream)
        for raw in metadata.get("exercises", []):
            if isinstance(raw, dict) and raw.get("name") == name:
                raise _DuplicateExerciseError(name)

        file_stem = name.replace("-", "_")
        exercise_relative = Path("tutorial/exercises") / section / f"{file_stem}.py"
        starter_relative = Path("tutorial/starters") / section / f"{file_stem}.py"
        check_relative = Path("tutorial/checks") / section / f"test_{file_stem}.py"
        solution_relative = Path("tutorial/solutions") / section / f"{file_stem}.py"
        lesson_relative = Path("tutorial/lessons") / section / f"{file_stem}.md"

        starter = _normalise(
            f'''\
            from didactyl.testing import incomplete


            def answer() -> str:
                """Complete the exercise: {title}."""
                incomplete("Replace this placeholder with the exercise implementation.")
            '''
        )
        solution = _normalise(
            f'''\
            def answer() -> str:
                """Reference solution for: {title}."""
                return "complete"
            '''
        )
        check = _normalise(
            """\
            from didactyl.testing import load_exercise_module


            exercise = load_exercise_module()


            def test_exercise() -> None:
                assert exercise.answer() == "complete"
            """
        )
        lesson = _normalise(
            f"""\
            # {title}

            Replace this file with the explanation that accompanies the exercise.
            """
        )
        metadata_entry = _normalise(
            f'''\

            [[exercises]]
            name = {json.dumps(name)}
            title = {json.dumps(title)}
            path = {json.dumps(exercise_relative.as_posix())}
            starter = {json.dumps(starter_relative.as_posix())}
            check = {json.dumps(check_relative.as_posix())}
            solution = {json.dumps(solution_relative.as_posix())}
            lesson = {json.dumps(lesson_relative.as_posix())}
            timeout = {float(self.timeout)}
            expected_failure = "tutorial-incomplete"
            hint = """
            Replace this hint with guidance specific to the exercise.
            """
            '''
        )

        return ScaffoldPlan(
            root=destination,
            files=(
                ScaffoldFile(destination / exercise_relative, starter),
                ScaffoldFile(destination / starter_relative, starter),
                ScaffoldFile(destination / check_relative, check),
                ScaffoldFile(destination / solution_relative, solution),
                ScaffoldFile(destination / lesson_relative, lesson),
                ScaffoldFile(
                    metadata_path,
                    metadata_entry,
                    mode="append_once",
                    marker=f'name = "{name}"',
                ),
            ),
        )


def scaffold_tutorial(
    root: str | Path,
    **options: Unpack[_TutorialScaffoldOptions],
) -> ScaffoldResult:
    """Add the generic tutorial scaffold to a repository."""
    plan = TutorialScaffold(
        title=options["title"],
        tutorial_id=options["tutorial_id"],
        include_vscode=options.get("include_vscode", True),
        include_test=options.get("include_test", True),
    ).plan(root)
    return apply_scaffold(plan, force=options.get("force", False))


def scaffold_exercise(
    root: str | Path,
    **options: Unpack[_ExerciseScaffoldOptions],
) -> ScaffoldResult:
    """Add one exercise and its metadata to an existing tutorial repository."""
    plan = ExerciseScaffold(
        name=options["name"],
        title=options["title"],
        section=options.get("section", "00_intro"),
        timeout=options.get("timeout", 20.0),
    ).plan(root)
    return apply_scaffold(plan, force=options.get("force", False))
