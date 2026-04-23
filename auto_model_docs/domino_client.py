"""Domino API client using direct REST calls (no SDK dependency).

Supports an optional ``project_id`` override so the app can target a
different project than the one it is running in.  When *project_id* is
``None`` every helper falls back to the environment variables set by
the Domino platform (``DOMINO_PROJECT_ID``, ``DOMINO_PROJECT_OWNER``,
``DOMINO_PROJECT_NAME``).
"""

from __future__ import annotations

import logging
import os
import time
from dataclasses import dataclass
from typing import Any, Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Domino status → local status mapping
# ---------------------------------------------------------------------------
_PENDING_STATUSES = {"queued", "pending", "initializing", "provisioning"}
_RUNNING_STATUSES = {"running", "executing"}
_SUCCEEDED_STATUSES = {"succeeded", "success", "successful", "completed", "complete", "done", "finished"}
_FAILED_STATUSES = {"failed", "error"}
_CANCELLED_STATUSES = {"stopped", "cancelled", "canceled", "archived"}

# ---------------------------------------------------------------------------
# Retryable HTTP status codes & defaults
# ---------------------------------------------------------------------------
_RETRYABLE_STATUS_CODES = (408, 502, 503, 504)
_DEFAULT_TIMEOUT = 30.0
_DEFAULT_MAX_RETRIES = 3


# ---------------------------------------------------------------------------
# Project info cache
# ---------------------------------------------------------------------------
@dataclass
class ProjectInfo:
    id: str
    name: str
    owner_username: str
    main_repo_id: Optional[str] = None


_project_cache: dict[str, ProjectInfo] = {}


# ---------------------------------------------------------------------------
# API host / auth resolution (delegated to domino_auth)
# ---------------------------------------------------------------------------

from domino_auth import resolve_api_host as _resolve_api_host
from domino_auth import current_auth as _current_auth


def _get_auth_headers() -> dict[str, str]:
    return _current_auth().to_headers()


# ---------------------------------------------------------------------------
# Core HTTP helper with retry
# ---------------------------------------------------------------------------

def _domino_request(
    method: str,
    path: str,
    *,
    json: Any = None,
    params: dict[str, Any] | None = None,
    timeout: float = _DEFAULT_TIMEOUT,
    max_retries: int = _DEFAULT_MAX_RETRIES,
) -> Any:
    """Send a synchronous HTTP request to the Domino API with retry logic."""
    import httpx

    base_url = _resolve_api_host()
    if not base_url:
        raise RuntimeError("Domino API host is not configured. Set DOMINO_API_HOST.")

    url = f"{base_url}{path}"
    last_exc: Exception | None = None

    for attempt in range(max_retries + 1):
        headers = _get_auth_headers()
        if json is not None:
            headers["Content-Type"] = "application/json"
        try:
            with httpx.Client(timeout=timeout) as client:
                resp = client.request(method, url, json=json, params=params, headers=headers)
                if resp.status_code in _RETRYABLE_STATUS_CODES and attempt < max_retries:
                    backoff = 2 ** attempt
                    time.sleep(backoff)
                    continue
                resp.raise_for_status()
                return resp.json()
        except httpx.HTTPStatusError as e:
            try:
                body_preview = (e.response.text or "")[:2000]
            except Exception:
                body_preview = "(could not read body)"
            logger.warning(
                "Domino API HTTP %s %s status=%s url=%s response_body=%r",
                method,
                path,
                e.response.status_code,
                str(e.request.url),
                body_preview,
            )
            raise
        except Exception as exc:
            last_exc = exc
            if attempt < max_retries:
                backoff = 2 ** attempt
                logger.warning(
                    "Domino API %s %s failed (%s), retrying in %ss (attempt %s/%s)",
                    method, path, exc, backoff, attempt + 1, max_retries,
                )
                time.sleep(backoff)
                continue
            raise

    raise last_exc or RuntimeError("Domino request failed after retries")


# ---------------------------------------------------------------------------
# Project resolution
# ---------------------------------------------------------------------------

def resolve_project(project_id: str) -> Optional[ProjectInfo]:
    """Resolve project name and owner from the Domino v4 projects API.

    Returns cached ``ProjectInfo`` on success, ``None`` on failure.
    """
    if project_id in _project_cache:
        return _project_cache[project_id]

    api_host = _resolve_api_host()
    if not api_host:
        return None

    try:
        # Try the internal /v4/ path first (works in many deployments),
        # then fall back to the documented public API path.
        data = None
        for path in (
            f"/v4/projects/{project_id}",
            f"/api/projects/v1/projects/{project_id}",
        ):
            try:
                data = _domino_request("GET", path)
                break
            except Exception as path_exc:
                logger.debug("Project resolve path %s failed: %s", path, path_exc)
                continue

        if data is None:
            return None

        name = data.get("name")
        owner = data.get("ownerUsername") or (data.get("owner") or {}).get("userName")

        if not name or not owner:
            return None

        main_repo = data.get("mainRepository") or {}
        main_repo_id = main_repo.get("id") if isinstance(main_repo, dict) else None

        info = ProjectInfo(id=project_id, name=name, owner_username=owner, main_repo_id=main_repo_id)
        _project_cache[project_id] = info
        return info

    except Exception:
        logger.exception("Error resolving project %s", project_id)
        return None


