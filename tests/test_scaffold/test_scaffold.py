import pathlib

from didactyl import verify_course
from didactyl._scaffold import (
    ExerciseScaffold,
    TutorialScaffold,
    apply_scaffold,
    scaffold_exercise,
    scaffold_tutorial,
)
from didactyl.course import load_course


def test_tutorial_scaffold_starts_empty(tmp_path: pathlib.Path) -> None:
    result = scaffold_tutorial(
        tmp_path,
        title="Biltlings",
        tutorial_id="biltlings",
    )

    assert tmp_path / "tutorial.toml" in result.written
    course = load_course(tmp_path)
    assert course.title == "Biltlings"
    assert course.exercises == ()
    assert ".tutorial-engine/" in (tmp_path / ".gitignore").read_text()


def test_scaffold_does_not_overwrite_by_default(tmp_path: pathlib.Path) -> None:
    scaffold_tutorial(tmp_path, title="First", tutorial_id="first")
    metadata = tmp_path / "tutorial.toml"
    metadata.write_text("custom\n")

    result = scaffold_tutorial(tmp_path, title="Second", tutorial_id="second")

    assert metadata in result.skipped
    assert metadata.read_text() == "custom\n"


def test_add_exercise_creates_valid_toy_exercise(tmp_path: pathlib.Path) -> None:
    scaffold_tutorial(tmp_path, title="Demo", tutorial_id="demo")
    result = scaffold_exercise(
        tmp_path,
        name="intro-example",
        title="Complete the example",
    )

    assert result.written
    course = load_course(tmp_path)
    assert [exercise.name for exercise in course.exercises] == ["intro-example"]

    report = verify_course(course)
    assert report.passed
    assert report.items[0].starter_failed_as_expected
    assert report.items[0].solution_passed


def test_scaffold_plan_can_be_inspected_before_application(tmp_path: pathlib.Path) -> None:
    tutorial_plan = TutorialScaffold(title="Demo", tutorial_id="demo").plan(tmp_path)
    assert any(file.path.name == "tutorial.toml" for file in tutorial_plan.files)
    apply_scaffold(tutorial_plan)

    exercise_plan = ExerciseScaffold(
        name="intro-example",
        title="Complete the example",
    ).plan(tmp_path)
    assert any(file.path.name == "intro_example.py" for file in exercise_plan.files)
