import re
import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import NotRequired, TypedDict, Unpack

from didactyl._course import COURSE_FILE
from didactyl._scaffold.apply import apply_scaffold
from didactyl._scaffold.models import (
    ScaffoldFile,
    ScaffoldPlan,
    ScaffoldResult,
)
from didactyl._scaffold.templates import (
    exercise_check,
    exercise_lesson,
    exercise_metadata_entry,
    exercise_solution,
    exercise_starter,
)
from didactyl._scaffold.tutorial import (
    validate_name,
    validate_title,
)

_NAME_PATTERN = re.compile(r"^[a-z0-9][a-z0-9_-]*$")


class _InvalidSectionError(ValueError):
    """Raised when an exercise section is not a valid relative path."""

    def __init__(self) -> None:
        message = "section must be a relative path without '.' or '..' components."
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


def _validate_section(value: str) -> str:
    section = Path(value)

    if (
        section.is_absolute()
        or not section.parts
        or any(part in {"", ".", ".."} for part in section.parts)
    ):
        raise _InvalidSectionError

    for part in section.parts:
        validate_name(
            part,
            field="section component",
        )

    return section.as_posix()


class _ExerciseScaffoldOptions(TypedDict):
    """Keyword options accepted by :func:`scaffold_exercise`."""

    name: str
    title: str
    section: NotRequired[str]
    timeout: NotRequired[float]
    force: NotRequired[bool]


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
        name = validate_name(
            self.name,
            field="name",
        )
        title = validate_title(self.title)
        section = _validate_section(self.section)

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

        starter = exercise_starter(title=title)

        return ScaffoldPlan(
            root=destination,
            files=(
                ScaffoldFile(
                    destination / exercise_relative,
                    starter,
                ),
                ScaffoldFile(
                    destination / starter_relative,
                    starter,
                ),
                ScaffoldFile(
                    destination / check_relative,
                    exercise_check(),
                ),
                ScaffoldFile(
                    destination / solution_relative,
                    exercise_solution(title=title),
                ),
                ScaffoldFile(
                    destination / lesson_relative,
                    exercise_lesson(title=title),
                ),
                ScaffoldFile(
                    metadata_path,
                    exercise_metadata_entry(
                        name=name,
                        title=title,
                        exercise=exercise_relative,
                        starter=starter_relative,
                        check=check_relative,
                        solution=solution_relative,
                        lesson=lesson_relative,
                        timeout=self.timeout,
                    ),
                    mode="append_once",
                    marker=f'name = "{name}"',
                ),
            ),
        )


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

    return apply_scaffold(
        plan,
        force=options.get("force", False),
    )
