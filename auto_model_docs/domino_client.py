"""Domino API client using direct REST calls (no SDK dependency).

Callers pass an explicit ``project_id`` where the API needs a project.
There is no env-var fallback for project context in this module.
"""

from __future__ import annotations

import logging
import os
import time
from dataclasses import dataclass
from datetime import datetime, timezone
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


def get_project_context(project_id: str) -> tuple[str, Optional[str], Optional[str]]:
    """Resolve (project_id, project_name, project_owner)."""
    pid = project_id.strip()
    if not pid:
        raise ValueError("project_id is required")
    info = resolve_project(pid)
    if info:
        return info.id, info.name, info.owner_username
    return pid, None, None


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


def get_project_code_root(owner_username: str, project_name: str) -> str:
    """Return the code root path for a project (/mnt/code for git-based, /mnt otherwise)."""
    browse = browse_code(owner_username, project_name, path_string="")
    ps = browse.get("projectSettings") or {}
    is_git = bool(ps.get("isGitBasedProject"))
    return "/mnt/code" if is_git else "/mnt"


def get_code_source_info(project_id: str) -> dict[str, Any]:
    """Return {is_git, repo_id, location} for the project's default code source."""
    info = resolve_project(project_id)
    if not info:
        raise ValueError(f"Could not resolve project {project_id}")
    browse = browse_code(info.owner_username, info.name)
    ps = browse.get("projectSettings") or {}
    is_git = bool(ps.get("isGitBasedProject"))
    repo_id: Optional[str] = None
    location = "/mnt/code" if is_git else "/mnt"
    if is_git:
        try:
            proj_data = _domino_request("GET", f"/v4/projects/{project_id}")
            main_repo = (proj_data or {}).get("mainRepository") or {}
            rid = main_repo.get("id")
            if rid:
                repo_id = str(rid)
        except Exception as exc:
            logger.warning("get_code_source_info: mainRepository lookup failed: %s", exc)
    return {"is_git": is_git, "repo_id": repo_id, "location": location}


def browse_gbp_code(project_id: str, repo_id: str, directory: str = "") -> list[dict[str, Any]]:
    """Browse files in a GBP git repo at the given directory path."""
    params: dict[str, Any] = {}
    if directory:
        params["directory"] = directory
    data = _domino_request(
        "GET",
        f"/v4/projects/{project_id}/gitRepositories/{repo_id}/git/browse",
        params=params,
    )
    inner = data.get("data") or {}
    items = inner.get("items") or data.get("items") or []
    result: list[dict[str, Any]] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        kind = item.get("kind", "")
        result.append({
            "fileName": item.get("name", ""),
            "isDirectory": kind == "dir",
        })
    return result


def browse_dfs_code(owner_username: str, project_name: str, file_path: str = "") -> list[dict[str, Any]]:
    """Browse DFS code files/directories at the given path."""
    fp = (file_path or "").strip() or "/"
    params: dict[str, Any] = {
        "ownerUsername": owner_username,
        "projectName": project_name,
        "filePath": fp,
    }
    result: list[dict[str, Any]] = []
    try:
        dirs = _domino_request("GET", "/v4/files/browseDirectories", params=params)
        for d in (dirs if isinstance(dirs, list) else []):
            if isinstance(d, dict):
                result.append({"fileName": d.get("name", ""), "isDirectory": True})
    except Exception as exc:
        logger.warning("browse_dfs_code directories failed: %s", exc)
    try:
        files = _domino_request("GET", "/v4/files/browseFiles", params=params)
        for f in (files if isinstance(files, list) else []):
            if isinstance(f, dict):
                result.append({"fileName": f.get("name", ""), "isDirectory": False})
    except Exception as exc:
        logger.warning("browse_dfs_code files failed: %s", exc)
    return result


def read_gbp_file_raw(project_id: str, repo_id: str, file_path: str) -> bytes:
    """Read raw file content from a GBP git repo."""
    import httpx
    base_url = _resolve_api_host()
    if not base_url:
        raise RuntimeError("Domino API host is not configured")
    url = f"{base_url}/v4/projects/{project_id}/gitRepositories/{repo_id}/git/raw"
    headers = _get_auth_headers()
    with httpx.Client(timeout=_DEFAULT_TIMEOUT, follow_redirects=True) as client:
        resp = client.get(url, params={"fileName": file_path}, headers=headers)
        resp.raise_for_status()
        return resp.content


