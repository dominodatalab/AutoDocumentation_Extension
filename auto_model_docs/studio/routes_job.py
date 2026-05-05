"""Job-related routes: run, stop, history."""

from __future__ import annotations

import json
from typing import Any

from starlette.requests import Request
from starlette.responses import Response

import auth_context
from authorization import (
    require_domino_job_list,
    require_domino_job_start,
)

from .state import (
    _resolve_request_project_id,
    _resolve_request_dataset_ids,
    domino_job_store,
)
from .job_engine import (
    _parse_request,
    _submit_domino_job,
    sync_jobs_for,
)


def _domino_id_str(raw: Any) -> str:
    if not isinstance(raw, str):
        return ""
    return raw.strip()


def _current_owner_id() -> str:
    try:
        return auth_context.get_viewing_user().id
    except Exception:
        return ""


def _json(data, status_code: int = 200) -> Response:
    return Response(json.dumps(data), status_code=status_code, media_type="application/json")


def _jobs_payload(owner_id: str, ds_id: str, snap_id: str) -> list:
    if not ds_id or not snap_id or not owner_id:
        return []
    try:
        return domino_job_store.get_user_jobs(ds_id, snap_id, owner_id, limit=50)
    except RuntimeError:
        return []


def register_job_routes(rt):

    async def run(req: Request):
        owner_id = _current_owner_id()
        ds_id, snap_id = _resolve_request_dataset_ids(req)
        if not owner_id:
            return _json({"ok": False, "error": "not authenticated", "jobs": []})
        job_request = await _parse_request(req)
        if not job_request.project_id:
            return _json({"ok": False, "error": "missing project_id", "jobs": _jobs_payload(owner_id, ds_id, snap_id)})
        require_domino_job_start(job_request.project_id)
        error = None
        try:
            await _submit_domino_job(job_request, owner_id, ds_id, snap_id)
        except Exception as exc:
            error = str(exc)
            if ds_id and snap_id:
                job_id = domino_job_store.create_job(
                    ds_id, snap_id,
                    owner_id=owner_id, branch=job_request.branch,
                    tier=job_request.hardware_tier, spec_path=job_request.spec_path,
                    environment_id=_domino_id_str(job_request.environment_id),
                    environment_revision_id=_domino_id_str(job_request.environment_revision_id),
                    project_id=job_request.project_id,
                )
                domino_job_store.update_job(ds_id, snap_id, job_id, status="failed", domino_status=error)
        return _json({"ok": error is None, "error": error, "jobs": _jobs_payload(owner_id, ds_id, snap_id)})

    rt("/run")(run)

    async def job_history(req: Request):
        owner_id = _current_owner_id()
        ds_id, snap_id = _resolve_request_dataset_ids(req)
        if not owner_id:
            return _json({"jobs": []})
        project_id = _resolve_request_project_id(req)
        if not project_id:
            return _json({"jobs": []})
        require_domino_job_list(project_id)
        if ds_id and snap_id:
            sync_jobs_for(owner_id, ds_id, snap_id)
        return _json({"jobs": _jobs_payload(owner_id, ds_id, snap_id)})

    rt("/job-history")(job_history)

    async def cancel_queued_jobs(req: Request):
        owner_id = _current_owner_id()
        ds_id, snap_id = _resolve_request_dataset_ids(req)
        if not owner_id:
            return _json({"ok": False, "error": "not authenticated", "jobs": []})
        project_id = _resolve_request_project_id(req)
        if not project_id:
            return _json({"ok": False, "error": "missing project_id", "jobs": []})
        require_domino_job_list(project_id)
        if ds_id and snap_id:
            domino_job_store.cancel_queued_jobs(ds_id, snap_id, owner_id)
        return _json({"ok": True, "jobs": _jobs_payload(owner_id, ds_id, snap_id)})

    rt("/cancel-queued-jobs")(cancel_queued_jobs)

