"""Domino Datasets API client using forwarded user identity.

All requests use the viewer's JWT captured by ``auth_context`` middleware
(extended identity propagation), ensuring dataset operations respect the
visiting user's permissions — not the app owner's.
"""

from __future__ import annotations

import logging
import os
import time
from typing import Any, Optional

import httpx

from domino_auth import resolve_api_host as _resolve_api_host
from domino_auth import current_auth as _current_auth


def _get_auth_headers() -> dict[str, str]:
    return _current_auth().to_headers()

logger = logging.getLogger(__name__)

AUTODOC_SPECS_DATASET = "autodoc"  # Legacy alias — use dataset_store.AUTODOC_DATASET_NAME
AUTODOC_SPECS_DESCRIPTION = (
    "Auto Model Docs artifacts — auto-created by Auto Model Docs Studio"
)

_RETRYABLE_STATUS_CODES = (408, 502, 503, 504)
_DEFAULT_TIMEOUT = 30.0
_DEFAULT_MAX_RETRIES = 2


# ---------------------------------------------------------------------------
# Core HTTP helper
# ---------------------------------------------------------------------------

def _api_request(
    method: str,
    path: str,
    *,
    json: Any = None,
    params: Optional[dict[str, Any]] = None,
    files: Optional[dict[str, Any]] = None,
    data: Optional[dict[str, Any]] = None,
    timeout: float = _DEFAULT_TIMEOUT,
    max_retries: int = _DEFAULT_MAX_RETRIES,
) -> httpx.Response:
    """Authenticated request to the Domino Datasets API."""
    base = _resolve_api_host()
    if not base:
        raise RuntimeError("No Domino API host configured")

    url = f"{base}{path}"
    last_exc: Exception | None = None

    for attempt in range(max_retries + 1):
        headers = _get_auth_headers()
        # Only set Content-Type for JSON requests (not multipart)
        if json is not None and files is None:
            headers["Content-Type"] = "application/json"
        try:
            with httpx.Client(timeout=timeout) as client:
                resp = client.request(
                    method, url,
                    json=json, params=params,
                    files=files, data=data,
                    headers=headers,
                )
                if resp.status_code in _RETRYABLE_STATUS_CODES and attempt < max_retries:
                    backoff = 2 ** attempt
                    time.sleep(backoff)
                    continue
                resp.raise_for_status()
                return resp
        except httpx.HTTPStatusError:
            raise
        except Exception as exc:
            last_exc = exc
            if attempt < max_retries:
                time.sleep(2 ** attempt)
                continue
            break

    raise RuntimeError(f"Datasets API {method} {path} failed: {last_exc}")


# ---------------------------------------------------------------------------
# List datasets (writable only)
# ---------------------------------------------------------------------------

def list_datasets(project_id: str) -> list[dict[str, Any]]:
    """List datasets for a project via the v4 datasets-v2 endpoint.

    Returns id, name, description, rwSnapshotId, and datasetPath per dataset.
    """
    resp = _api_request(
        "GET", "/v4/datasetrw/datasets-v2",
        params={
            "includeStorageInfo": "true",
            "projectIdsToInclude": project_id,
        },
    )
    items = resp.json()
    if not isinstance(items, list):
        items = items.get("datasets") or items.get("items") or []

    datasets: list[dict[str, Any]] = []
    for item in items:
        ds = item.get("datasetRwDto", item) if isinstance(item, dict) else item
        snapshot_ids = ds.get("snapshotIds") or []
        datasets.append({
            "id": ds.get("id", ""),
            "name": ds.get("name", ""),
            "description": ds.get("description", ""),
            "rwSnapshotId": ds.get("readWriteSnapshotId") or (snapshot_ids[0] if snapshot_ids else None),
            "datasetPath": ds.get("datasetPath", ""),
        })

    return datasets


# ---------------------------------------------------------------------------
# Create / ensure dataset
# ---------------------------------------------------------------------------

