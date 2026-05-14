"""In-process job submission index (per app instance).

Tracks which jobs were submitted by this app, with metadata needed for
display (user, branch, spec, tier). Actual job status comes live from
the Domino Jobs API when synced.

Local queue: jobs waiting for a slot are tracked with ``domino_run_id: null``.
Once submitted, the run id is filled in and status comes from Domino.
"""

from __future__ import annotations

import json
import threading
from datetime import datetime, timezone
from typing import Any, Optional
from uuid import uuid4

_MAX_COMPLETED_JOBS = 50
_COMPLETED_STATUSES = {"succeeded", "failed", "cancelled"}

_lock = threading.Lock()
_buckets: dict[tuple[str, str], list[dict[str, Any]]] = {}


def reset_store() -> None:
    with _lock:
        _buckets.clear()


def _json_safe_optional_str(val: Any) -> Optional[str]:
    if not isinstance(val, str):
        return None
    return val


def _json_safe_required_str(val: Any) -> str:
    if isinstance(val, str):
        return val
    return str(val) if val is not None else ""


def _bucket_key(dataset_id: str, snapshot_id: str) -> tuple[str, str]:
    return (dataset_id, snapshot_id)


def _prune(jobs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    active = [j for j in jobs if j.get("status") not in _COMPLETED_STATUSES]
    completed = [j for j in jobs if j.get("status") in _COMPLETED_STATUSES]

    by_owner: dict[str, list[dict[str, Any]]] = {}
    for j in completed:
        by_owner.setdefault(j.get("owner_id", ""), []).append(j)
    pruned_completed: list[dict[str, Any]] = []
    for owner_jobs in by_owner.values():
        owner_jobs.sort(key=lambda j: j.get("submitted_at", ""), reverse=True)
        pruned_completed.extend(owner_jobs[:_MAX_COMPLETED_JOBS])

    return active + pruned_completed


def _read_index(dataset_id: str, snapshot_id: str) -> list[dict[str, Any]]:
    with _lock:
        raw = _buckets.get(_bucket_key(dataset_id, snapshot_id))
        if not raw:
            return []
        return json.loads(json.dumps(raw))


def _write_index(dataset_id: str, snapshot_id: str, jobs: list[dict[str, Any]]) -> None:
    jobs = _prune(jobs)
    with _lock:
        _buckets[_bucket_key(dataset_id, snapshot_id)] = json.loads(json.dumps(jobs))


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
    dataset_url: Optional[str] = None,
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
        "dataset_id": _json_safe_optional_str(dataset_id),
        "dataset_url": _json_safe_optional_str(dataset_url),
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