def get_project_context(
    project_id: Optional[str] = None,
) -> tuple[Optional[str], Optional[str], Optional[str]]:
    """Resolve (project_id, project_name, project_owner).

    Requires *project_id* — does not fall back to the app project.
    """
    if not project_id:
        return None, None, None
    info = resolve_project(project_id)
    if info:
        return info.id, info.name, info.owner_username
    # Resolution failed — return the ID but no name/owner
    return project_id, None, None


def browse_code(
    owner_username: str,
    project_name: str,
    *,
    path_string: str = "",
) -> dict[str, Any]:
    """GET /v4/code/browseCode. Domino requires ``pathString``; project root is ``/``."""
    path_param = (path_string or "").strip() or "/"
    params: dict[str, Any] = {
        "ownerUsername": owner_username,
        "projectName": project_name,
        "pathString": path_param,
    }
    return _domino_request("GET", "/v4/code/browseCode", params=params)


def code_root_options_from_browse_response(browse: dict[str, Any]) -> dict[str, Any]:
    """Build combobox payload from browseCode JSON (projectSettings)."""
    ps = browse.get("projectSettings") or {}
    is_git = bool(ps.get("isGitBasedProject"))
    default_root = "/mnt/code" if is_git else "/mnt"
    options: list[dict[str, str]] = [{"value": default_root, "label": default_root}]
    seen: set[str] = {default_root}
    for repo in ps.get("repositories") or []:
        if not isinstance(repo, dict):
            continue
        loc = str(repo.get("location") or "").strip()
        if not loc or loc in seen:
            continue
        seen.add(loc)
        name = str(repo.get("repoName") or "").strip()
        label = f"{loc} ({name})" if name else loc
        options.append({"value": loc, "label": label})
    return {
        "isGitBasedProject": is_git,
        "defaultRoot": default_root,
        "options": options,
    }


# ---------------------------------------------------------------------------
# Branches
# ---------------------------------------------------------------------------

def list_branches_api(project_id: str, search: str = "") -> list[dict[str, Any]]:
    """List branches in the target project via the Domino git API.

    Requires the project to have been resolved first (to obtain the repo ID).
    Returns a list of ``{"name": branch_name}`` dicts, or empty on failure.
    """
    info = _project_cache.get(project_id)
    if not info or not info.main_repo_id:
        info = resolve_project(project_id)
    if not info or not info.main_repo_id:
        return []

    try:
        data = _domino_request(
            "GET",
            f"/v4/projects/{project_id}/gitRepositories/{info.main_repo_id}/git/branches",
            params={"count": 300, "searchPattern": search},
        )
        branches = []
        # Unwrap nested pagination: {"data": {"items": [...], ...}}
        payload = data
        if isinstance(payload, dict) and isinstance(payload.get("data"), dict):
            payload = payload["data"]
        if isinstance(payload, list):
            items = payload
        elif isinstance(payload, dict):
            items = (
                payload.get("items")
                or payload.get("branches")
                or payload.get("data")
                or []
            )
            # Ensure we got a list, not another nested dict
            if not isinstance(items, list):
                items = []
        else:
            items = []
        for item in items:
            if isinstance(item, dict):
                name = item.get("name") or item.get("value", "")
            elif isinstance(item, str):
                name = item
            else:
                continue
            if name:
                branches.append({"name": name})
        return branches
    except Exception as exc:
        logger.warning("Failed to list branches via API: %s", exc)
        return []


# ---------------------------------------------------------------------------
# Hardware tiers
# ---------------------------------------------------------------------------

def list_hardware_tiers(project_id: Optional[str] = None) -> list[dict[str, Any]]:
    """Return available hardware tiers for a project.

    Requires *project_id* — does not fall back to the app project.
    """
    pid = project_id
    if not pid:
        return []

    try:
        data = _domino_request("GET", f"/v4/projects/{pid}/hardwareTiers")
        tiers = data if isinstance(data, list) else data.get("hardwareTiers", data.get("data", []))
        results = []
        for t in tiers:
            hw = t.get("hardwareTier", t) if isinstance(t, dict) else t
            if not isinstance(hw, dict):
                continue
            results.append({
                "id": hw.get("id", ""),
                "name": hw.get("name") or hw.get("id", ""),
                "isDefault": hw.get("hwtFlags", {}).get("isDefault", False)
                    if isinstance(hw.get("hwtFlags"), dict)
                    else hw.get("isDefault", False),
            })
        return results
    except Exception as exc:
        logger.warning("Failed to list hardware tiers: %s", exc)
        return []


