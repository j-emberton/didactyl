import os
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from didactyl._models import (
    Course,
    Exercise,
    ExerciseResult,
    VerificationItem,
    VerificationReport,
)
from didactyl.testing import EXERCISE_ENVIRONMENT_VARIABLE


def _combined_output(result: subprocess.CompletedProcess[str]) -> str:
    return "\n".join(part.strip() for part in (result.stdout, result.stderr) if part.strip())


def run_exercise(
    course: Course,
    exercise: Exercise,
    *,
    candidate: str | Path | None = None,
) -> ExerciseResult:
    """Run one exercise check in an isolated Python subprocess."""
    candidate_path = Path(candidate or exercise.path).resolve()
    environment = os.environ.copy()
    environment[EXERCISE_ENVIRONMENT_VARIABLE] = str(candidate_path)
    package_root = str(Path(__file__).resolve().parents[1])
    existing_pythonpath = environment.get("PYTHONPATH", "")
    environment["PYTHONPATH"] = os.pathsep.join(
        part for part in (package_root, existing_pythonpath) if part
    )

    command = [
        sys.executable,
        "-m",
        "pytest",
        "-q",
        str(exercise.check),
        "--tb=short",
        "--disable-warnings",
    ]

    try:
        result = subprocess.run(  # noqa: S603
            command,
            cwd=course.root,
            env=environment,
            capture_output=True,
            text=True,
            timeout=exercise.timeout,
            check=False,
        )
    except subprocess.TimeoutExpired as error:
        output_parts = [
            part.decode() if isinstance(part, bytes) else part
            for part in (error.stdout, error.stderr)
            if part
        ]
        output = "\n".join(output_parts)
        return ExerciseResult(
            exercise=exercise,
            passed=False,
            returncode=124,
            output=(output + f"\nCheck timed out after {exercise.timeout:g} seconds.").strip(),
            timed_out=True,
            candidate=candidate_path,
        )

    return ExerciseResult(
        exercise=exercise,
        passed=result.returncode == 0,
        returncode=result.returncode,
        output=_combined_output(result),
        candidate=candidate_path,
    )


def check_all(
    course: Course,
    *,
    max_workers: int | None = None,
) -> tuple[ExerciseResult, ...]:
    """Check all learner exercise files, preserving course order."""
    if not course.exercises:
        return ()
    worker_count = max_workers or min(8, len(course.exercises))
    with ThreadPoolExecutor(max_workers=worker_count) as executor:
        return tuple(executor.map(lambda item: run_exercise(course, item), course.exercises))


def verify_course(course: Course) -> VerificationReport:
    """Verify authoring invariants for all starters and solutions."""
    items: list[VerificationItem] = []
    warnings: list[str] = []

    if not course.exercises:
        warnings.append("The tutorial contains no exercises yet.")

    for exercise in course.exercises:
        starter = run_exercise(course, exercise, candidate=exercise.starter)
        if exercise.solution is None:
            solution = ExerciseResult(
                exercise=exercise,
                passed=True,
                returncode=0,
                output="No reference solution configured.",
            )
        else:
            solution = run_exercise(course, exercise, candidate=exercise.solution)

        marker = exercise.expected_failure
        expected = not starter.passed and (marker is None or marker in starter.output)
        items.append(
            VerificationItem(
                exercise=exercise,
                starter_failed=not starter.passed,
                starter_failed_as_expected=expected,
                solution_passed=solution.passed,
                starter_output=starter.output,
                solution_output=solution.output,
            )
        )

    return VerificationReport(course=course, items=tuple(items), warnings=tuple(warnings))
