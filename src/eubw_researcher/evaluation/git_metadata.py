from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any, Optional


def collect_git_metadata(repo_root: Path) -> dict[str, Any]:
    branch = _run_git_command(repo_root, "branch", "--show-current")
    commit = _run_git_command(repo_root, "rev-parse", "HEAD")
    status = _run_git_command(repo_root, "status", "--short")
    return {
        "branch": branch,
        "commit": commit,
        "dirty": bool(status) if status is not None else True,
    }


def _run_git_command(repo_root: Path, *args: str) -> Optional[str]:
    allowed_commands = {
        ("branch", "--show-current"),
        ("rev-parse", "HEAD"),
        ("status", "--short"),
    }
    if args not in allowed_commands:
        raise ValueError(f"Unsupported git metadata command: {args}")
    completed = subprocess.run(
        ["git", *args],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=False,
    )
    if completed.returncode != 0:
        return None
    output = completed.stdout.strip()
    return output or None