def _create_dataset(
    project_id: str, name: str, description: str,
) -> dict[str, Any]:
    payloads = [
        {"name": name, "projectId": project_id, "description": description},
        {"name": name, "projectId": project_id},
        {"datasetName": name, "projectId": project_id, "description": description},
    ]

    last_error = None
    for payload in payloads:
        try:
            resp = _api_request(
                "POST", "/api/datasetrw/v1/datasets",
                json=payload,
            )
            data = resp.json()
            # API may wrap the dataset object: {"dataset": {...}, "metadata": {...}}
            ds = data.get("dataset", data) if isinstance(data, dict) else data
            snapshot_ids = ds.get("snapshotIds") or []
            return {
                "id": ds.get("datasetId") or ds.get("id", ""),
                "name": ds.get("datasetName") or ds.get("name", name),
                "rwSnapshotId": ds.get("readWriteSnapshotId") or (snapshot_ids[0] if snapshot_ids else None),
                "datasetPath": (ds.get("datasetPath") or "").strip(),
            }
        except httpx.HTTPStatusError as exc:
            last_error = exc.response.text if exc.response else str(exc)
            if exc.response is not None and "marked for deletion" in exc.response.text:
                raise RuntimeError(
                    f"Dataset '{name}' is marked for deletion. "
                    "A Domino admin must complete the deletion."
                )
        except Exception as exc:
            last_error = str(exc)

    raise RuntimeError(f"Failed to create dataset '{name}': {last_error}")


def ensure_dataset(
    project_id: str,
    name: str = AUTODOC_SPECS_DATASET,
    description: str = AUTODOC_SPECS_DESCRIPTION,
) -> dict[str, Any]:
    """Return the named dataset if it exists; otherwise create it."""
    datasets = list_datasets(project_id)
    for row in datasets:
        if row["name"] == name:
            return row

    try:
        return _create_dataset(project_id, name, description)
    except Exception:
        logger.debug("Create failed for '%s', re-listing datasets", name, exc_info=True)

    datasets = list_datasets(project_id)
    for row in datasets:
        if row["name"] == name:
            return row

    raise RuntimeError(f"Failed to create or find dataset '{name}' in project {project_id}")


def get_existing_autodoc_dataset(
    project_id: str,
    name: str = AUTODOC_SPECS_DATASET,
) -> Optional[dict[str, Any]]:
    for row in list_datasets(project_id):
        if row.get("name") == name:
            return row
    return None


# ---------------------------------------------------------------------------
# Dataset detail (includes datasetPath)
# ---------------------------------------------------------------------------

def get_dataset_detail(dataset_id: str) -> dict[str, Any]:
    """Fetch full dataset metadata including datasetPath (mount location)."""
    resp = _api_request("GET", f"/v4/datasetrw/datasets/{dataset_id}")
    return resp.json()


def _dataset_path_from_detail_payload(detail: Any) -> str:
    if not isinstance(detail, dict):
        return ""
    path = (detail.get("datasetPath") or "").strip()
    if path:
        return path
    for key in ("datasetRwDto", "dataset"):
        inner = detail.get(key)
        if isinstance(inner, dict):
            path = (inner.get("datasetPath") or "").strip()
            if path:
                return path
    return ""


def resolve_dataset_mount_path(ensured: dict[str, Any]) -> str:
    path = (ensured.get("datasetPath") or "").strip()
    if path:
        return path
    ds_id = (ensured.get("id") or "").strip()
    if not ds_id:
        raise RuntimeError("Cannot resolve dataset mount path: missing dataset id")
    detail = get_dataset_detail(ds_id)
    path = _dataset_path_from_detail_payload(detail)
    if not path:
        raise RuntimeError(f"Cannot resolve dataset mount path for dataset {ds_id}")
    return path


# ---------------------------------------------------------------------------
# Snapshots
# ---------------------------------------------------------------------------

def get_rw_snapshot_id(dataset_id: str) -> Optional[str]:
    """Resolve the read-write (active) snapshot ID for a dataset."""
    try:
        resp = _api_request(
            "GET", f"/api/datasetrw/v1/datasets/{dataset_id}/snapshots",
            params={"limit": 5},
        )
        data = resp.json()
        for s in data.get("snapshots", []):
            if s.get("status", "").lower() == "active":
                return s.get("id")
        # Fallback: first snapshot
        snapshots = data.get("snapshots", [])
        if snapshots:
            return snapshots[0].get("id")
    except Exception:
        logger.warning("Failed to get snapshots for dataset %s", dataset_id, exc_info=True)
    return None