# ---------------------------------------------------------------------------
# Hardware tiers
# ---------------------------------------------------------------------------

_HW_CAPACITY_LABELS: dict[str, str] = {
    "FULL": "NO ESTIMATE",
    "REQUIRES_LAUNCHING_INSTANCE": "< 7 MIN",
    "CAN_EXECUTE_WITH_CURRENT_INSTANCES": "< 1 MIN",
    "UNKNOWN": "NO ESTIMATE",
}


def _hw_capacity_label(capacity_level: Any) -> str:
    if capacity_level is None:
        return ""
    key = str(capacity_level).strip().upper().replace("-", "_")
    return _HW_CAPACITY_LABELS.get(key, "")


def _hw_format_price(cents_per_minute: Any) -> str:
    try:
        c = float(cents_per_minute or 0)
    except (TypeError, ValueError):
        return ""
    if c <= 0:
        return ""
    return f"${(c / 100.0):.4f}/min"


def _hw_memory_ram_label(mem: Any) -> str:
    if mem is None:
        return ""
    if isinstance(mem, dict):
        val = mem.get("value")
        unit = (mem.get("unit") or "").strip()
        if val is not None:
            base = f"{val} {unit}".strip()
            if base.upper().endswith("RAM"):
                return base
            return f"{base} RAM" if base else ""
    return str(mem)


def _hw_core_label(cores: Any) -> str:
    try:
        c = float(cores)
    except (TypeError, ValueError):
        return ""
    if c <= 0:
        return ""
    if abs(c - 1.0) < 1e-9:
        return "1 core"
    if abs(c - round(c)) < 1e-9:
        return f"{int(round(c))} cores"
    return f"{c} cores"


def _hw_gpu_label(gpu: Any) -> str:
    if not isinstance(gpu, dict):
        return ""
    try:
        n = int(gpu.get("numberOfGpus", 0) or 0)
    except (TypeError, ValueError):
        return ""
    if n == 1:
        return "1 GPU"
    if n > 1:
        return f"{n} GPUs"
    return ""


def _hw_specs_subtitle(hw: dict[str, Any]) -> str:
    res = hw.get("hwtResources") or hw.get("resources") or {}
    if not isinstance(res, dict):
        res = {}
    parts: list[str] = []
    cl = _hw_core_label(res.get("cores"))
    if cl:
        parts.append(cl)
    ml = _hw_memory_ram_label(res.get("memory"))
    if ml:
        parts.append(ml)
    gl = _hw_gpu_label(hw.get("gpuConfiguration"))
    if gl:
        parts.append(gl)
    pl = _hw_format_price(hw.get("centsPerMinute"))
    if pl:
        parts.append(pl)
    return " \u00b7 ".join(parts)


def _hw_spot_enabled(hw: dict[str, Any]) -> bool:
    r = hw.get("capacityTypeRestrictions")
    if isinstance(r, dict):
        return bool(r.get("enableSpotInstances"))
    return False


def _hw_option_label(hw: dict[str, Any], capacity: Optional[dict[str, Any]]) -> str:
    name = (hw.get("name") or hw.get("id") or "").strip() or "(unnamed)"
    specs = _hw_specs_subtitle(hw)
    cap_level = None
    if isinstance(capacity, dict):
        cap_level = capacity.get("capacityLevel")
    elif isinstance(hw.get("capacity"), dict):
        cap_level = hw["capacity"].get("capacityLevel")
    cap_txt = _hw_capacity_label(cap_level)
    spot = _hw_spot_enabled(hw)
    tail: list[str] = []
    if specs:
        tail.append(specs)
    if cap_txt:
        tail.append(cap_txt)
    if spot:
        tail.append("Spot")
    if not tail:
        return name
    return f"{name} - " + " \u00b7 ".join(tail)


