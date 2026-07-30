"""Public API for Tutorial Engine."""

from didactyl._course import find_course_root, load_course
from didactyl._models import (
    Course,
    Exercise,
    ExerciseResult,
    Progress,
    ScaffoldFile,
    ScaffoldPlan,
    ScaffoldResult,
    VerificationItem,
    VerificationReport,
)
from didactyl._progress import (
    current_exercise,
    exercise_digest,
    is_complete,
    load_progress,
    progress_path,
    save_progress,
)
from didactyl._runner import check_all, run_exercise, verify_course
from didactyl._scaffold import (
    ExerciseScaffold,
    TutorialScaffold,
    apply_scaffold,
    scaffold_exercise,
    scaffold_tutorial,
)
from didactyl._tui import run_tui
from didactyl._version import __version__
from didactyl.cli import course_main
from didactyl.testing import (
    TutorialIncompleteError,
    exercise_path,
    incomplete,
    load_exercise_module,
)

__all__ = [
    "Course",
    "Exercise",
    "ExerciseResult",
    "ExerciseScaffold",
    "Progress",
    "ScaffoldFile",
    "ScaffoldPlan",
    "ScaffoldResult",
    "TutorialIncompleteError",
    "TutorialScaffold",
    "VerificationItem",
    "VerificationReport",
    "__version__",
    "apply_scaffold",
    "check_all",
    "course_main",
    "current_exercise",
    "exercise_digest",
    "exercise_path",
    "find_course_root",
    "incomplete",
    "is_complete",
    "load_course",
    "load_exercise_module",
    "load_progress",
    "progress_path",
    "run_exercise",
    "run_tui",
    "save_progress",
    "scaffold_exercise",
    "scaffold_tutorial",
    "verify_course",
]
