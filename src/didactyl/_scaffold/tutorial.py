import re
from dataclasses import dataclass
from pathlib import Path
from typing import NotRequired, TypedDict, Unpack

from didactyl._course import COURSE_FILE
from didactyl._scaffold.apply import apply_scaffold
from didactyl._scaffold.models import (
    ScaffoldFile,
    ScaffoldPlan,
    ScaffoldResult,
)
from didactyl._scaffold.templates import (
    course_metadata,
    gitignore_entry,
    tutorial_readme,
    tutorial_test,
    vscode_extensions,
    vscode_settings,
)

_NAME_PATTERN = re.compile(r"^[a-z0-9][a-z0-9_-]*$")
_GITIGNORE_MARKER = "# tutorial-engine state"


class InvalidNameError(ValueError):
    """Raised when a scaffold identifier has an invalid format."""

    def __init__(self, field: str) -> None:
        message = (
            f"{field} must start with a lower-case letter or number and contain "
            "only lower-case letters, numbers, '-' and '_'."
        )
        super().__init__(message)


class EmptyTitleError(ValueError):
    """Raised when a scaffold title is empty."""

    def __init__(self) -> None:
        message = "title must not be empty."
        super().__init__(message)


def validate_name(value: str, *, field: str) -> str:
    """Validate and return a scaffold identifier."""
    if not _NAME_PATTERN.fullmatch(value):
        raise InvalidNameError(field)

    return value


def validate_title(value: str) -> str:
    """Strip and validate a scaffold title."""
    title = value.strip()

    if not title:
        raise EmptyTitleError

    return title


class _TutorialScaffoldOptions(TypedDict):
    """Keyword options accepted by :func:`scaffold_tutorial`."""

    title: str
    tutorial_id: str
    force: NotRequired[bool]
    include_vscode: NotRequired[bool]
    include_test: NotRequired[bool]


@dataclass(frozen=True)
class TutorialScaffold:
    """Configuration for the generic tutorial repository scaffold."""

    title: str
    tutorial_id: str
    include_vscode: bool = True
    include_test: bool = True

    def plan(self, root: str | Path) -> ScaffoldPlan:
        """Return the files that would be added to a course repository."""
        destination = Path(root).expanduser().resolve()
        tutorial_id = validate_name(
            self.tutorial_id,
            field="tutorial_id",
        )
        title = validate_title(self.title)

        files: list[ScaffoldFile] = [
            ScaffoldFile(
                destination / COURSE_FILE,
                course_metadata(
                    title=title,
                    tutorial_id=tutorial_id,
                ),
            ),
            ScaffoldFile(
                destination / "tutorial" / "README.md",
                tutorial_readme(),
            ),
            ScaffoldFile(
                destination / "tutorial" / "exercises" / ".gitkeep",
                "",
            ),
            ScaffoldFile(
                destination / "tutorial" / "starters" / ".gitkeep",
                "",
            ),
            ScaffoldFile(
                destination / "tutorial" / "checks" / ".gitkeep",
                "",
            ),
            ScaffoldFile(
                destination / "tutorial" / "solutions" / ".gitkeep",
                "",
            ),
            ScaffoldFile(
                destination / "tutorial" / "lessons" / ".gitkeep",
                "",
            ),
            ScaffoldFile(
                destination / ".gitignore",
                gitignore_entry(marker=_GITIGNORE_MARKER),
                mode="append_once",
                marker=_GITIGNORE_MARKER,
            ),
        ]

        if self.include_vscode:
            files.extend(
                [
                    ScaffoldFile(
                        destination / ".vscode" / "extensions.json",
                        vscode_extensions(),
                    ),
                    ScaffoldFile(
                        destination / ".vscode" / "settings.json",
                        vscode_settings(),
                    ),
                ]
            )

        if self.include_test:
            files.append(
                ScaffoldFile(
                    destination / "tests" / "test_tutorial.py",
                    tutorial_test(),
                )
            )

        return ScaffoldPlan(
            root=destination,
            files=tuple(files),
        )


def scaffold_tutorial(
    root: str | Path,
    **options: Unpack[_TutorialScaffoldOptions],
) -> ScaffoldResult:
    """Add the generic tutorial scaffold to a repository."""
    plan = TutorialScaffold(
        title=options["title"],
        tutorial_id=options["tutorial_id"],
        include_vscode=options.get("include_vscode", True),
        include_test=options.get("include_test", True),
    ).plan(root)

    return apply_scaffold(
        plan,
        force=options.get("force", False),
    )
