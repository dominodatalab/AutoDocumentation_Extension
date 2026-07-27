"""Job-related routes: run, stop, history."""

from __future__ import annotations

import json
from starlette.requests import Request
from starlette.responses import Response

import auth_context

from .state import (
    _max_jobs,
    _resolve_request_project_id,
    domino_job_store,
    logger,
)
from .job_engine import (
    _parse_request,
    submit_from_queue_payload,
    submit_or_enqueue,
)
from .ui_components import studio_datasets_blocking_error

_FAILURE_HINT_CACHE: dict[str, dict[str, str] | None] = {}


def _failure_hint_for_job(job: dict) -> dict[str, str] | None:
    status = (job.get("status") or "").strip().lower()
    if status != "failed":
        return None
    run_id = str(job.get("domino_run_id") or "").strip()
    if not run_id:
        return None
    if run_id in _FAILURE_HINT_CACHE:
        return _FAILURE_HINT_CACHE[run_id]

    import domino_client
    from job_failure_hints import failure_hint_dict

    log_text = domino_client.get_job_log_text(run_id)
    hint = failure_hint_dict(log_text)
    _FAILURE_HINT_CACHE[run_id] = hint
    return hint


def _current_owner_id() -> str:
    try:
        return auth_context.get_viewing_user().id
    except Exception:
        return ""


def _json(data, status_code: int = 200) -> Response:
    return Response(json.dumps(data), status_code=status_code, media_type="application/json")


def _jobs_payload(project_id: str, owner_id: str) -> list:
    if not owner_id or not project_id:
        return []
    try:
        jobs = domino_job_store.get_user_jobs(
            project_id,
            owner_id,
            limit=50,
            max_jobs=_max_jobs(),
            submit_fn=submit_from_queue_payload,
        )
    except RuntimeError:
        return []
    import domino_client
    for j in jobs:
        run_id = str(j.get("domino_run_id") or "").strip()
        j["document_url"] = (
            domino_client.build_autodoc_artifacts_run_url(project_id, run_id) or ""
            if run_id else ""
        )
        hint = _failure_hint_for_job(j)
        if hint:
            j["failure_hint"] = hint
        j.pop("dataset_url", None)
    return jobs


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
        datasets_err = studio_datasets_blocking_error(job_request.project_id)
        if datasets_err:
            _heading, message, detail = datasets_err
            return _json({"error": message, "detail": detail}, 503)
        try:
            result = submit_or_enqueue(owner_id, job_request)
        except ValueError as e:
            return _json({"error": str(e)}, 400)
        except Exception:
            return _json({"error": "Job submission failed. Try again later."}, 500)
        jobs = result.get("jobs") or []
        import domino_client
        for j in jobs:
            run_id = str(j.get("domino_run_id") or "").strip()
            j["document_url"] = (
                domino_client.build_autodoc_artifacts_run_url(job_request.project_id, run_id) or ""
                if run_id else ""
            )
        return _json(
            {
                "ok": True,
                "queued": bool(result.get("queued")),
                "jobs": jobs,
            },
            200,
        )

    rt("/run")(run)

    async def job_history(req: Request):
        owner_id = _current_owner_id()
        if not owner_id:
            return _json({"jobs": []})
        project_id = _resolve_request_project_id(req)
        if not project_id:
            return _json({"jobs": []})
        jobs = _jobs_payload(project_id, owner_id)
        return _json({"jobs": jobs})

    rt("/job-history")(job_history)

    async def cancel_queued_jobs(req: Request):
        owner_id = _current_owner_id()
        if not owner_id:
            return _json({"ok": False, "error": "not authenticated", "jobs": []})
        project_id = _resolve_request_project_id(req)
        if not project_id:
            return _json({"ok": False, "error": "missing project_id", "jobs": []})
        domino_job_store.cancel_queued_jobs(project_id, owner_id)
        jobs = _jobs_payload(project_id, owner_id)
        return _json({"ok": True, "jobs": jobs})

    rt("/cancel-queued-jobs")(cancel_queued_jobs)