# ---------------------------------------------------------------------------
# File browsing
# ---------------------------------------------------------------------------

def list_files(snapshot_id: str, path: str = "") -> list[dict[str, Any]]:
    """List files in a dataset snapshot, returning only directories and yaml files."""
    resp = _api_request(
        "GET", f"/v4/datasetrw/files/{snapshot_id}",
        params={"path": path},
    )
    data = resp.json()
    rows = data.get("rows", [])

    # The Domino API may return fileName as a full relative path from the
    # dataset root (e.g. "subdir/file.yaml") even when browsing inside
    # "subdir".  The JS caller builds full paths by prepending the current
    # browse path, so we must strip the path prefix to avoid duplication
    # (e.g. "subdir/subdir/file.yaml").
    path_prefix = (path.rstrip("/") + "/") if path else ""

    files: list[dict[str, Any]] = []
    for row in rows:
        name_info = row.get("name", {})
        size_info = row.get("size", {})
        filename = name_info.get("fileName") or name_info.get("label", "")
        is_dir = name_info.get("isDirectory", False)

        # Strip parent path prefix if the API returned the full relative path
        if path_prefix and filename.startswith(path_prefix):
            filename = filename[len(path_prefix):]

        if is_dir or filename.lower().endswith((".yaml", ".yml")):
            files.append({
                "fileName": filename,
                "isDirectory": is_dir,
                "sizeInBytes": size_info.get("sizeInBytes") or name_info.get("sizeInBytes", 0),
                "lastModified": row.get("lastModified"),
            })

    return files


# ---------------------------------------------------------------------------
# File upload (v4 chunked API)
# ---------------------------------------------------------------------------

async def upload_file(
    dataset_id: str,
    file_path: str,
    content: bytes,
) -> None:
    """Upload a file to a dataset via the v4 chunked upload API.

    Uses httpx.AsyncClient for multipart uploads.
    """
    import hashlib
    import io

    headers = _get_auth_headers()
    base = _resolve_api_host()
    base_url = base.rstrip("/")

    # Step 1: start upload session
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.request(
            "POST",
            f"{base_url}/v4/datasetrw/datasets/{dataset_id}/snapshot/file/start",
            json={"filePaths": [file_path], "fileCollisionSetting": "Overwrite"},
            headers=headers,
        )
        resp.raise_for_status()

    upload_key = resp.json()
    if not isinstance(upload_key, str):
        upload_key = upload_key.get("upload_key") or upload_key.get("uploadKey") or upload_key.get("key")
    if not upload_key:
        raise RuntimeError(f"Failed to start upload session for dataset {dataset_id}")

    try:
        # Step 2: upload single chunk
        identifier = file_path.replace(".", "-").replace("/", "-")
        checksum = hashlib.md5(content).hexdigest()
        chunk_params = {
            "key": upload_key,
            "resumableChunkNumber": 1,
            "resumableChunkSize": len(content),
            "resumableCurrentChunkSize": len(content),
            "resumableTotalChunks": 1,
            "resumableIdentifier": identifier,
            "resumableRelativePath": file_path,
            "checksum": checksum,
        }
        # Csrf-Token: nocheck bypasses Play framework CSRF protection on multipart POSTs
        chunk_headers = {**headers, "Csrf-Token": "nocheck"}
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.request(
                "POST",
                f"{base_url}/v4/datasetrw/datasets/{dataset_id}/snapshot/file",
                params=chunk_params,
                files={file_path: (file_path, io.BytesIO(content), "application/octet-stream")},
                headers=chunk_headers,
            )
            resp.raise_for_status()

        # Step 3: finalize
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.request(
                "GET",
                f"{base_url}/v4/datasetrw/datasets/{dataset_id}/snapshot/file/end/{upload_key}",
                headers=headers,
            )
            resp.raise_for_status()

    except Exception:
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                await client.request(
                    "GET",
                    f"{base_url}/v4/datasetrw/datasets/{dataset_id}/snapshot/file/cancel/{upload_key}",
                    headers=headers,
                )
        except Exception:
            pass
        raise

