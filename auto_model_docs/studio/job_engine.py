"""Domino job submission, command building, and background polling."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Optional

from starlette.requests import Request

_root = Path(__file__).resolve().parent.parent
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))

from default_consts import (
    ALLOWED_LANGUAGES,
    DEFAULT_GENERATION_WORKERS,
    DEFAULT_LANGUAGE,
    DEFAULT_LLM_BACKOFF_JITTER,
    DEFAULT_LLM_INITIAL_BACKOFF,
    DEFAULT_LLM_MAX_BACKOFF,
    DEFAULT_LLM_MAX_RETRIES,
    DEFAULT_MAX_FILES,
    DEFAULT_PLANNING_WORKERS,
    DEFAULT_PROVIDER,
    DEFAULT_TIMEOUT,
)

from .state import (
    JobRequest,
    DominoJobRecord,
    _max_jobs,
    domino_client,
    domino_job_store,
    domino_datasets,
    logger,
)
from .ui_components import (
    _sanitize_optional_int,
    _sanitize_optional_float,
    _db_record_to_dataclass,
)


def _validate_job_inputs(req: JobRequest, dataset_path: str, spec_path: str) -> None:
    if not spec_path or not str(spec_path).strip():
        raise ValueError("A spec file is required. Please select or upload a spec before generating documentation.")
    if not (dataset_path or "").strip():
        raise ValueError("Dataset mount path is required. Ensure a dataset is selected.")
    if not (req.code_root or "").strip():
        raise ValueError("Code root is required. Choose a source code root path before generating documentation.")
    if not (req.provider or "").strip():
        raise ValueError("Provider is required.")


def _checkbox_truthy(raw: Any) -> bool:
    if raw is None:
        return False
    s = str(raw).strip().lower()
    return s in ("on", "true", "1", "yes")


def _form_str(form: Any, key: str) -> str:
    v = form.get(key)
    if v is None:
        return ""
    return str(v).strip()


def _optional_domino_id(raw: Any) -> Optional[str]:
    if not isinstance(raw, str):
        return None
    s = raw.strip()
    return s or None


def _form_int(form: Any, key: str, default: int) -> int:
    v = _sanitize_optional_int(form.get(key))
    return default if v is None else v


def _form_float(form: Any, key: str, default: float) -> float:
    v = _sanitize_optional_float(form.get(key))
    return default if v is None else v


# ---------------------------------------------------------------------------
# Request parsing
# ---------------------------------------------------------------------------

async def _parse_request(req: Request) -> JobRequest:
    form = await req.form()

    project_id = (
        (req.query_params.get("projectId") or req.query_params.get("project_id") or "").strip()
        or None
    )
    if not project_id:
        raise RuntimeError("No target project ID available. The app requires ?projectId= on the request URL.")

    _prov = (_form_str(form, "provider") or DEFAULT_PROVIDER).strip().lower()
    _lang_raw = (_form_str(form, "language") or DEFAULT_LANGUAGE).strip().lower()
    _language = _lang_raw if _lang_raw in ALLOWED_LANGUAGES else DEFAULT_LANGUAGE

    return JobRequest(
        spec_path=_form_str(form, "spec_path"),
        provider=_prov,
        model=_form_str(form, "model"),
        code_root=_form_str(form, "code_root"),
        max_files=_form_int(form, "max_files", DEFAULT_MAX_FILES),
        workers=_form_int(form, "workers", DEFAULT_GENERATION_WORKERS),
        planning_workers=_form_int(form, "planning_workers", DEFAULT_PLANNING_WORKERS),
        timeout=_form_float(form, "timeout", DEFAULT_TIMEOUT),
        notebook=form.get("notebook") in ("on", "true", "1", "yes"),
        notebook_path=_form_str(form, "notebook_path"),
        filtered_experiment_names=_form_str(form, "filtered_experiment_names"),
        filtered_model_names=_form_str(form, "filtered_model_names"),
        latest_only=_checkbox_truthy(form.get("latest_only")),
        verbose=_checkbox_truthy(form.get("verbose")),
        branch=_form_str(form, "branch"),
        hardware_tier=_form_str(form, "hardware_tier"),
        environment_id=_form_str(form, "environment_id"),
        environment_revision_id=_form_str(form, "environment_revision_id"),
        project_id=project_id,
        provider_base_url=_form_str(form, "provider_base_url"),
        language=_language,
        max_retries=_form_int(form, "max_retries", DEFAULT_LLM_MAX_RETRIES),
        initial_backoff=_form_float(form, "initial_backoff", DEFAULT_LLM_INITIAL_BACKOFF),
        max_backoff=_form_float(form, "max_backoff", DEFAULT_LLM_MAX_BACKOFF),
        backoff_jitter=_form_float(form, "backoff_jitter", DEFAULT_LLM_BACKOFF_JITTER),
        notebook_from_cache=_checkbox_truthy(form.get("notebook_from_cache")),
    )


# ---------------------------------------------------------------------------
# Domino job command building
# ---------------------------------------------------------------------------

def _build_job_command(req: JobRequest, spec_path: str, dataset_path: str = "") -> list[str]:
    if not spec_path or not str(spec_path).strip():
        raise ValueError("internal: spec_path is required to build the job command")
    if not (dataset_path or "").strip():
        raise ValueError("internal: dataset_path is required to build the job command")

    code_root_arg = (req.code_root or "").strip()

    command = [
        "python",
        "/mnt/code/auto_model_docs/main.py",
        "--spec",
        spec_path,
        "--dataset-path",
        dataset_path.strip(),
        "--code-root",
        code_root_arg,
        "--provider",
        req.provider.strip().lower(),
        "--language",
        req.language,
        "--max-files",
        str(req.max_files),
        "--generation-workers",
        str(req.workers),
        "--planning-workers",
        str(req.planning_workers),
        "--timeout",
        str(req.timeout),
        "--max-retries",
        str(req.max_retries),
        "--initial-backoff",
        str(req.initial_backoff),
        "--max-backoff",
        str(req.max_backoff),
        "--backoff-jitter",
        str(req.backoff_jitter),
    ]
    if req.model:
        command += ["--model", req.model]
    if req.provider_base_url:
        command += ["--provider-base-url", req.provider_base_url]
    if (req.filtered_experiment_names or "").strip():
        command += ["--filtered-experiments", req.filtered_experiment_names.strip()]
    if (req.filtered_model_names or "").strip():
        command += ["--filtered-models", req.filtered_model_names.strip()]
    if req.notebook_path:
        command += ["--notebook-path", req.notebook_path]
    if req.latest_only:
        command += ["--latest-only"]
    if req.notebook:
        command += ["--notebook"]
    if req.notebook_from_cache:
        command += ["--notebook-from-cache"]
    if req.verbose:
        command += ["--verbose"]
    return command


def _build_job_command_str(req: JobRequest, spec_path: str, dataset_path: str = "") -> str:
    import shlex
    parts = _build_job_command(req, spec_path, dataset_path)
    return " ".join(shlex.quote(p) for p in parts)


def _resolve_spec_field_to_cli_path(raw_from_field: str, dataset_path: str) -> str:
    raw = (raw_from_field or "").strip()
    if not raw:
        return ""
    if raw.startswith("dataset://"):
        parts = raw[len("dataset://"):].split("/", 1)
        dataset_name = parts[0]
        file_path = parts[1] if len(parts) > 1 else ""
        if (dataset_path or "").strip():
            return f"{dataset_path}/{file_path}"
        mount_prefix = domino_datasets.get_dataset_mount_prefix()
        return f"{mount_prefix}/{dataset_name}/{file_path}"
    return raw


# ---------------------------------------------------------------------------
# Domino job submission
# ---------------------------------------------------------------------------

def launch_domino_job_run(
    command_str: str,
    *,
    branch: Optional[str] = None,
    tier_id: Optional[str] = None,
    project_id: Optional[str] = None,
    environment_id: Optional[str] = None,
    environment_revision_id: Optional[str] = None,
) -> tuple[str, str]:
    run_id = domino_client.submit_job(
        command_str,
        branch=branch,
        tier_id=tier_id,
        project_id=project_id,
        environment_id=environment_id or None,
        environment_revision_id=environment_revision_id or None,
    )
    job_url = domino_client.build_job_url(run_id, project_id=project_id)
    return run_id, job_url


async def _submit_domino_job(
    req: JobRequest, owner_id: str, dataset_id: str, snapshot_id: str,
) -> DominoJobRecord:
    spec_path = ""
    dataset_path = ""

    if dataset_id:
        try:
            detail = domino_datasets.get_dataset_detail(dataset_id)
            dataset_path = detail.get("datasetPath", "")
        except Exception:
            pass

    field_raw = (req.spec_path or "").strip()
    if field_raw:
        spec_path = _resolve_spec_field_to_cli_path(field_raw, dataset_path)

    if not spec_path:
        raise ValueError(
            "A spec file is required. Set the spec path field (select a file in the browser or enter a path) before running."
        )

    _validate_job_inputs(req, dataset_path, spec_path)

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
        environment_id=_optional_domino_id(req.environment_id),
        environment_revision_id=_optional_domino_id(req.environment_revision_id),
    )

    active = domino_job_store.count_active_jobs(dataset_id, snapshot_id, owner_id)
    if active > _max_jobs():
        row = domino_job_store.get_job(dataset_id, snapshot_id, job_id)
        return _db_record_to_dataclass(row)

    try:
        run_id, job_url = launch_domino_job_run(
            command_str,
            branch=req.branch or None,
            tier_id=req.hardware_tier or None,
            project_id=req.project_id,
            environment_id=_optional_domino_id(req.environment_id),
            environment_revision_id=_optional_domino_id(req.environment_revision_id),
        )
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
            environment_id=oldest.get("environment_id"),
            environment_revision_id=oldest.get("environment_revision_id"),
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
