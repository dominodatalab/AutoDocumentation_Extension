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
    domino_datasets,
    domino_job_store,
    logger,
)
from .job_engine import (
    _parse_request,
    _submit_domino_job,
)


def _current_owner_id() -> str:
    try:
        return auth_context.get_viewing_user().id
    except Exception:
        return ""


def _json(data, status_code: int = 200) -> Response:
    return Response(json.dumps(data), status_code=status_code, media_type="application/json")


def _error_body(exc: HTTPException) -> str:
    d = exc.detail
    if isinstance(d, str):
        return d
    if isinstance(d, dict):
        inner = d.get("detail")
        if isinstance(inner, str):
            return inner
    return "Request failed."


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
            return _json({"error": "Not authenticated."}, 401)
        try:
            job_request = await _parse_request(req)
        except RuntimeError as e:
            return _json({"error": str(e)}, 400)
        if not job_request.project_id:
            return _json({"error": "Project ID is required."}, 400)
        try:
            ensured = domino_datasets.ensure_dataset(job_request.project_id)
            dataset_mount_path = domino_datasets.resolve_dataset_mount_path(ensured)
        except Exception:
            logger.exception("ensure_dataset or mount path resolution failed for project %s", job_request.project_id)
            return _json(
                {"error": "Could not prepare the documentation dataset. Try again later."},
                500,
            )
        try:
            require_domino_job_start(job_request.project_id)
        except HTTPException as e:
            return _json({"error": _error_body(e)}, e.status_code)
        try:
            await _submit_domino_job(job_request, dataset_mount_path)
        except ValueError as e:
            return _json({"error": str(e)}, 400)
        except Exception:
            return _json({"error": "Job submission failed. Try again later."}, 500)
        return _json({"ok": True}, 200)

    rt("/run")(run)

    async def job_history(req: Request):
        owner_id = _current_owner_id()
        if not owner_id:
            return _json({"jobs": []})
        project_id = _resolve_request_project_id(req)
        if not project_id:
            return _json({"jobs": []})
        require_domino_job_list(project_id)
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

