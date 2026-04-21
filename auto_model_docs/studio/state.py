"""Shared mutable state, core types, and helpers used across all studio modules."""

from __future__ import annotations

import importlib.util as _imputil
import logging
import os
import ctypes as _ctypes
from collections import deque
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Deque, Optional

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


class _RingBufferLogHandler(logging.Handler):
    """In-process ring buffer that keeps the last N formatted log records.

    Attached to the root logger so /logs can expose recent app output for
    troubleshooting without reading container stdout.
    """

    def __init__(self, capacity: int = 2000):
        super().__init__()
        self.buffer: Deque[str] = deque(maxlen=capacity)

    def emit(self, record: logging.LogRecord) -> None:
        try:
            self.buffer.append(self.format(record))
        except Exception:
            self.handleError(record)

    def snapshot(self) -> list[str]:
        return list(self.buffer)


log_buffer = _RingBufferLogHandler(capacity=2000)
log_buffer.setLevel(logging.DEBUG)
log_buffer.setFormatter(logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
))
_root = logging.getLogger()
if not any(isinstance(h, _RingBufferLogHandler) for h in _root.handlers):
    _root.addHandler(log_buffer)

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
    spec_path: Optional[str]
    spec_content: Optional[str]
    provider: str
    model: Optional[str]
    code_root: Optional[str]
    max_files: Optional[int]
    workers: Optional[int]
    planning_workers: Optional[int]
    timeout: Optional[float]
    notebook: bool
    notebook_path: Optional[str]
    experiment_names: Optional[str]  # Comma-separated list
    model_names: Optional[str]  # Comma-separated list
    latest_only: bool
    verbose: bool  # Enable verbose logging
    branch: Optional[str] = None
    hardware_tier: Optional[str] = None
    spec_filename: Optional[str] = None  # original uploaded filename
    project_id: Optional[str] = None     # target Domino project (from ?projectId=)


@dataclass
class DominoJobRecord:
    id: str                              # local UUID
    owner_id: str                        # Domino user id (from /v4/users/self)
    domino_run_id: Optional[str] = None
    branch: Optional[str] = None
    hardware_tier: Optional[str] = None
    status: str = "queued"               # queued | submitted | running | succeeded | failed | cancelled
    domino_status: Optional[str] = None
    job_url: Optional[str] = None
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

# Target project context — captured from the ?projectId query param on
# first request and used by all components so that specs, jobs, output,
# and history are scoped to the target project, not the app's own project.
_TARGET_PROJECT_ID: Optional[str] = None


# ---------------------------------------------------------------------------
# Target project helpers
# ---------------------------------------------------------------------------

def _set_target_project(project_id: str) -> bool:
    """Capture the target project from the ?projectId query param.

    Called on every page load but only acts on the first call.
    Initializes ArtifactLayout and DatasetStore for the target project.
    Returns ``True`` when the project was newly captured (first load),
    ``False`` when it was already set.
    """
    import studio.state as _self  # avoid stale module-level refs
    from artifact_layout import init_layout
    from dataset_store import init_store, AUTODOC_DATASET_NAME

    if _self._TARGET_PROJECT_ID is not None:
        return False  # already captured

    _self._TARGET_PROJECT_ID = project_id

    info = domino_client.resolve_project(project_id)
    if info:
        init_layout()

        try:
            ds = domino_datasets.ensure_dataset(
                project_id=project_id,
                name=AUTODOC_DATASET_NAME,
                description="Auto Model Docs artifacts",
            )
            ds_id = ds.get("id") or ""
            if not ds_id:
                raise RuntimeError(
                    f"Dataset '{AUTODOC_DATASET_NAME}' created/found but has no ID. "
                    f"Raw response: {ds}"
                )
            snap_id = ds.get("rwSnapshotId") or ""
            if not snap_id:
                snap_id = domino_datasets.get_rw_snapshot_id(ds_id, project_id) or ""
            if not snap_id:
                raise RuntimeError(
                    f"Could not resolve snapshot ID for dataset '{ds_id}'. "
                    f"The dataset may still be initializing."
                )
            init_store(ds_id, snap_id, project_id)
        except Exception as exc:
            logger.error(
                "Failed to initialize DatasetStore for project %s: %s",
                project_id, exc, exc_info=True,
            )
            raise RuntimeError(
                f"Cannot initialize artifact storage for project {project_id}. "
                f"Check dataset permissions and Domino API availability. "
                f"Error: {exc}"
            ) from exc

        domino_job_store.init_db()
        return True

    return True


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
    """Extract project ID from request query params.

    Intentionally does NOT fall back to any process-global target project;
    that would leak the first-arriving user's project to later requests from
    other users. Callers must supply ``projectId`` on every request.
    """
    for key in ("projectId", "project_id"):
        pid = req.query_params.get(key)
        if pid:
            return pid
    return None
