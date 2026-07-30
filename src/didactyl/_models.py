from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal


@dataclass(frozen=True)
class Exercise:
    """One ordered tutorial exercise."""

    name: str
    title: str
    path: Path
    starter: Path
    check: Path
    solution: Path | None
    lesson: Path | None
    hint: str
    timeout: float = 20.0
    expected_failure: str | None = None


@dataclass(frozen=True)
class Course:
    """A loaded tutorial course."""

    root: Path
    title: str
    tutorial_id: str
    version: int
    format_version: int
    state_directory: Path
    welcome_message: str
    completion_message: str
    exercises: tuple[Exercise, ...]

    def exercise(self, name: str) -> Exercise:
        """Return an exercise by name."""
        for exercise in self.exercises:
            if exercise.name == name:
                return exercise
        available = ", ".join(item.name for item in self.exercises) or "none"
        error = f"Unknown exercise {name!r}. Available exercises: {available}"
        raise KeyError(error)


@dataclass(frozen=True)
class ExerciseResult:
    """Result of running an exercise check."""

    exercise: Exercise
    passed: bool
    returncode: int
    output: str
    timed_out: bool = False
    candidate: Path | None = None


@dataclass(frozen=True)
class VerificationItem:
    """Author-facing verification result for one exercise."""

    exercise: Exercise
    starter_failed: bool
    starter_failed_as_expected: bool
    solution_passed: bool
    starter_output: str = ""
    solution_output: str = ""

    @property
    def passed(self) -> bool:
        return self.starter_failed and self.starter_failed_as_expected and self.solution_passed


@dataclass(frozen=True)
class VerificationReport:
    """Course verification result."""

    course: Course
    items: tuple[VerificationItem, ...]
    warnings: tuple[str, ...] = ()

    @property
    def passed(self) -> bool:
        return all(item.passed for item in self.items)


@dataclass(frozen=True)
class Progress:
    """Persisted learner progress."""

    course_version: int
    current: str | None = None
    completed: dict[str, str] = field(default_factory=dict)


WriteMode = Literal["create", "append_once"]


@dataclass(frozen=True)
class ScaffoldFile:
    """A file operation in a scaffold plan."""

    path: Path
    content: str
    mode: WriteMode = "create"
    marker: str | None = None


@dataclass(frozen=True)
class ScaffoldPlan:
    """A set of scaffold files ready to be applied."""

    root: Path
    files: tuple[ScaffoldFile, ...]


@dataclass(frozen=True)
class ScaffoldResult:
    """Summary of scaffold changes."""

    written: tuple[Path, ...] = ()
    updated: tuple[Path, ...] = ()
    skipped: tuple[Path, ...] = ()

    @property
    def changed(self) -> tuple[Path, ...]:
        return (*self.written, *self.updated)
