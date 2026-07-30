import os
import subprocess
import sys
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).parents[1]


def _environment() -> dict[str, str]:
    environment = os.environ.copy()
    source = str(REPOSITORY_ROOT / "src")
    environment["PYTHONPATH"] = os.pathsep.join(
        part for part in (source, environment.get("PYTHONPATH", "")) if part
    )
    return environment


def test_cli_authoring_workflow(tmp_path: Path) -> None:
    init_result = subprocess.run(
        [
            sys.executable,
            "-m",
            "didactyl",
            "init",
            str(tmp_path),
            "--title",
            "Demo",
            "--example",
        ],
        cwd=REPOSITORY_ROOT,
        env=_environment(),
        capture_output=True,
        text=True,
        check=False,
    )
    assert init_result.returncode == 0, init_result.stdout + init_result.stderr

    verify_result = subprocess.run(
        [sys.executable, "-m", "didactyl", "verify"],
        cwd=tmp_path,
        env=_environment(),
        capture_output=True,
        text=True,
        check=False,
    )
    assert verify_result.returncode == 0, verify_result.stdout + verify_result.stderr
    assert "starter fails for the expected reason" in verify_result.stdout
