"""Job-related routes: run, stop, history."""

from __future__ import annotations

import json
from starlette.exceptions import HTTPException
from starlette.requests import Request
from starlette.responses import Response

import auth_context
from authorization import (
    require_domino_job_list,
    require_domino_job_start,
)

from .state import (
    _resolve_request_project_id,
    domino_job_store,
)
from .job_engine import (
    _parse_request,
    _submit_domino_job,
    sync_jobs_for,
)


def _current_owner_id() -> str:
    try:
        return auth_context.get_viewing_user().id
    except Exception:
        return ""


def _json(data, status_code: int = 200) -> Response:
    return Response(json.dumps(data), status_code=status_code, media_type="application/json")


def _jobs_payload(owner_id: str) -> list:
    if not owner_id:
        return []
    try:
        return domino_job_store.get_user_jobs("", "", owner_id, limit=50)
    except RuntimeError:
        return []


def register_job_routes(rt):

    async def run(req: Request):
        owner_id = _current_owner_id()
        if not owner_id:
            return Response(status_code=401)
        try:
            job_request = await _parse_request(req)
        except RuntimeError:
            return Response(status_code=400)
        if not job_request.project_id:
            return Response(status_code=400)
        try:
            require_domino_job_start(job_request.project_id)
        except HTTPException as e:
            return Response(status_code=e.status_code)
        try:
            await _submit_domino_job(job_request)
        except ValueError:
            return Response(status_code=400)
        except Exception:
            return Response(status_code=500)
        return Response(status_code=204)

    rt("/run")(run)

    async def job_history(req: Request):
        owner_id = _current_owner_id()
        if not owner_id:
            return _json({"jobs": []})
        project_id = _resolve_request_project_id(req)
        if not project_id:
            return _json({"jobs": []})
        require_domino_job_list(project_id)
        sync_jobs_for(owner_id)
        return _json({"jobs": _jobs_payload(owner_id)})

    rt("/job-history")(job_history)

    async def cancel_queued_jobs(req: Request):
        owner_id = _current_owner_id()
        if not owner_id:
            return _json({"ok": False, "error": "not authenticated", "jobs": []})
        project_id = _resolve_request_project_id(req)
        if not project_id:
            return _json({"ok": False, "error": "missing project_id", "jobs": []})
        require_domino_job_list(project_id)
        domino_job_store.cancel_queued_jobs("", "", owner_id)
        return _json({"ok": True, "jobs": _jobs_payload(owner_id)})

    rt("/cancel-queued-jobs")(cancel_queued_jobs)

