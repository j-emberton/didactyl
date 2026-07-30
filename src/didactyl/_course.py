from __future__ import annotations

import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import cast

from didactyl._models import Course, Exercise

COURSE_FILE = "tutorial.toml"
SUPPORTED_FORMAT_VERSION = 1


class _CourseRootNotFoundError(FileNotFoundError):
    def __init__(self, candidate: Path) -> None:
        message = f"Could not find {COURSE_FILE!r} in {candidate} or any parent directory."
        super().__init__(message)


class _CourseFileMissingError(FileNotFoundError):
    def __init__(self, path: Path) -> None:
        super().__init__(f"Missing {path}")


class _ExpectedStringError(TypeError):
    def __init__(self, field: str) -> None:
        super().__init__(f"Expected {field!r} to be a string.")


class _EmptyStringError(ValueError):
    def __init__(self, field: str) -> None:
        super().__init__(f"Expected {field!r} to be a non-empty string.")


class _ExercisePathEscapesRootError(ValueError):
    def __init__(self, field: str, relative: Path) -> None:
        message = f"Exercise field {field!r} escapes the course root: {relative}"
        super().__init__(message)


class _ExerciseFileMissingError(ValueError):
    def __init__(self, field: str, relative: Path) -> None:
        message = f"Exercise field {field!r} points to a missing file: {relative}"
        super().__init__(message)


class _UnsupportedFormatVersionError(ValueError):
    def __init__(self, version: object) -> None:
        message = (
            f"Unsupported tutorial format version {version!r}; expected {SUPPORTED_FORMAT_VERSION}."
        )
        super().__init__(message)


class _CourseTableError(TypeError):
    def __init__(self) -> None:
        super().__init__("tutorial.toml must contain a [course] table.")


class _InvalidCourseVersionTypeError(TypeError):
    def __init__(self) -> None:
        super().__init__("course.version must be an integer.")


class _InvalidCourseVersionError(ValueError):
    def __init__(self) -> None:
        super().__init__("course.version must be a positive integer.")


class _StateDirectoryOutsideRootError(ValueError):
    def __init__(self) -> None:
        message = "course.state_directory must remain inside the course root."
        super().__init__(message)


class _ExpectedExerciseListError(TypeError):
    def __init__(self) -> None:
        message = "Every [[exercises]] entry must be a TOML table."
        super().__init__(message)


class _DuplicateExerciseNameError(ValueError):
    def __init__(self, name: str) -> None:
        super().__init__(f"Duplicate exercise name: {name}")


class _DuplicateExercisePathError(ValueError):
    def __init__(self, path: Path) -> None:
        super().__init__(f"Duplicate exercise path: {path}")


class _InvalidTimeoutTypeError(TypeError):
    def __init__(self, name: str, timeout: object) -> None:
        message = f"Exercise {name!r} has an invalid timeout: {timeout!r}"
        super().__init__(message)


class _InvalidTimeoutError(ValueError):
    def __init__(self, name: str, timeout: float) -> None:
        message = f"Exercise {name!r} has an invalid timeout: {timeout!r}"
        super().__init__(message)


@dataclass(frozen=True)
class _CourseConfiguration:
    title: str
    tutorial_id: str
    version: int
    state_directory: Path
    welcome_message: str
    completion_message: str


def find_course_root(start: str | Path | None = None) -> Path:
    """Find the nearest parent containing ``tutorial.toml``."""
    candidate = Path(start or Path.cwd()).expanduser().resolve()
    if candidate.is_file():
        candidate = candidate.parent

    for directory in (candidate, *candidate.parents):
        if (directory / COURSE_FILE).is_file():
            return directory

    raise _CourseRootNotFoundError(candidate)


def _required_string(value: object, *, field: str) -> str:
    if not isinstance(value, str):
        raise _ExpectedStringError(field)

    stripped = value.strip()
    if not stripped:
        raise _EmptyStringError(field)

    return stripped


def _optional_string(
    value: object,
    *,
    field: str,
    default: str = "",
) -> str:
    if value is None:
        return default
    if not isinstance(value, str):
        raise _ExpectedStringError(field)
    return value


def _required_path(root: Path, value: object, *, field: str) -> Path:
    relative = Path(_required_string(value, field=field))
    path = (root / relative).resolve()

    try:
        path.relative_to(root)
    except ValueError as error:
        raise _ExercisePathEscapesRootError(field, relative) from error

    if not path.is_file():
        raise _ExerciseFileMissingError(field, relative)

    return path


def _optional_path(
    root: Path,
    value: object,
    *,
    field: str,
) -> Path | None:
    if value is None:
        return None
    return _required_path(root, value, field=field)


def _resolve_course_root(root: str | Path | None) -> Path:
    if root is None:
        return find_course_root()
    return Path(root).expanduser().resolve()


def _load_metadata(course_root: Path) -> dict[str, object]:
    metadata_path = course_root / COURSE_FILE
    if not metadata_path.is_file():
        raise _CourseFileMissingError(metadata_path)

    with metadata_path.open("rb") as stream:
        return cast("dict[str, object]", tomllib.load(stream))


