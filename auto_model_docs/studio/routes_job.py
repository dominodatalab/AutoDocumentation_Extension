"""Job-related routes: run, stop, history."""

from __future__ import annotations

from fasthtml.common import *
from starlette.requests import Request

from auth_context import get_viewing_user

from .state import (
    _DOMINO_AVAILABLE,
    domino_client,
    domino_job_store,
)
from .ui_components import (
    _render_job_history_table,
)
from .job_engine import (
    _parse_request,
    _submit_domino_job,
    sync_jobs_for,
)


def _current_owner_id() -> str:
    """Resolve the viewing user's id, or "" if no forwarded token is available.

    This keeps job routes usable when a request arrives without a forwarded
    JWT (e.g. background client-side polls from an idle tab). Matches the
    index route's behavior.
    """
    try:
        return get_viewing_user().id
    except Exception:
        return ""


def register_job_routes(rt):
    """Register all job-related routes on the given rt decorator."""

    async def run(req: Request):
        owner_id = _current_owner_id()
        if not owner_id:
            return _render_job_history_table(owner_id)
        job_request = await _parse_request(req)
        if not job_request.project_id:
            job_id = domino_job_store.create_job(
                owner_id=owner_id, branch=None, tier=None, spec_path=None,
            )
            domino_job_store.update_job(
                job_id, status="failed",
                domino_status="No target project ID. Reload the app with ?projectId= in the URL.",
            )
            return _render_job_history_table(owner_id)
        try:
            await _submit_domino_job(job_request, owner_id)
        except Exception as exc:
            job_id = domino_job_store.create_job(
                owner_id=owner_id, branch=job_request.branch,
                tier=job_request.hardware_tier, spec_path=job_request.spec_path,
                project_id=job_request.project_id,
            )
            domino_job_store.update_job(job_id, status="failed", domino_status=str(exc))
        return _render_job_history_table(owner_id)

    rt("/run")(run)

    async def job_history():
        owner_id = _current_owner_id()
        if not owner_id:
            return _render_job_history_table(owner_id)
        sync_jobs_for(owner_id)
        return _render_job_history_table(owner_id)

    rt("/job-history")(job_history)

    async def cancel_queued_jobs():
        """Cancel all queued (not yet submitted) jobs for the current user."""
        owner_id = _current_owner_id()
        if owner_id and _DOMINO_AVAILABLE:
            domino_job_store.cancel_queued_jobs(owner_id)
        return _render_job_history_table(owner_id)

    rt("/cancel-queued-jobs")(cancel_queued_jobs)

    async def stop_job_history(req: Request):
        """Stop a job and return the updated history table."""
        owner_id = _current_owner_id()
        if not owner_id:
            return _render_job_history_table(owner_id)
        form = await req.form()
        job_id = form.get("job_id")
        if job_id and _DOMINO_AVAILABLE:
            row = domino_job_store.get_job(job_id)
            if row and row.get("owner_id") != owner_id:
                return _render_job_history_table(owner_id)
            if row and row.get("domino_run_id"):
                try:
                    domino_client.stop_job(
                        row["domino_run_id"],
                        project_id=row.get("project_id"),
                    )
                except Exception:
                    pass
            if row:
                domino_job_store.update_job(job_id, status="cancelled")
        return _render_job_history_table(owner_id)

    rt("/stop-job-history")(stop_job_history)
