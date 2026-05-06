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
    DEFAULT_TIMEOUT,
)

from .state import (
    JobRequest,
    _max_jobs,
    domino_client,
    domino_job_store,
    logger,
)
from .ui_components import (
    _sanitize_optional_int,
    _sanitize_optional_float,
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


def _domino_id_str(raw: Any) -> str:
    if not isinstance(raw, str):
        return ""
    return raw.strip()


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
    try:
        body = await req.json()
    except Exception:
        body = {}
    if not isinstance(body, dict):
        body = {}

    project_id = (
        (req.query_params.get("projectId") or req.query_params.get("project_id") or "").strip()
        or None
    )
    if not project_id:
        raise RuntimeError("No target project ID available. The app requires ?projectId= on the request URL.")

    _prov = _form_str(body, "provider").strip().lower()
    if not _prov:
        raise RuntimeError("provider is required in the JSON body")
    _lang_raw = (_form_str(body, "language") or DEFAULT_LANGUAGE).strip().lower()
    _language = _lang_raw if _lang_raw in ALLOWED_LANGUAGES else DEFAULT_LANGUAGE

    return JobRequest(
        spec_path=_form_str(body, "spec_path"),
        provider=_prov,
        model=_form_str(body, "model"),
        code_root=_form_str(body, "code_root"),
        dataset_path=_form_str(body, "dataset_path"),
        max_files=_form_int(body, "max_files", DEFAULT_MAX_FILES),
        workers=_form_int(body, "workers", DEFAULT_GENERATION_WORKERS),
        planning_workers=_form_int(body, "planning_workers", DEFAULT_PLANNING_WORKERS),
        timeout=_form_float(body, "timeout", DEFAULT_TIMEOUT),
        notebook=_checkbox_truthy(body.get("notebook")),
        notebook_path=_form_str(body, "notebook_path"),
        filtered_experiment_names=_form_str(body, "filtered_experiment_names"),
        filtered_model_names=_form_str(body, "filtered_model_names"),
        latest_only=_checkbox_truthy(body.get("latest_only")),
        verbose=_checkbox_truthy(body.get("verbose")),
        branch=_form_str(body, "branch"),
        hardware_tier=_form_str(body, "hardware_tier"),
        environment_id=_form_str(body, "environment_id"),
        environment_revision_id=_form_str(body, "environment_revision_id"),
        project_id=project_id,
        provider_base_url=_form_str(body, "provider_base_url"),
        language=_language,
        max_retries=_form_int(body, "max_retries", DEFAULT_LLM_MAX_RETRIES),
        initial_backoff=_form_float(body, "initial_backoff", DEFAULT_LLM_INITIAL_BACKOFF),
        max_backoff=_form_float(body, "max_backoff", DEFAULT_LLM_MAX_BACKOFF),
        backoff_jitter=_form_float(body, "backoff_jitter", DEFAULT_LLM_BACKOFF_JITTER),
        notebook_from_cache=_checkbox_truthy(body.get("notebook_from_cache")),
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


# ---------------------------------------------------------------------------
# Domino job submission
# ---------------------------------------------------------------------------

def launch_domino_job_run(
    command_str: str,
    *,
    branch: Optional[str] = None,
    tier_id: str,
    project_id: str,
    environment_id: str,
    environment_revision_id: str,
) -> tuple[str, str]:
    run_id = domino_client.submit_job(
        command_str,
        branch=branch,
        tier_id=tier_id,
        project_id=project_id,
        environment_id=environment_id,
        environment_revision_id=environment_revision_id,
    )
    job_url = domino_client.build_job_url(run_id, project_id=project_id)
    return run_id, job_url


async def _submit_domino_job(req: JobRequest) -> None:
    spec_path = (req.spec_path or "").strip()
    dataset_path = (req.dataset_path or "").strip()

    if not spec_path:
        raise ValueError(
            "A spec file is required. Set the spec path field (select a file in the browser or enter a path) before running."
        )

    _validate_job_inputs(req, dataset_path, spec_path)

    command_str = _build_job_command_str(req, spec_path, dataset_path)

    try:
        launch_domino_job_run(
            command_str,
            branch=req.branch or None,
            tier_id=_domino_id_str(req.hardware_tier),
            project_id=_domino_id_str(req.project_id),
            environment_id=_domino_id_str(req.environment_id),
            environment_revision_id=_domino_id_str(req.environment_revision_id),
        )
    except Exception as exc:
        logger.error("Domino job submission failed: %s", exc, exc_info=True)
        raise


# ---------------------------------------------------------------------------
# Request-driven job sync
# ---------------------------------------------------------------------------

def _refresh_active_jobs_for(owner_id: str) -> None:
    from datetime import datetime, timezone

    active_jobs = [
        j for j in domino_job_store.get_active_jobs("", "")
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
                domino_job_store.update_job("", "", row["id"], **updates)
        except Exception as exc:
            logger.warning("Status sync failed for run %s: %s", run_id, exc)


def _promote_queued_jobs_for(owner_id: str) -> None:
    active = domino_job_store.count_active_jobs("", "", owner_id)
    if active > _max_jobs():
        return
    oldest = domino_job_store.get_oldest_queued_job("", "", owner_id)
    if not oldest or oldest.get("domino_run_id"):
        return
    try:
        cmd = oldest.get("command", "")
        run_id = domino_client.submit_job(
            cmd,
            branch=oldest.get("branch"),
            tier_id=_domino_id_str(oldest.get("hardware_tier")),
            project_id=_domino_id_str(oldest.get("project_id")),
            environment_id=_domino_id_str(oldest.get("environment_id")),
            environment_revision_id=_domino_id_str(oldest.get("environment_revision_id")),
        )
        job_url = domino_client.build_job_url(
            run_id, project_id=_domino_id_str(oldest.get("project_id")),
        )
        domino_job_store.update_job(
            "", "", oldest["id"],
            status="submitted",
            domino_run_id=run_id,
            job_url=job_url,
        )
    except Exception as exc:
        logger.warning("Failed to promote queued job %s: %s", oldest["id"], exc)


def sync_jobs_for(owner_id: str) -> None:
    try:
        _refresh_active_jobs_for(owner_id)
        _promote_queued_jobs_for(owner_id)
    except Exception as exc:
        logger.warning("sync_jobs_for(%s) failed: %s", owner_id, exc)