def list_hardware_tiers(project_id: Optional[str] = None) -> list[dict[str, Any]]:
    """Return available hardware tiers for a project.

    Requires *project_id* — does not fall back to the app project.

    Each dict includes ``id``, ``name``, ``isDefault``, ``option_label`` (for
    ``<select>`` option text mirroring Domino hardware tier summaries), and
    optional ``specs_subtitle`` / ``capacity_label`` derived from the v4 API.
    """
    pid = project_id
    if not pid:
        return []

    try:
        data = _domino_request("GET", f"/v4/projects/{pid}/hardwareTiers")
        tiers = data if isinstance(data, list) else data.get("hardwareTiers", data.get("data", []))
        results = []
        for t in tiers:
            row = t if isinstance(t, dict) else {}
            hw = row.get("hardwareTier", row) if isinstance(row, dict) else t
            if not isinstance(hw, dict):
                continue
            cap = row.get("capacity") if isinstance(row.get("capacity"), dict) else None
            is_default = hw.get("hwtFlags", {}).get("isDefault", False) if isinstance(hw.get("hwtFlags"), dict) else hw.get("isDefault", False)
            cap_level = cap.get("capacityLevel") if isinstance(cap, dict) else None
            results.append({
                "id": hw.get("id", ""),
                "name": hw.get("name") or hw.get("id", ""),
                "isDefault": bool(is_default),
                "specs_subtitle": _hw_specs_subtitle(hw),
                "capacity_label": _hw_capacity_label(cap_level),
                "option_label": _hw_option_label(hw, cap),
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


def _format_domino_datetime(raw: Any) -> str:
    if raw is None:
        return ""
    if isinstance(raw, (int, float)):
        try:
            ts = float(raw) / 1000.0 if raw > 1e12 else float(raw)
            dt = datetime.fromtimestamp(ts, tz=timezone.utc)
            return dt.strftime("%B %d, %Y")
        except Exception:
            return ""
    if isinstance(raw, str):
        s = raw.strip()
        if s.isdigit():
            return _format_domino_datetime(int(s))
        try:
            dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt.astimezone(timezone.utc).strftime("%B %d, %Y")
        except Exception:
            return s[:16]
    if isinstance(raw, dict):
        v = raw.get("$date")
        if isinstance(v, (int, float)):
            return _format_domino_datetime(v)
        if isinstance(v, str):
            return _format_domino_datetime(v)
    return ""


def _revision_option_label(rev: dict[str, Any]) -> str:
    num = rev.get("number")
    created = rev.get("created")
    date_s = _format_domino_datetime(created)
    prefix = f"#{num}" if num is not None else "#?"
    if date_s:
        return f"{prefix}: {date_s}"
    return prefix


def list_self_environments() -> list[dict[str, Any]]:
    try:
        data = _domino_request("GET", "/v4/environments/self")
        if isinstance(data, list):
            raw = data
        elif isinstance(data, dict):
            raw = data.get("environments", data.get("data", []))
        else:
            raw = []
        out: list[dict[str, Any]] = []
        for item in raw:
            if not isinstance(item, dict):
                continue
            eid = item.get("id")
            if eid is None:
                continue
            name = (item.get("name") or str(eid)).strip()
            out.append({"id": str(eid), "name": name})
        return out
    except Exception as exc:
        logger.warning("Failed to list self environments: %s", exc)
        return []


def list_environment_revisions(environment_id: str) -> list[dict[str, Any]]:
    eid = environment_id.strip()
    if not eid:
        return []
    try:
        data = _domino_request(
            "GET",
            f"/v4/environments/{eid}/page/0/pageSize/1000/revisions",
        )
        if isinstance(data, dict):
            raw_list = data.get("revisions", data.get("data", []))
        elif isinstance(data, list):
            raw_list = data
        else:
            raw_list = []
        revs: list[dict[str, Any]] = []
        for r in raw_list:
            if not isinstance(r, dict):
                continue
            rid = r.get("id")
            if rid is None:
                continue
            rid_s = str(rid)
            row = {
                "id": rid_s,
                "number": r.get("number"),
                "created": r.get("created"),
                "active": r.get("active"),
                "option_label": _revision_option_label(r),
            }
            revs.append(row)
        revs.sort(key=lambda x: (-(x.get("number") or 0), x.get("id") or ""))
        return revs
    except Exception as exc:
        logger.warning("Failed to list environment revisions: %s", exc)
        return []


# ---------------------------------------------------------------------------
# Job submission
# ---------------------------------------------------------------------------

def submit_job(
    command: str | list[str],
    branch: Optional[str],
    tier_id: str,
    project_id: str,
    environment_id: str,
    environment_revision_id: str,
) -> str:
    """Submit a Domino job via the v1 jobs API and return the job ID."""
    pid, pname, _ = get_project_context(project_id)

    title = f"AutoDoc: {pname or pid}" + (f" ({branch})" if branch else "")

    command_str = " ".join(command) if isinstance(command, list) else command

    payload: dict[str, Any] = {
        "projectId": pid,
        "commandToRun": command_str,
        "title": title,
    }
    tid = tier_id.strip()
    if tid:
        payload["overrideHardwareTierId"] = tid
    if branch:
        payload["mainRepoGitRef"] = {"type": "branches", "value": branch}

    eid = environment_id.strip()
    rid = environment_revision_id.strip()
    if eid:
        payload["environmentId"] = eid
        if rid:
            payload["environmentRevisionSpec"] = {"revisionId": rid}
        else:
            payload["environmentRevisionSpec"] = "ActiveRevision"

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


def build_job_url(run_id: str, project_id: str) -> str | None:
    """Return the Domino UI URL for a job."""
    if not _ui_host:
        return None

    _, pname, powner = get_project_context(project_id)
    if not powner or not pname:
        return None
    return f"{_ui_host}/jobs/{powner}/{pname}/{run_id}/logs?status=all"


def build_autodoc_dataset_data_page_url(project_id: str, dataset_id: str) -> str | None:
    """Return the Domino UI URL for the autodoc dataset data browser (rw upload path)."""
    from dataset_manager import AUTODOC_DATASET_NAME

    if not _ui_host:
        return None
    ds = (dataset_id or "").strip()
    if not ds:
        return None
    try:
        _, pname, powner = get_project_context(project_id)
    except ValueError:
        return None
    if not powner or not pname:
        return None
    seg = (AUTODOC_DATASET_NAME or "autodoc").strip()
    return f"{_ui_host}/u/{powner}/{pname}/data/rw/upload/{seg}/{ds}/docs"


def build_autodoc_artifacts_run_url(project_id: str, run_id: str) -> str | None:
    """Return the Domino UI URL for the artifacts browser at docs/<run_id[:8]>."""
    if not _ui_host:
        return None
    rid = (run_id or "").strip()
    if not rid:
        return None
    try:
        _, pname, powner = get_project_context(project_id)
    except ValueError:
        return None
    if not powner or not pname:
        return None
    short = rid[:8]
    return f"{_ui_host}/u/{powner}/{pname}/dfs/code/docs/{short}"


def download_artifact_at_head(project_id: str, artifact_path: str) -> bytes | None:
    """Download an artifact file from a project's DFS at HEAD.

    Uses GET /u/<owner>/<project>/raw/latest/<path>?inline=false, which redirects
    to the commit-pinned URL and returns the file bytes. Returns None on 404.
    """
    import httpx

    api_host = _resolve_api_host()
    if not api_host:
        return None
    try:
        _, pname, powner = get_project_context(project_id)
    except ValueError:
        return None
    if not powner or not pname:
        return None

    path = (artifact_path or "").lstrip("/")
    url = f"{api_host}/u/{powner}/{pname}/raw/latest/{path}"
    headers = _get_auth_headers()
    try:
        with httpx.Client(timeout=_DEFAULT_TIMEOUT, follow_redirects=True) as client:
            resp = client.get(url, params={"inline": "false"}, headers=headers)
            if resp.status_code == 404:
                return None
            resp.raise_for_status()
            return resp.content
    except Exception:
        logger.exception("download_artifact_at_head failed for %s %s", project_id, artifact_path)
        return None
