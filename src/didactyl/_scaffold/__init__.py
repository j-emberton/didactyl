"""Public scaffolding API."""

from didactyl._scaffold.exercise import (
    ExerciseScaffold,
    apply_scaffold,
    scaffold_exercise,
)
from didactyl._scaffold.models import ScaffoldFile, ScaffoldPlan, ScaffoldResult
from didactyl._scaffold.tutorial import TutorialScaffold, scaffold_tutorial

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
