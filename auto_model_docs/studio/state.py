"""Shared mutable state, core types, and helpers used across all studio modules."""

from __future__ import annotations

import importlib.util as _imputil
import logging
import os
import sys
import ctypes as _ctypes
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

# ---------------------------------------------------------------------------
# Logging setup
# ---------------------------------------------------------------------------

logger = logging.getLogger(__name__)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)
for _mod_name in ("domino_datasets", "domino_client", "auth_context"):
    logging.getLogger(_mod_name).setLevel(logging.INFO)

logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)

# ---------------------------------------------------------------------------
# Sibling module imports  (domino_client, domino_job_store, etc.)
# ---------------------------------------------------------------------------

def _import_sibling(name: str):
    """Import a .py file from the auto_model_docs directory (parent of studio/)."""
    import sys
    # studio/state.py -> studio/ -> auto_model_docs/
    path = Path(__file__).resolve().parent.parent / f"{name}.py"
    if not path.exists():
        raise FileNotFoundError(f"Sibling module not found: {path}")
    spec = _imputil.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Could not load module spec for {path}")
    mod = _imputil.module_from_spec(spec)
    # Register in sys.modules so @dataclass and other introspection works
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


# Preload conda's libstdc++ to fix CXXABI version mismatch in Domino Apps.
try:
    for _candidate in (
        os.path.join(os.environ.get("CONDA_PREFIX", "/opt/conda"), "lib", "libstdc++.so.6"),
        "/opt/conda/lib/libstdc++.so.6",
    ):
        if os.path.isfile(_candidate):
            try:
                _ctypes.CDLL(_candidate, mode=_ctypes.RTLD_GLOBAL)
                break
            except OSError:
                continue
except Exception:
    pass

import auth_context  # type: ignore  # normal import; must not be re-loaded via _import_sibling or ContextVars duplicate

domino_client = _import_sibling("domino_client")
domino_job_store = _import_sibling("domino_job_store")
spec_store = _import_sibling("spec_store")
domino_datasets = _import_sibling("domino_datasets")


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------

@dataclass
class JobRequest:
    spec_path: str
    provider: str
    model: str
    code_root: str
    max_files: int
    workers: int
    planning_workers: int
    timeout: float
    notebook: bool
    notebook_path: str
    filtered_experiment_names: str
    filtered_model_names: str
    latest_only: bool
    verbose: bool
    hardware_tier: str
    environment_id: str
    environment_revision_id: str
    project_id: str
    provider_base_url: str
    max_retries: int
    initial_backoff: float
    max_backoff: float
    backoff_jitter: float
    notebook_from_cache: bool


@dataclass
class DominoJobRecord:
    id: str                              # local UUID
    owner_id: str                        # Domino user id (from /v4/users/self)
    domino_run_id: Optional[str] = None
    hardware_tier: Optional[str] = None
    status: str = "queued"               # queued | submitted | running | succeeded | failed | cancelled
    domino_status: Optional[str] = None
    job_url: Optional[str] = None
    dataset_id: Optional[str] = None
    spec_path: Optional[str] = None
    submitted_at: Optional[str] = None
    completed_at: Optional[str] = None
    error: Optional[str] = None
    project_id: Optional[str] = None     # target Domino project ID


@dataclass
class EnvironmentWarning:
    """A startup environment warning."""
    level: str   # "info" | "warning" | "error"
    message: str
    action: str  # suggested action


# ---------------------------------------------------------------------------
# Mutable global state
# ---------------------------------------------------------------------------

_STARTUP_WARNINGS: list = []




# ---------------------------------------------------------------------------
# Path helpers
# ---------------------------------------------------------------------------

def _get_default_code_root() -> Path:
    """Return the default code root: /mnt/code for git projects,
    /mnt for DFS projects, or cwd as fallback."""
    if Path("/mnt/code").exists():
        return Path("/mnt/code")
    if Path("/mnt").exists():
        return Path("/mnt")
    return Path(".")


def _get_default_spec_path() -> Path:
    return Path(__file__).resolve().parent.parent / "doc_spec.yaml"


def _max_jobs() -> int:
    return int(os.environ.get("AUTODOC_MAX_JOBS", "1"))


def _resolve_request_project_id(req) -> Optional[str]:
    for key in ("projectId", "project_id"):
        raw = req.query_params.get(key)
        if raw:
            s = str(raw).strip()
            if s:
                return s
    return None


def _resolve_request_dataset_ids(req) -> tuple[str, str]:
    """Extract (dataset_id, snapshot_id) from request params (query or form).

    Returns ("", "") if not provided.
    """
    dataset_id = req.query_params.get("datasetId", "")
    snapshot_id = req.query_params.get("snapshotId", "")
    return dataset_id, snapshot_id
