import shutil
from pathlib import Path

import pytest

from didactyl import (
    current_exercise,
    is_complete,
    load_course,
    load_progress,
    run_exercise,
    scaffold_exercise,
    scaffold_tutorial,
)
from didactyl._models import Course
from didactyl._progress import record_result


def _course(tmp_path: Path) -> Course:
    scaffold_tutorial(
        tmp_path,
        title="Demo",
        tutorial_id="demo",
    )
    scaffold_exercise(
        tmp_path,
        name="intro-example",
        title="Complete the example",
    )
    return load_course(tmp_path)


def test_progress_tracks_completed_content_hash(tmp_path: Path) -> None:
    course = _course(tmp_path)
    exercise = course.exercises[0]

    solution = exercise.solution
    if solution is None:
        pytest.fail("Scaffolded exercise has no reference solution")

    shutil.copyfile(solution, exercise.path)

    result = run_exercise(course, exercise)
    progress = record_result(
        course,
        load_progress(course),
        exercise,
        passed=result.passed,
    )

    assert result.passed
    assert is_complete(exercise, progress)
    assert current_exercise(course, progress) is None

    exercise.path.write_text(
        exercise.path.read_text() + "\n# changed\n",
    )

    assert not is_complete(exercise, progress)


def test_incompatible_course_version_resets_progress(tmp_path: Path) -> None:
    course = _course(tmp_path)
    path = course.state_directory / "progress.json"
    path.parent.mkdir(parents=True)
    path.write_text(
        '{"course_version": 999, "current": "intro-example", "completed": {}}\n',
    )

    assert load_progress(course).current is None