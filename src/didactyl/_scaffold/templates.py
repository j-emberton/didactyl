import json
import textwrap
from pathlib import Path


def normalise(content: str) -> str:
    """Normalise generated text to a single trailing newline."""
    return textwrap.dedent(content).lstrip("\n").rstrip() + "\n"


def course_metadata(
    *,
    title: str,
    tutorial_id: str,
) -> str:
    """Return the initial tutorial metadata file."""
    return normalise(
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
    )


def tutorial_readme() -> str:
    """Return the README placed inside the tutorial directory."""
    return normalise(
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
    )


def gitignore_entry(*, marker: str) -> str:
    """Return the Didactyl state-directory gitignore entry."""
    return normalise(
        f"""\
        {marker}
        .tutorial-engine/
        """
    )


def vscode_extensions() -> str:
    """Return the recommended VS Code extensions configuration."""
    return (
        json.dumps(
            {
                "recommendations": [
                    "ms-python.python",
                    "ms-python.vscode-pylance",
                ]
            },
            indent=2,
        )
        + "\n"
    )


def vscode_settings() -> str:
    """Return the default VS Code workspace settings."""
    return (
        json.dumps(
            {
                "python.analysis.diagnosticMode": "workspace",
                "problems.decorations.enabled": True,
                "explorer.decorations.colors": True,
                "explorer.decorations.badges": True,
            },
            indent=2,
        )
        + "\n"
    )


def tutorial_test() -> str:
    """Return the initial course-verification test."""
    return normalise(
        """\
        from didactyl import load_course, verify_course


        def test_tutorial_starters_and_solutions() -> None:
            report = verify_course(load_course())
            failures = [
                item.exercise.name
                for item in report.items
                if not item.passed
            ]
            assert not failures, f"Invalid tutorial exercises: {failures}"
        """
    )


def exercise_starter(*, title: str) -> str:
    """Return the starter implementation for an exercise."""
    return normalise(
        f'''\
        from didactyl.testing import incomplete


        def answer() -> str:
            """Complete the exercise: {title}."""
            incomplete(
                "Replace this placeholder with the exercise implementation."
            )
        '''
    )


def exercise_solution(*, title: str) -> str:
    """Return the initial reference solution for an exercise."""
    return normalise(
        f'''\
        def answer() -> str:
            """Reference solution for: {title}."""
            return "complete"
        '''
    )


def exercise_check() -> str:
    """Return the initial pytest check for an exercise."""
    return normalise(
        """\
        from didactyl.testing import load_exercise_module


        exercise = load_exercise_module()


        def test_exercise() -> None:
            assert exercise.answer() == "complete"
        """
    )


def exercise_lesson(*, title: str) -> str:
    """Return the initial lesson for an exercise."""
    return normalise(
        f"""\
        # {title}

        Replace this file with the explanation that accompanies the exercise.
        """
    )


def exercise_metadata_entry(
    *,
    name: str,
    title: str,
    exercise: Path,
    starter: Path,
    check: Path,
    solution: Path,
    lesson: Path,
    timeout: float,
) -> str:
    """Return one exercise entry for tutorial.toml."""
    return normalise(
        f'''\

        [[exercises]]
        name = {json.dumps(name)}
        title = {json.dumps(title)}
        path = {json.dumps(exercise.as_posix())}
        starter = {json.dumps(starter.as_posix())}
        check = {json.dumps(check.as_posix())}
        solution = {json.dumps(solution.as_posix())}
        lesson = {json.dumps(lesson.as_posix())}
        timeout = {float(timeout)}
        expected_failure = "tutorial-incomplete"
        hint = """
        Replace this hint with guidance specific to the exercise.
        """
        '''
    )
