import importlib.util
import os
from pathlib import Path
from types import ModuleType

EXERCISE_ENVIRONMENT_VARIABLE = "didactyl_EXERCISE"
INCOMPLETE_MARKER = "didactyl_FAILURE:tutorial-incomplete"


class TutorialIncompleteError(RuntimeError):
    """Raised by an intentionally incomplete generated exercise."""


def exercise_path() -> Path:
    """Return the candidate exercise path supplied by the engine."""
    raw = os.environ.get(EXERCISE_ENVIRONMENT_VARIABLE)
    if raw is None:
        error = (
            f"{EXERCISE_ENVIRONMENT_VARIABLE} is not set. Run the check through Tutorial Engine."
        )
        raise RuntimeError(error)

    return Path(raw).resolve()


def load_exercise_module(*, module_name: str = "didactyl_exercise") -> ModuleType:
    """Load the candidate exercise as a Python module."""
    path = exercise_path()
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        error = f"Could not load exercise from {path}"
        raise RuntimeError(error)

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def incomplete(message: str = "This exercise is not complete.") -> None:
    """Mark a generated starter as intentionally incomplete."""
    error = f"{INCOMPLETE_MARKER}\n{message}"
    raise TutorialIncompleteError(error)
