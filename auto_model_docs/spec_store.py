"""Manages uploaded spec files via the Domino Datasets API.

All I/O goes through DatasetManager (dataset_manager.py). The (dataset_id,
snapshot_id) pair is read from dataset_ctx and must be set by the caller
before invoking any function here.
"""

from __future__ import annotations

import logging
from typing import Any
from uuid import uuid4

from artifact_layout import get_layout
from dataset_ctx import get_dataset_ctx
from dataset_manager import DatasetManager

logger = logging.getLogger(__name__)


def save_spec(original_filename: str, content: str) -> str:
    """Write spec content to the autodoc dataset with a UUID prefix.

    Returns the dataset-relative path of the saved file.
    """
    ctx = get_dataset_ctx()
    layout = get_layout()
    safe_name = original_filename.rsplit("/", 1)[-1].rsplit("\\", 1)[-1]
    relative_path = f"{layout.specs_dir}/{uuid4()}_{safe_name}"
    DatasetManager.write_file(ctx.dataset_id, relative_path, content.encode("utf-8"))
    return relative_path


def list_specs() -> list[dict[str, Any]]:
    """Return metadata for all saved spec files."""
    ctx = get_dataset_ctx()
    layout = get_layout()
    try:
        files = DatasetManager.list_files(ctx.snapshot_id, layout.specs_dir)
    except Exception as exc:
        logger.warning("list_specs failed: %s", exc)
        return []
    results: list[dict[str, Any]] = []
    for f in files:
        if f.get("isDirectory"):
            continue
        results.append({
            "name": f["fileName"],
            "path": f"{layout.specs_dir}/{f['fileName']}",
            "size_kb": round((f.get("sizeInBytes") or 0) / 1024, 1),
            "created_at": f.get("lastModified", ""),
        })
    return results