def get_project_default_tier() -> Optional[str]:
    """Return the default hardware tier ID for the project."""
    override = os.environ.get("AUTODOC_DEFAULT_HARDWARE_TIER")
    if override:
        return override
    return os.environ.get("DOMINO_HARDWARE_TIER_ID") or None


# ---------------------------------------------------------------------------
# Job submission
# ---------------------------------------------------------------------------

def submit_job(
    command: str | list[str],
    branch: Optional[str],
    tier_id: Optional[str] = None,
    project_id: Optional[str] = None,
) -> str:
    """Submit a Domino job via the v1 jobs API and return the job ID.

    When *project_id* is provided the job is started in that project.
    Otherwise uses the env-var project.
    """
    pid, pname, _ = get_project_context(project_id)
    if not pid:
        raise RuntimeError("No project ID available to submit a job.")

    title = f"AutoDoc: {pname or pid}" + (f" ({branch})" if branch else "")

    command_str = " ".join(command) if isinstance(command, list) else command

    payload: dict[str, Any] = {
        "projectId": pid,
        "commandToRun": command_str,
        "title": title,
    }
    if tier_id:
        payload["overrideHardwareTierId"] = tier_id
    if branch:
        payload["mainRepoGitRef"] = {"type": "branches", "value": branch}


    try:
        data = _domino_request("POST", "/v4/jobs/start", json=payload)
    except Exception:
        # Retry without commit pin if Domino can't resolve the ref
        if branch and payload.get("mainRepoGitRef"):
            logger.warning("Retrying job start without mainRepoGitRef")
            payload.pop("mainRepoGitRef", None)
            data = _domino_request("POST", "/v4/jobs/start", json=payload)
        else:
            raise


    run_id = (
        data.get("id")
        or data.get("runId")
        or data.get("run_id")
        or data.get("jobId")
    )
    if not run_id:
        raise ValueError(f"Domino job_start returned unexpected response: {data!r}")

    return str(run_id)


# ---------------------------------------------------------------------------
# Job status
# ---------------------------------------------------------------------------

def get_job_status(run_id: str) -> dict[str, Any]:
    """Return job status dict from Domino.

    Uses the v1 jobs API.  Returns a dict with 'domino_status' and
    'local_status'.
    """
    try:
        data = _domino_request("GET", f"/v4/jobs/{run_id}")
    except Exception as exc:
        logger.warning("Failed to get status for run %s: %s", run_id, exc)
        return {"domino_status": "unknown", "local_status": "running"}

    raw = (
        data.get("statuses", {}).get("executionStatus", "")
        or data.get("status")
        or data.get("jobStatus")
        or ""
    )

    raw_lower = raw.lower()
    if raw_lower in _SUCCEEDED_STATUSES:
        local = "succeeded"
    elif raw_lower in _FAILED_STATUSES:
        local = "failed"
    elif raw_lower in _CANCELLED_STATUSES:
        local = "cancelled"
    elif raw_lower in _RUNNING_STATUSES:
        local = "running"
    elif raw_lower in _PENDING_STATUSES:
        local = "pending"
    else:
        local = "submitted"

    return {"domino_status": raw, "local_status": local}


# ---------------------------------------------------------------------------
# Job stop
# ---------------------------------------------------------------------------

def stop_job(run_id: str, project_id: Optional[str] = None) -> None:
    """Stop a running Domino job. Requires project_id."""
    if not project_id:
        raise ValueError("project_id is required to stop a job")
    payload: dict[str, Any] = {"jobId": run_id, "commitResults": True, "projectId": project_id}
    try:
        _domino_request("POST", "/v4/jobs/stop", json=payload)
    except Exception as exc:
        logger.warning("Failed to stop run %s: %s", run_id, exc)


# ---------------------------------------------------------------------------
# UI host resolution & job URL building
# ---------------------------------------------------------------------------

_ui_host: str | None = None


def set_ui_host(request_host: str, scheme: str = "https") -> None:
    """Cache the external Domino UI host from an incoming request header."""
    global _ui_host
    if _ui_host is not None:
        return

    from urllib.parse import urlparse, urlunparse

    raw = (request_host or "").strip()
    if not raw:
        return

    if "://" not in raw:
        raw = f"{scheme}://{raw}"

    parsed = urlparse(raw)
    hostname = (parsed.hostname or "").strip()
    if not hostname:
        return

    if hostname.startswith("apps."):
        hostname = hostname[len("apps."):]
    if not hostname:
        return

    netloc = f"{hostname}:{parsed.port}" if parsed.port else hostname
    _ui_host = urlunparse((parsed.scheme or scheme, netloc, "", "", "", "")).rstrip("/")


def build_job_url(run_id: str, project_id: Optional[str] = None) -> str | None:
    """Return the Domino UI URL for a job.

    When *project_id* is given, resolves owner/name from the API cache.
    """
    if not _ui_host:
        return None

    _, pname, powner = get_project_context(project_id)
    if not powner or not pname:
        return None
    return f"{_ui_host}/jobs/{powner}/{pname}/{run_id}/logs?status=all"
