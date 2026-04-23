"""Throwaway deploy hint: git HEAD for the repo containing this file.

Delete this file and remove its import from web_app_studio.py when no longer needed.
"""

from __future__ import annotations

import subprocess
from pathlib import Path


def _git_root(start: Path) -> Path | None:
    for p in [start, *start.parents]:
        if (p / ".git").exists():
            return p
    return None


def get_deploy_version_label() -> str:
    here = Path(__file__).resolve().parent
    root = _git_root(here)
    if root is None:
        return "version unavailable"
    try:
        proc = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=str(root),
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return "version unavailable"
    if proc.returncode != 0:
        return "version unavailable"
    h = (proc.stdout or "").strip()
    if not h:
        return "version unavailable"
    return h