def _validate_format_version(value: object) -> int:
    if value != SUPPORTED_FORMAT_VERSION:
        raise _UnsupportedFormatVersionError(value)
    return SUPPORTED_FORMAT_VERSION


def _course_table(value: object) -> dict[str, object]:
    if not isinstance(value, dict):
        raise _CourseTableError
    return cast("dict[str, object]", value)


def _course_version(value: object) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise _InvalidCourseVersionTypeError
    if value < 1:
        raise _InvalidCourseVersionError
    return value


def _state_directory(
    course_root: Path,
    raw_course: dict[str, object],
) -> Path:
    state_name = _optional_string(
        raw_course.get("state_directory"),
        field="course.state_directory",
        default=".tutorial-engine",
    )
    directory = (course_root / state_name).resolve()

    try:
        directory.relative_to(course_root)
    except ValueError as error:
        raise _StateDirectoryOutsideRootError from error

    return directory


def _parse_course_configuration(
    course_root: Path,
    value: object,
) -> _CourseConfiguration:
    raw_course = _course_table(value)
    return _CourseConfiguration(
        title=_required_string(raw_course.get("title"), field="course.title"),
        tutorial_id=_required_string(raw_course.get("id"), field="course.id"),
        version=_course_version(raw_course.get("version")),
        state_directory=_state_directory(course_root, raw_course),
        welcome_message=_optional_string(
            raw_course.get("welcome_message"),
            field="course.welcome_message",
        ),
        completion_message=_optional_string(
            raw_course.get("completion_message"),
            field="course.completion_message",
        ),
    )


def _exercise_tables(value: object) -> tuple[dict[str, object], ...]:
    if not isinstance(value, list):
        raise _ExpectedExerciseListError

    tables: list[dict[str, object]] = []
    for item in value:
        if not isinstance(item, dict):
            raise _ExpectedExerciseListError
        tables.append(cast("dict[str, object]", item))

    return tuple(tables)


def _exercise_timeout(name: str, value: object) -> float:
    if isinstance(value, bool) or not isinstance(value, int | float):
        raise _InvalidTimeoutTypeError(name, value)
    if value <= 0:
        raise _InvalidTimeoutError(name, value)
    return float(value)


def _parse_exercise(
    course_root: Path,
    raw: dict[str, object],
) -> Exercise:
    name = _required_string(raw.get("name"), field="exercises.name")
    return Exercise(
        name=name,
        title=_required_string(raw.get("title", name), field="title"),
        path=_required_path(course_root, raw.get("path"), field="path"),
        starter=_required_path(course_root, raw.get("starter"), field="starter"),
        check=_required_path(course_root, raw.get("check"), field="check"),
        solution=_optional_path(
            course_root,
            raw.get("solution"),
            field="solution",
        ),
        lesson=_optional_path(
            course_root,
            raw.get("lesson"),
            field="lesson",
        ),
        hint=_optional_string(raw.get("hint"), field="hint"),
        timeout=_exercise_timeout(name, raw.get("timeout", 20.0)),
        expected_failure=(
            _optional_string(
                raw.get("expected_failure"),
                field="expected_failure",
            )
            or None
        ),
    )


def _ensure_unique_exercise(
    exercise: Exercise,
    *,
    course_root: Path,
    names: set[str],
    paths: set[Path],
) -> None:
    if exercise.name in names:
        raise _DuplicateExerciseNameError(exercise.name)
    if exercise.path in paths:
        relative = exercise.path.relative_to(course_root)
        raise _DuplicateExercisePathError(relative)

    names.add(exercise.name)
    paths.add(exercise.path)


def _parse_exercises(
    course_root: Path,
    value: object,
) -> tuple[Exercise, ...]:
    exercises: list[Exercise] = []
    names: set[str] = set()
    paths: set[Path] = set()

    for raw in _exercise_tables(value):
        exercise = _parse_exercise(course_root, raw)
        _ensure_unique_exercise(
            exercise,
            course_root=course_root,
            names=names,
            paths=paths,
        )
        exercises.append(exercise)

    return tuple(exercises)


def load_course(root: str | Path | None = None) -> Course:
    """Load and validate a tutorial course."""
    course_root = _resolve_course_root(root)
    metadata = _load_metadata(course_root)
    format_version = _validate_format_version(metadata.get("format_version"))
    configuration = _parse_course_configuration(
        course_root,
        metadata.get("course"),
    )
    exercises = _parse_exercises(
        course_root,
        metadata.get("exercises", []),
    )

    return Course(
        root=course_root,
        title=configuration.title,
        tutorial_id=configuration.tutorial_id,
        version=configuration.version,
        format_version=format_version,
        state_directory=configuration.state_directory,
        welcome_message=configuration.welcome_message,
        completion_message=configuration.completion_message,
        exercises=exercises,
    )
