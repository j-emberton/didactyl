from didactyl.testing import load_exercise_module

exercise = load_exercise_module()


def test_exercise() -> None:
    assert exercise.answer() == "complete"
