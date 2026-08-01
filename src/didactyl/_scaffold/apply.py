import typing

from didactyl._scaffold.models import (
    ScaffoldPlan,
    ScaffoldResult,
)

if typing.TYPE_CHECKING:
    from pathlib import Path


def apply_scaffold(
    plan: ScaffoldPlan,
    *,
    force: bool = False,
) -> ScaffoldResult:
    """Apply a scaffold plan without overwriting existing files by default."""
    written: list[Path] = []
    updated: list[Path] = []
    skipped: list[Path] = []

    for scaffold_file in plan.files:
        path = scaffold_file.path
        path.parent.mkdir(parents=True, exist_ok=True)

        if scaffold_file.mode == "append_once":
            existing = path.read_text() if path.is_file() else ""
            marker = scaffold_file.marker or scaffold_file.content.strip()

            if marker in existing:
                skipped.append(path)
                continue

            separator = "" if not existing or existing.endswith("\n") else "\n"
            path.write_text(existing + separator + scaffold_file.content)

            if existing:
                updated.append(path)
            else:
                written.append(path)

            continue

        if path.exists() and not force:
            skipped.append(path)
            continue

        path.write_text(scaffold_file.content)
        written.append(path)

    return ScaffoldResult(
        written=tuple(written),
        updated=tuple(updated),
        skipped=tuple(skipped),
    )
