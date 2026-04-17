"""Central path resolver for all autodoc artifacts.

All artifact paths flow through this module. Paths are logical paths
relative to the job artifacts root (see get_artifacts_root()), used with
domino_artifacts module for actual I/O.

Directory structure within artifacts:
    docs/          — Generated .docx and .ipynb files
    specs/         — Uploaded YAML spec files
    .autodoc/      — Internal artifacts
        cache.json — Generation results cache
"""

from __future__ import annotations

import logging
import os
from datetime import datetime
from typing import Optional

logger = logging.getLogger(__name__)

_DFS_ARTIFACTS_ROOT = "/mnt"


def get_artifacts_root() -> str:
    configured = (os.environ.get("DOMINO_ARTIFACTS_DIR") or "").strip()
    if configured:
        return configured.rstrip("/")
    return _DFS_ARTIFACTS_ROOT

_layout: Optional["ArtifactLayout"] = None


class ArtifactLayout:
    """Logical path resolver for autodoc artifacts under the job artifacts root.

    Paths returned are relative to get_artifacts_root(). All actual I/O
    goes through domino_artifacts module or filesystem in job containers.
    """

    # -- User-visible paths (relative to dataset root) --

    @property
    def docs_dir(self) -> str:
        return "docs"

    @property
    def specs_dir(self) -> str:
        return "specs"

    # -- Internal paths --

    @property
    def internal_dir(self) -> str:
        return ".autodoc"

    @property
    def generation_cache(self) -> str:
        return ".autodoc/cache.json"

    def run_dir(self, timestamp: datetime | None = None) -> str:
        """Generate docs/<YYYY-MM-DD_HH-MM-SS> directory path for a run.

        Args:
            timestamp: datetime to use. If None, uses current time.

        Returns:
            Path relative to artifacts root, e.g. "docs/2026-05-27_14-30-45"
        """
        if timestamp is None:
            timestamp = datetime.now()
        date_str = timestamp.strftime("%Y-%m-%d_%H-%M-%S")
        return f"docs/{date_str}"


def init_layout() -> ArtifactLayout:
    """Initialize the global artifact layout singleton."""
    global _layout
    if _layout is not None:
        return _layout
    _layout = ArtifactLayout()
    return _layout


def get_layout() -> ArtifactLayout:
    """Return the initialized artifact layout.

    Raises RuntimeError if init_layout() has not been called.
    """
    if _layout is None:
        raise RuntimeError(
            "ArtifactLayout not initialized. Call init_layout() first."
        )
    return _layout


def reset_layout() -> None:
    """Reset the layout singleton. Used only in tests."""
    global _layout
    _layout = None
