"""Domino job submission, command building, and background polling."""

from __future__ import annotations

from typing import Any, Optional

from starlette.requests import Request

from .state import (
    JobRequest,
    DominoJobRecord,
    _max_jobs,
    domino_client,
    domino_job_store,
    spec_store,
    domino_datasets,
    logger,
)
from .ui_components import (
    _sanitize_optional_int,
    _sanitize_optional_float,
    _db_record_to_dataclass,
)


# ---------------------------------------------------------------------------
# Request parsing
# ---------------------------------------------------------------------------

async def _parse_request(req: Request) -> JobRequest:
    form = await req.form()
    spec_upload = form.get("spec_upload")
    spec_content = None
    spec_filename = None
    if spec_upload and hasattr(spec_upload, "read"):
        content = await spec_upload.read()
        spec_content = content.decode("utf-8", errors="replace")
        spec_filename = getattr(spec_upload, "filename", None)

    project_id = (
        form.get("target_project")
        or form.get("project_id")
        or req.query_params.get("projectId")
    )
    if not project_id:
        raise RuntimeError("No target project ID available. The app requires ?projectId= in the URL.")

    _prov = (form.get("provider") or "anthropic").strip().lower()
    _pbu = (form.get("provider_base_url") or "").strip() or None
    _lang_raw = (form.get("language") or "auto").strip().lower()
    _allowed_lang = {"auto", "python", "r", "sas", "matlab"}
    _language = _lang_raw if _lang_raw in _allowed_lang else "auto"

    return JobRequest(
        spec_path=form.get("spec_path") or None,
        spec_content=spec_content,
        provider=_prov,
        model=form.get("model") or None,
        code_root=form.get("code_root") or None,
        max_files=_sanitize_optional_int(form.get("max_files")),
        workers=_sanitize_optional_int(form.get("workers")),
        planning_workers=_sanitize_optional_int(form.get("planning_workers")),
        timeout=_sanitize_optional_float(form.get("timeout")),
        notebook=form.get("notebook") in ("on", "true", "1", "yes"),
        notebook_path=form.get("notebook_path") or None,
        experiment_names=form.get("experiment_names") or None,
        model_names=form.get("model_names") or None,
        latest_only=form.get("latest_only") in ("on", "true", "1", "yes"),
        verbose=True,
        branch=form.get("branch") or None,
        hardware_tier=form.get("hardware_tier") or None,
        spec_filename=spec_filename,
        project_id=project_id,
        provider_base_url=_pbu,
        language=_language,
    )


# ---------------------------------------------------------------------------
# Domino job command building
# ---------------------------------------------------------------------------

def _build_job_command(req: JobRequest, spec_path: Optional[str], dataset_path: str = "") -> list[str]:
    command = ["python", "/mnt/code/auto_model_docs/main.py"]
    if spec_path:
        command += ["--spec", spec_path]
    if dataset_path:
        command += ["--dataset-path", dataset_path]
    if req.provider:
        command += ["--provider", req.provider]
    if req.model:
        command += ["--model", req.model]
    code_root_arg = (req.code_root or "").strip() or "/mnt/code"
    command += ["--code-root", code_root_arg]
    if req.max_files:
        command += ["--max-files", str(req.max_files)]
    if req.workers:
        command += ["--generation-workers", str(req.workers)]
    if req.planning_workers:
        command += ["--planning-workers", str(req.planning_workers)]
    if req.timeout:
        command += ["--timeout", str(req.timeout)]
    if req.provider_base_url:
        command += ["--provider-base-url", req.provider_base_url]
    if req.experiment_names:
        command += ["--filtered-experiments", req.experiment_names]
    if req.model_names:
        command += ["--filtered-models", req.model_names]
    if req.latest_only:
        command += ["--latest-only"]
    command += ["--notebook"]
    if req.verbose:
        command += ["--verbose"]
    command += ["--language", req.language]
    return command


def _build_job_command_str(req: JobRequest, spec_path: Optional[str], dataset_path: str = "") -> str:
    import shlex
    parts = _build_job_command(req, spec_path, dataset_path)
    return " ".join(shlex.quote(p) for p in parts)


# ---------------------------------------------------------------------------
# Domino job submission
# ---------------------------------------------------------------------------

