from dataclasses import dataclass
from pathlib import Path
from typing import Literal

WriteMode = Literal["create", "append_once"]


@dataclass(frozen=True)
class ScaffoldFile:
    """A file operation in a scaffold plan."""

    path: Path
    content: str
    mode: WriteMode = "create"
    marker: str | None = None


@dataclass(frozen=True)
class ScaffoldPlan:
    """A set of scaffold files ready to be applied."""

    root: Path
    files: tuple[ScaffoldFile, ...]


@dataclass(frozen=True)
class ScaffoldResult:
    """Summary of scaffold changes."""

    written: tuple[Path, ...] = ()
    updated: tuple[Path, ...] = ()
    skipped: tuple[Path, ...] = ()

    @property
    def changed(self) -> tuple[Path, ...]:
        """Return all files that were written or updated."""
        return (*self.written, *self.updated)
