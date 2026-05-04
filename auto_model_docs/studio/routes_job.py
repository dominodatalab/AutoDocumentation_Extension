"""Job-related routes: run, stop, history."""

from __future__ import annotations

from typing import Any, Optional

from fasthtml.common import *
from starlette.requests import Request

import auth_context
from authorization import (
    require_domino_job_list,
    require_domino_job_start,
    require_domino_job_stop,
)

from .state import (
    _resolve_request_project_id,
    _resolve_request_dataset_ids,
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


def _optional_domino_id(raw: Any) -> Optional[str]:
    if not isinstance(raw, str):
        return None
    s = raw.strip()
    return s or None


def _current_owner_id() -> str:
    try:
        return auth_context.get_viewing_user().id
    except Exception:
        return ""


def register_job_routes(rt):

    async def run(req: Request):
        owner_id = _current_owner_id()
        ds_id, snap_id = _resolve_request_dataset_ids(req)
        if not owner_id:
            return _render_job_history_table(owner_id, ds_id, snap_id)
        job_request = await _parse_request(req)
        if not job_request.project_id:
            return _render_job_history_table(owner_id, ds_id, snap_id)
        require_domino_job_start(job_request.project_id)
        try:
            await _submit_domino_job(job_request, owner_id, ds_id, snap_id)
        except Exception as exc:
            if ds_id and snap_id:
                job_id = domino_job_store.create_job(
                    ds_id, snap_id,
                    owner_id=owner_id, branch=job_request.branch,
                    tier=job_request.hardware_tier, spec_path=job_request.spec_path,
                    project_id=job_request.project_id,
                    environment_id=_optional_domino_id(job_request.environment_id),
                    environment_revision_id=_optional_domino_id(job_request.environment_revision_id),
                )
                domino_job_store.update_job(ds_id, snap_id, job_id, status="failed", domino_status=str(exc))
        return _render_job_history_table(owner_id, ds_id, snap_id)

    rt("/run")(run)

    async def job_history(req: Request):
        owner_id = _current_owner_id()
        ds_id, snap_id = _resolve_request_dataset_ids(req)
        if not owner_id:
            return _render_job_history_table(owner_id, ds_id, snap_id)
        project_id = _resolve_request_project_id(req)
        if not project_id:
            return _render_job_history_table(owner_id, ds_id, snap_id)
        require_domino_job_list(project_id)
        if ds_id and snap_id:
            sync_jobs_for(owner_id, ds_id, snap_id)
        return _render_job_history_table(owner_id, ds_id, snap_id)

    rt("/job-history")(job_history)

    async def cancel_queued_jobs(req: Request):
        owner_id = _current_owner_id()
        ds_id, snap_id = _resolve_request_dataset_ids(req)
        if not owner_id:
            return _render_job_history_table(owner_id, ds_id, snap_id)
        project_id = _resolve_request_project_id(req)
        if not project_id:
            return _render_job_history_table(owner_id, ds_id, snap_id)
        require_domino_job_list(project_id)
        if ds_id and snap_id:
            domino_job_store.cancel_queued_jobs(ds_id, snap_id, owner_id)
        return _render_job_history_table(owner_id, ds_id, snap_id)

    rt("/cancel-queued-jobs")(cancel_queued_jobs)

    async def stop_job_history(req: Request):
        owner_id = _current_owner_id()
        ds_id, snap_id = _resolve_request_dataset_ids(req)
        if not owner_id:
            return _render_job_history_table(owner_id, ds_id, snap_id)
        form = await req.form()
        job_id = form.get("job_id")
        if job_id:
            project_id = _resolve_request_project_id(req)
            if not project_id:
                return _render_job_history_table(owner_id, ds_id, snap_id)
            ds_id = form.get("datasetId", "") or ds_id
            snap_id = form.get("snapshotId", "") or snap_id
            if ds_id and snap_id:
                row = domino_job_store.get_job(ds_id, snap_id, job_id)
                if row and row.get("owner_id") != owner_id:
                    return _render_job_history_table(owner_id, ds_id, snap_id)
                if row and row.get("domino_run_id"):
                    require_domino_job_stop(row["domino_run_id"])
                    try:
                        domino_client.stop_job(
                            row["domino_run_id"],
                            project_id=row.get("project_id"),
                        )
                    except Exception:
                        pass
                if row:
                    domino_job_store.update_job(ds_id, snap_id, job_id, status="cancelled")
        return _render_job_history_table(owner_id, ds_id, snap_id)

    rt("/stop-job-history")(stop_job_history)
