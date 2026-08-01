from didactyl import load_course, verify_course


def test_tutorial_starters_and_solutions() -> None:
    report = verify_course(load_course())
    failures = [item.exercise.name for item in report.items if not item.passed]
    assert not failures, f"Invalid tutorial exercises: {failures}"
