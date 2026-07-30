import hashlib
import json
from pathlib import Path

from didactyl._models import Course, Exercise, Progress

PROGRESS_FILE = "progress.json"


def progress_path(course: Course) -> Path:
    """Return the progress file path for a course."""
    return course.state_directory / PROGRESS_FILE


def load_progress(course: Course) -> Progress:
    """Load learner progress, resetting incompatible or malformed state."""
    path = progress_path(course)
    if not path.is_file():
        return Progress(course_version=course.version)

    try:
        data = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError):
        return Progress(course_version=course.version)

    if data.get("course_version") != course.version:
        return Progress(course_version=course.version)

    current = data.get("current")
    completed = data.get("completed")
    if current is not None and not isinstance(current, str):
        current = None
    if not isinstance(completed, dict):
        completed = {}

    return Progress(
        course_version=course.version,
        current=current,
        completed={
            str(name): str(digest)
            for name, digest in completed.items()
            if isinstance(name, str) and isinstance(digest, str)
        },
    )


def save_progress(course: Course, progress: Progress) -> None:
    """Persist learner progress atomically."""
    path = progress_path(course)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".tmp")
    temporary.write_text(
        json.dumps(
            {
                "course_version": course.version,
                "current": progress.current,
                "completed": progress.completed,
            },
            indent=2,
            sort_keys=True,
        )
        + "\n"
    )
    temporary.replace(path)


def exercise_digest(exercise: Exercise) -> str:
    """Hash the learner file and its check to invalidate stale completion."""
    digest = hashlib.sha256()
    for path in (exercise.path, exercise.check):
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def is_complete(exercise: Exercise, progress: Progress) -> bool:
    """Return whether the stored completion hash still matches."""
    return progress.completed.get(exercise.name) == exercise_digest(exercise)


def current_exercise(course: Course, progress: Progress) -> Exercise | None:
    """Resolve the selected exercise or the first incomplete exercise."""
    if progress.current is not None:
        for exercise in course.exercises:
            if exercise.name == progress.current and not is_complete(exercise, progress):
                return exercise
    return next((item for item in course.exercises if not is_complete(item, progress)), None)


def record_result(
    course: Course, progress: Progress, exercise: Exercise, *, passed: bool
) -> Progress:
    """Return and persist progress updated from an exercise result."""
    completed = dict(progress.completed)
    if passed:
        completed[exercise.name] = exercise_digest(exercise)
    else:
        completed.pop(exercise.name, None)

    next_current = exercise.name
    if passed:
        for candidate in course.exercises:
            candidate_digest = completed.get(candidate.name)
            if candidate_digest != exercise_digest(candidate):
                next_current = candidate.name
                break
        else:
            next_current = None

    updated = Progress(
        course_version=course.version,
        current=next_current,
        completed=completed,
    )
    save_progress(course, updated)
    return updated


def select_exercise(course: Course, progress: Progress, exercise: Exercise) -> Progress:
    """Persist an explicitly selected exercise."""
    updated = Progress(
        course_version=course.version,
        current=exercise.name,
        completed=dict(progress.completed),
    )
    save_progress(course, updated)
    return updated
