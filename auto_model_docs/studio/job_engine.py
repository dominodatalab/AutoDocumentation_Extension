"""Documentation job submission and command building."""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any

from starlette.requests import Request

_root = Path(__file__).resolve().parent.parent
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))

from default_consts import (
    ALLOWED_PROVIDERS,
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

_MAX_JOB_MAX_FILES = 1_000_000
_MAX_JOB_WORKERS = 512
_MAX_JOB_TIMEOUT_SEC = 7 * 24 * 3600
_MAX_JOB_MAX_RETRIES = 100
from artifact_layout import get_artifacts_root

from .state import (
    JobRequest,
    _resolve_request_project_id,
    domino_client,
    logger,
)
from .ui_components import (
    _sanitize_optional_int,
    _sanitize_optional_float,
)


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


def _validate_job_inputs(req: JobRequest, spec_path: str) -> None:
    if not spec_path or not str(spec_path).strip():
        raise ValueError("A spec file is required. Please select or upload a spec before generating documentation.")
    if not _domino_id_str(req.project_id):
        raise ValueError("Project ID is required.")
    prov = (req.provider or "").strip().lower()
    if not prov:
        raise ValueError("Provider is required.")
    if prov not in ALLOWED_PROVIDERS:
        raise ValueError("Provider must be anthropic or openai.")
    if not (req.model or "").strip():
        raise ValueError("Model is required. Choose a model before generating documentation.")
    if not _domino_id_str(req.hardware_tier):
        raise ValueError("Hardware tier is required. Select a hardware tier before generating documentation.")
    if not _domino_id_str(req.environment_id):
        raise ValueError("Environment is required. Select an environment before generating documentation.")
    if not _domino_id_str(req.environment_revision_id):
        raise ValueError("Environment revision is required. Select an environment revision before generating documentation.")
    if req.max_files < 1 or req.max_files > _MAX_JOB_MAX_FILES:
        raise ValueError(f"max_files must be between 1 and {_MAX_JOB_MAX_FILES}.")
    if req.workers < 1 or req.workers > _MAX_JOB_WORKERS:
        raise ValueError(f"generation workers must be between 1 and {_MAX_JOB_WORKERS}.")
    if req.planning_workers < 1 or req.planning_workers > _MAX_JOB_WORKERS:
        raise ValueError(f"planning workers must be between 1 and {_MAX_JOB_WORKERS}.")
    if req.timeout <= 0 or req.timeout > _MAX_JOB_TIMEOUT_SEC:
        raise ValueError(f"timeout must be positive and at most {_MAX_JOB_TIMEOUT_SEC} seconds.")
    if req.max_retries < 0 or req.max_retries > _MAX_JOB_MAX_RETRIES:
        raise ValueError(f"max_retries must be between 0 and {_MAX_JOB_MAX_RETRIES}.")
    if req.initial_backoff < 0:
        raise ValueError("initial_backoff must be non-negative.")
    if req.max_backoff < 0:
        raise ValueError("max_backoff must be non-negative.")
    if req.max_backoff < req.initial_backoff:
        raise ValueError("max_backoff must be greater than or equal to initial_backoff.")
    if req.backoff_jitter < 0:
        raise ValueError("backoff_jitter must be non-negative.")


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

    project_id = _resolve_request_project_id(req)
    if not project_id:
        raise RuntimeError(
            "No target project ID available. The app requires projectId (or project_id) on the request query string."
        )

    _prov = _form_str(body, "provider").strip().lower()
    if not _prov:
        raise RuntimeError("provider is required in the JSON body")
    _model = _form_str(body, "model").strip()
    if not _model:
        raise RuntimeError("model is required in the JSON body")

    notebook = True
    notebook_path = _form_str(body, "notebook_path")
    notebook_from_cache = _checkbox_truthy(body.get("notebook_from_cache"))

    _code_path = _form_str(body, "code_path").strip()
    if _code_path:
        _code_root = _code_path
    else:
        info = domino_client.resolve_project(project_id)
        if not info:
            raise RuntimeError("Could not resolve project info to determine code root.")
        try:
            _code_root = domino_client.get_project_code_root(info.owner_username, info.name)
        except Exception as exc:
            raise RuntimeError(f"Could not determine code root for project: {exc}") from exc

    _branch = _form_str(body, "branch").strip()
    if _branch:
        try:
            src = domino_client.get_code_source_info(project_id)
            if not src.get("is_git"):
                _branch = ""
        except Exception:
            _branch = ""

    env_defaults = domino_client.resolve_job_environment_defaults()
    environment_id = _form_str(body, "environment_id") or env_defaults["environment_id"]
    environment_revision_id = _form_str(body, "environment_revision_id") or env_defaults["environment_revision_id"]

    return JobRequest(
        spec_path=_form_str(body, "spec_path"),
        provider=_prov,
        model=_model,
        code_root=_code_root,
        max_files=_form_int(body, "max_files", DEFAULT_MAX_FILES),
        workers=_form_int(body, "workers", DEFAULT_GENERATION_WORKERS),
        planning_workers=_form_int(body, "planning_workers", DEFAULT_PLANNING_WORKERS),
        timeout=_form_float(body, "timeout", DEFAULT_TIMEOUT),
        notebook=notebook,
        notebook_path=notebook_path,
        filtered_experiment_names=_form_str(body, "filtered_experiment_names"),
        filtered_model_names=_form_str(body, "filtered_model_names"),
        latest_only=_checkbox_truthy(body.get("latest_only")),
        verbose=_checkbox_truthy(body.get("verbose")),
        hardware_tier=_form_str(body, "hardware_tier"),
        environment_id=environment_id,
        environment_revision_id=environment_revision_id,
        project_id=project_id,
        provider_base_url=_form_str(body, "provider_base_url"),
        max_retries=_form_int(body, "max_retries", DEFAULT_LLM_MAX_RETRIES),
        initial_backoff=_form_float(body, "initial_backoff", DEFAULT_LLM_INITIAL_BACKOFF),
        max_backoff=_form_float(body, "max_backoff", DEFAULT_LLM_MAX_BACKOFF),
        backoff_jitter=_form_float(body, "backoff_jitter", DEFAULT_LLM_BACKOFF_JITTER),
        notebook_from_cache=notebook_from_cache,
        bundle_id=_form_str(body, "bundle_id"),
        branch=_branch,
        prompts_file=_form_str(body, "prompts_file"),
    )


# ---------------------------------------------------------------------------
# Documentation job command building
# ---------------------------------------------------------------------------

def _build_job_command(req: JobRequest, spec_path: str) -> list[str]:
    if not spec_path or not str(spec_path).strip():
        raise ValueError("internal: spec_path is required to build the job command")

    code_root_arg = (req.code_root or "").strip()
    app_work_dir = os.environ.get("APP_WORK_DIR", ".")
    cli_sh = f"{app_work_dir}/cli.sh"

    command = [
        cli_sh,
        "--spec",
        spec_path,
        "--output_dir",
        get_artifacts_root(),
        "--code-root",
        code_root_arg,
        "--provider",
        req.provider.strip().lower(),
        "--language",
        DEFAULT_LANGUAGE,
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
        "--model",
        (req.model or "").strip(),
    ]
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
    bundle_id = (req.bundle_id or "").strip()
    prompts_path = (req.prompts_file or "").strip()
    if prompts_path:
        command += ["--prompts-file", prompts_path]
    if bundle_id:
        command += ["--bundle-id", bundle_id]
    return command


def _build_job_command_str(req: JobRequest, spec_path: str) -> str:
    import shlex
    parts = _build_job_command(req, spec_path)
    return " ".join(shlex.quote(p) for p in parts)


# ---------------------------------------------------------------------------
# Documentation job submission
# ---------------------------------------------------------------------------

def launch_domino_job_run(
    command_str: str,
    *,
    branch: str | None = None,
    tier_id: str,
    project_id: str,
    environment_id: str,
    environment_revision_id: str,
) -> tuple[str, str]:
    run_id = domino_client.submit_job(
        command_str,
        branch=branch or None,
        tier_id=tier_id,
        project_id=project_id,
        environment_id=environment_id,
        environment_revision_id=environment_revision_id,
    )
    job_url = domino_client.build_job_url(run_id, project_id=project_id)
    return run_id, job_url


def _submit_domino_job(req: JobRequest) -> tuple[str, str]:
    spec_path = (req.spec_path or "").strip()

    if not spec_path:
        raise ValueError(
            "A spec file is required. Set the spec path field (select a file in the browser or enter a path) before running."
        )

    _validate_job_inputs(req, spec_path)

    command_str = _build_job_command_str(req, spec_path)

    try:
        run_id, job_url = launch_domino_job_run(
            command_str,
            branch=(req.branch or "").strip() or None,
            tier_id=_domino_id_str(req.hardware_tier),
            project_id=_domino_id_str(req.project_id),
            environment_id=_domino_id_str(req.environment_id),
            environment_revision_id=_domino_id_str(req.environment_revision_id),
        )
        return run_id, job_url or ""
    except Exception as exc:
        logger.error("Documentation job submission failed: %s", exc, exc_info=True)
        raise

def build_queue_payload(req: JobRequest, spec_path: str) -> dict[str, Any]:
    return {
        "command_str": _build_job_command_str(req, spec_path),
        "branch": (req.branch or "").strip() or None,
        "tier_id": _domino_id_str(req.hardware_tier),
        "project_id": _domino_id_str(req.project_id),
        "environment_id": _domino_id_str(req.environment_id),
        "environment_revision_id": _domino_id_str(req.environment_revision_id),
    }


def submit_from_queue_payload(payload: dict[str, Any]) -> tuple[str, str]:
    return launch_domino_job_run(
        str(payload.get("command_str") or ""),
        branch=payload.get("branch") or None,
        tier_id=str(payload.get("tier_id") or ""),
        project_id=str(payload.get("project_id") or ""),
        environment_id=str(payload.get("environment_id") or ""),
        environment_revision_id=str(payload.get("environment_revision_id") or ""),
    )


def submit_or_enqueue(owner_id: str, req: JobRequest) -> dict[str, Any]:
    import json

    from .state import _max_jobs, domino_job_store

    spec_path = (req.spec_path or "").strip()
    _validate_job_inputs(req, spec_path)
    project_id = _domino_id_str(req.project_id)
    max_jobs = _max_jobs()

    domino_job_store.dispatch_queued_jobs(
        project_id,
        owner_id,
        max_jobs,
        submit_from_queue_payload,
    )

    active = domino_job_store.count_active_slots(project_id, owner_id)
    queued = False
    if active < max_jobs:
        run_id, job_url = _submit_domino_job(req)
        domino_job_store.record_job(
            owner_id,
            project_id,
            domino_run_id=run_id,
            job_url=job_url,
            hardware_tier=(req.hardware_tier or "").strip(),
            spec_path=spec_path,
        )
    else:
        payload = build_queue_payload(req, spec_path)
        domino_job_store.enqueue_job(
            owner_id,
            project_id,
            hardware_tier=(req.hardware_tier or "").strip(),
            spec_path=spec_path,
            queue_payload=json.dumps(payload),
        )
        queued = True

    jobs = domino_job_store.get_user_jobs(
        project_id,
        owner_id,
        limit=50,
        max_jobs=max_jobs,
        submit_fn=submit_from_queue_payload,
    )
    return {"ok": True, "queued": queued, "jobs": jobs}