async def _submit_domino_job(
    req: JobRequest, owner_id: str, dataset_id: str, snapshot_id: str,
) -> DominoJobRecord:
    spec_path: Optional[str] = None
    dataset_path = ""

    if dataset_id:
        try:
            detail = domino_datasets.get_dataset_detail(dataset_id)
            dataset_path = detail.get("datasetPath", "")
        except Exception:
            pass

    if req.spec_content and req.spec_filename:
        if not dataset_id:
            raise ValueError("datasetId is required to save the uploaded spec.")
        saved = spec_store.save_spec(dataset_id, req.spec_filename, req.spec_content)
        if dataset_path:
            spec_path = f"{dataset_path}/{saved}"
    elif req.spec_path:
        if req.spec_path.startswith("dataset://"):
            parts = req.spec_path[len("dataset://"):].split("/", 1)
            dataset_name = parts[0]
            file_path = parts[1] if len(parts) > 1 else ""
            if dataset_path:
                spec_path = f"{dataset_path}/{file_path}"
            else:
                mount_prefix = domino_datasets.get_dataset_mount_prefix()
                spec_path = f"{mount_prefix}/{dataset_name}/{file_path}"
        else:
            spec_path = req.spec_path

    if not spec_path:
        raise ValueError("A spec file is required. Please select or upload a spec before generating documentation.")

    if req.spec_path and req.spec_path.startswith("dataset://") and snapshot_id:
        ds_relative = req.spec_path[len("dataset://"):].split("/", 1)
        if len(ds_relative) > 1:
            from dataset_manager import DatasetManager
            if not DatasetManager.file_exists(snapshot_id, ds_relative[1]):
                raise ValueError(
                    "The selected spec file no longer exists in the dataset. "
                    "It may have been deleted. Please select or upload a spec file and try again."
                )

    command_str = _build_job_command_str(req, spec_path, dataset_path)

    job_id = domino_job_store.create_job(
        dataset_id, snapshot_id,
        owner_id=owner_id,
        branch=req.branch,
        tier=req.hardware_tier,
        spec_path=spec_path,
        command=command_str,
        project_id=req.project_id,
    )

    active = domino_job_store.count_active_jobs(dataset_id, snapshot_id, owner_id)
    if active > _max_jobs():
        row = domino_job_store.get_job(dataset_id, snapshot_id, job_id)
        return _db_record_to_dataclass(row)

    try:
        run_id = domino_client.submit_job(
            command_str,
            branch=req.branch,
            tier_id=req.hardware_tier,
            project_id=req.project_id,
        )
        job_url = domino_client.build_job_url(run_id, project_id=req.project_id)
        domino_job_store.update_job(
            dataset_id, snapshot_id, job_id,
            status="submitted",
            domino_run_id=run_id,
            job_url=job_url,
        )
    except Exception as exc:
        domino_job_store.update_job(
            dataset_id, snapshot_id, job_id,
            status="failed",
            domino_status=str(exc),
        )
        logger.error("Domino job submission failed: %s", exc, exc_info=True)

    row = domino_job_store.get_job(dataset_id, snapshot_id, job_id)
    return _db_record_to_dataclass(row)


# ---------------------------------------------------------------------------
# Request-driven job sync
# ---------------------------------------------------------------------------

def _refresh_active_jobs_for(owner_id: str, dataset_id: str, snapshot_id: str) -> None:
    from datetime import datetime, timezone

    active_jobs = [
        j for j in domino_job_store.get_active_jobs(dataset_id, snapshot_id)
        if j.get("owner_id") == owner_id
    ]
    for row in active_jobs:
        run_id = row.get("domino_run_id")
        if not run_id:
            continue
        try:
            status_info = domino_client.get_job_status(run_id)
            domino_status = status_info.get("domino_status", "")
            mapped = status_info.get("local_status", "submitted")
            updates: dict[str, Any] = {}
            if domino_status != row.get("domino_status"):
                updates["domino_status"] = domino_status
            if mapped != row.get("status"):
                updates["status"] = mapped
            if mapped in ("succeeded", "failed", "cancelled"):
                updates["completed_at"] = datetime.now(tz=timezone.utc).isoformat()
            if updates:
                domino_job_store.update_job(dataset_id, snapshot_id, row["id"], **updates)
        except Exception as exc:
            logger.warning("Status sync failed for run %s: %s", run_id, exc)


def _promote_queued_jobs_for(owner_id: str, dataset_id: str, snapshot_id: str) -> None:
    active = domino_job_store.count_active_jobs(dataset_id, snapshot_id, owner_id)
    if active > _max_jobs():
        return
    oldest = domino_job_store.get_oldest_queued_job(dataset_id, snapshot_id, owner_id)
    if not oldest or oldest.get("domino_run_id"):
        return
    try:
        cmd = oldest.get("command", "")
        run_id = domino_client.submit_job(
            cmd,
            branch=oldest.get("branch"),
            tier_id=oldest.get("hardware_tier"),
            project_id=oldest.get("project_id"),
        )
        job_url = domino_client.build_job_url(run_id, project_id=oldest.get("project_id"))
        domino_job_store.update_job(
            dataset_id, snapshot_id, oldest["id"],
            status="submitted",
            domino_run_id=run_id,
            job_url=job_url,
        )
    except Exception as exc:
        logger.warning("Failed to promote queued job %s: %s", oldest["id"], exc)


def sync_jobs_for(owner_id: str, dataset_id: str, snapshot_id: str) -> None:
    try:
        _refresh_active_jobs_for(owner_id, dataset_id, snapshot_id)
        _promote_queued_jobs_for(owner_id, dataset_id, snapshot_id)
    except Exception as exc:
        logger.warning("sync_jobs_for(%s) failed: %s", owner_id, exc)


def _reconcile_stale_jobs(dataset_id: str, snapshot_id: str) -> None:
    try:
        domino_job_store.reconcile_stale_jobs(dataset_id, snapshot_id)
    except Exception as exc:
        logger.warning("Reconcile stale jobs failed: %s", exc)
