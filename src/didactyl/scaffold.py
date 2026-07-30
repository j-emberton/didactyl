"""Public scaffolding API."""

from didactyl._models import ScaffoldFile, ScaffoldPlan, ScaffoldResult
from didactyl._scaffold import (
    ExerciseScaffold,
    TutorialScaffold,
    apply_scaffold,
    scaffold_exercise,
    scaffold_tutorial,
)

__all__ = [
    "ExerciseScaffold",
    "ScaffoldFile",
    "ScaffoldPlan",
    "ScaffoldResult",
    "TutorialScaffold",
    "apply_scaffold",
    "scaffold_exercise",
    "scaffold_tutorial",
]
