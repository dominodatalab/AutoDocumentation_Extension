"""Job submission index backed by a JSON file in the Datasets API.

Tracks which jobs were submitted by this app, with metadata needed for
display (user, branch, spec, tier). Actual job status comes live from
the Domino Jobs API - we don't duplicate it.

The index file lives at ``.autodoc/jobs_index.json`` in the autodoc dataset,
read/written via DatasetManager. Callers must pass (dataset_id, snapshot_id)
explicitly to every function that performs I/O.

Local queue: jobs waiting for a slot are tracked in the index with
``domino_run_id: null``. Once submitted, the run id is filled in and status
comes from Domino.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any, Optional


def _json_safe_optional_str(val: Any) -> Optional[str]:
    if not isinstance(val, str):
        return None
    return val


def _json_safe_required_str(val: Any) -> str:
    if isinstance(val, str):
        return val
    return str(val) if val is not None else ""
from uuid import uuid4

logger = logging.getLogger(__name__)

_INDEX_PATH = ".autodoc/jobs_index.json"
_MAX_COMPLETED_JOBS = 50
_COMPLETED_STATUSES = {"succeeded", "failed", "cancelled"}


def _read_index(dataset_id: str, snapshot_id: str) -> list[dict[str, Any]]:
    from dataset_manager import DatasetManager
    try:
        if not DatasetManager.file_exists(snapshot_id, _INDEX_PATH):
            return []
        content = DatasetManager.read_file(snapshot_id, _INDEX_PATH)
        return json.loads(content)
    except Exception as exc:
        logger.warning("Failed to read job index: %s", exc)
        return []


def _write_index(dataset_id: str, snapshot_id: str, jobs: list[dict[str, Any]]) -> None:
    from dataset_manager import DatasetManager

    active = [j for j in jobs if j.get("status") not in _COMPLETED_STATUSES]
    completed = [j for j in jobs if j.get("status") in _COMPLETED_STATUSES]

    by_owner: dict[str, list[dict[str, Any]]] = {}
    for j in completed:
        by_owner.setdefault(j.get("owner_id", ""), []).append(j)
    pruned_completed = []
    for owner_jobs in by_owner.values():
        owner_jobs.sort(key=lambda j: j.get("submitted_at", ""), reverse=True)
        pruned_completed.extend(owner_jobs[:_MAX_COMPLETED_JOBS])

    jobs = active + pruned_completed

    content = json.dumps(jobs, indent=2).encode("utf-8")
    DatasetManager.write_file(dataset_id, _INDEX_PATH, content)


def _now_iso() -> str:
    return datetime.now(tz=timezone.utc).isoformat()


def create_job(
    dataset_id: str,
    snapshot_id: str,
    owner_id: str,
    branch: Optional[str],
    tier: Optional[str],
    spec_path: Optional[str],
    environment_id: str,
    environment_revision_id: str,
    command: Optional[str] = None,
    job_id: Optional[str] = None,
    project_id: Optional[str] = None,
) -> str:
    jid = job_id or str(uuid4())
    jobs = _read_index(dataset_id, snapshot_id)
    jobs.append({
        "id": _json_safe_required_str(jid),
        "owner_id": _json_safe_required_str(owner_id),
        "domino_run_id": None,
        "branch": _json_safe_optional_str(branch),
        "hardware_tier": _json_safe_optional_str(tier),
        "status": "queued",
        "domino_status": None,
        "job_url": None,
        "spec_path": _json_safe_optional_str(spec_path),
        "command": _json_safe_optional_str(command),
        "submitted_at": _now_iso(),
        "completed_at": None,
        "project_id": _json_safe_optional_str(project_id),
        "environment_id": _json_safe_optional_str(environment_id),
        "environment_revision_id": _json_safe_optional_str(environment_revision_id),
    })
    _write_index(dataset_id, snapshot_id, jobs)
    return jid


def update_job(dataset_id: str, snapshot_id: str, job_id: str, **fields: Any) -> None:
    if not fields:
        return
    jobs = _read_index(dataset_id, snapshot_id)
    for job in jobs:
        if job["id"] == job_id:
            job.update(fields)
            break
    _write_index(dataset_id, snapshot_id, jobs)


def get_job(dataset_id: str, snapshot_id: str, job_id: str) -> Optional[dict[str, Any]]:
    jobs = _read_index(dataset_id, snapshot_id)
    for job in jobs:
        if job["id"] == job_id:
            return job
    return None


def get_user_jobs(dataset_id: str, snapshot_id: str, owner_id: str, limit: int = 50) -> list[dict[str, Any]]:
    jobs = _read_index(dataset_id, snapshot_id)
    owner_jobs = [j for j in jobs if j.get("owner_id") == owner_id]
    owner_jobs.sort(key=lambda j: j.get("submitted_at", ""), reverse=True)
    return owner_jobs[:limit]


def count_active_jobs(dataset_id: str, snapshot_id: str, owner_id: str) -> int:
    active_statuses = {"queued", "submitted", "pending", "running"}
    jobs = _read_index(dataset_id, snapshot_id)
    return sum(
        1 for j in jobs
        if j.get("owner_id") == owner_id and j.get("status") in active_statuses
    )


def get_oldest_queued_job(dataset_id: str, snapshot_id: str, owner_id: str) -> Optional[dict[str, Any]]:
    jobs = _read_index(dataset_id, snapshot_id)
    queued = [
        j for j in jobs
        if j.get("owner_id") == owner_id and j.get("status") == "queued"
    ]
    if not queued:
        return None
    queued.sort(key=lambda j: j.get("submitted_at", ""))
    return queued[0]


def get_active_jobs(dataset_id: str, snapshot_id: str) -> list[dict[str, Any]]:
    active_statuses = {"submitted", "pending", "running"}
    jobs = _read_index(dataset_id, snapshot_id)
    return [j for j in jobs if j.get("status") in active_statuses]


def get_queued_owner_ids(dataset_id: str, snapshot_id: str) -> list[str]:
    jobs = _read_index(dataset_id, snapshot_id)
    return list({
        j["owner_id"] for j in jobs
        if j.get("status") == "queued"
    })


def reconcile_stale_jobs(dataset_id: str, snapshot_id: str) -> None:
    jobs = _read_index(dataset_id, snapshot_id)
    changed = False
    for job in jobs:
        if (
            job.get("status") in ("submitted", "pending", "running")
            and not job.get("domino_run_id")
        ):
            job["status"] = "failed"
            job["domino_status"] = "App restarted"
            changed = True
    if changed:
        _write_index(dataset_id, snapshot_id, jobs)


def cancel_queued_jobs(dataset_id: str, snapshot_id: str, owner_id: str) -> None:
    jobs = _read_index(dataset_id, snapshot_id)
    changed = False
    for job in jobs:
        if (
            job.get("owner_id") == owner_id
            and job.get("status") == "queued"
            and not job.get("domino_run_id")
        ):
            job["status"] = "cancelled"
            changed = True
    if changed:
        _write_index(dataset_id, snapshot_id, jobs)
