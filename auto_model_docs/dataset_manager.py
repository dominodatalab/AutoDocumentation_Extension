"""Stateless facade for Domino Dataset file I/O.

All methods on DatasetManager are @staticmethod; the class deliberately has
no instance or class members. Callers pass the ids (dataset_id, snapshot_id)
that each individual endpoint needs. There is no cache, no singleton, and no
shared state across requests.
"""

from __future__ import annotations

import hashlib
import io
import json
import logging
from typing import Any

import httpx

from domino_auth import current_auth as _current_auth
from domino_auth import resolve_api_host as _resolve_api_host

logger = logging.getLogger(__name__)

AUTODOC_DATASET_NAME = "autodoc"
AUTODOC_DATASET_DESCRIPTION = (
    "Auto Model Docs artifacts - generated docs, specs, and internal state"
)


def _get_auth_headers() -> dict[str, str]:
    return _current_auth().to_headers()


class DatasetManager:
    """Pure-static facade for Domino Datasets v4 file operations.

    Do NOT instantiate. There is no __init__ beyond the default object one,
    and no class/instance attributes. Tests enforce both invariants.
    """

    @staticmethod
    def write_file(dataset_id: str, path: str, content: bytes) -> None:
        """Upload a file to a dataset, overwriting if it exists.

        Chunked upload flow:
          POST /v4/datasetrw/datasets/{id}/snapshot/file/start
          POST /v4/datasetrw/datasets/{id}/snapshot/file   (chunk)
          GET  /v4/datasetrw/datasets/{id}/snapshot/file/end/{key}
        """
        base_url = _resolve_api_host().rstrip("/")
        upload_key = None
        try:
            headers = _get_auth_headers()
            with httpx.Client(timeout=30.0) as client:
                resp = client.post(
                    f"{base_url}/v4/datasetrw/datasets/{dataset_id}/snapshot/file/start",
                    json={"filePaths": [path], "fileCollisionSetting": "Overwrite"},
                    headers=headers,
                )
                resp.raise_for_status()

            upload_key = resp.json()
            if not isinstance(upload_key, str):
                upload_key = (
                    upload_key.get("upload_key")
                    or upload_key.get("uploadKey")
                    or upload_key.get("key")
                )
            if not upload_key:
                raise RuntimeError(f"Failed to start upload for {path}")

            identifier = path.replace(".", "-").replace("/", "-")
            checksum = hashlib.md5(content).hexdigest()
            chunk_params = {
                "key": upload_key,
                "resumableChunkNumber": 1,
                "resumableChunkSize": len(content),
                "resumableCurrentChunkSize": len(content),
                "resumableTotalChunks": 1,
                "resumableIdentifier": identifier,
                "resumableRelativePath": path,
                "checksum": checksum,
            }
            chunk_headers = {**_get_auth_headers(), "Csrf-Token": "nocheck"}
            with httpx.Client(timeout=60.0) as client:
                resp = client.post(
                    f"{base_url}/v4/datasetrw/datasets/{dataset_id}/snapshot/file",
                    params=chunk_params,
                    files={path: (path, io.BytesIO(content), "application/octet-stream")},
                    headers=chunk_headers,
                )
                resp.raise_for_status()

            with httpx.Client(timeout=30.0) as client:
                resp = client.get(
                    f"{base_url}/v4/datasetrw/datasets/{dataset_id}/snapshot/file/end/{upload_key}",
                    headers=_get_auth_headers(),
                )
                resp.raise_for_status()

        except Exception:
            if upload_key:
                try:
                    with httpx.Client(timeout=10.0) as client:
                        client.get(
                            f"{base_url}/v4/datasetrw/datasets/{dataset_id}/snapshot/file/cancel/{upload_key}",
                            headers=_get_auth_headers(),
                        )
                except Exception as cancel_exc:
                    logger.warning(
                        "Failed to cancel upload %s for dataset %s: %s",
                        upload_key, dataset_id, cancel_exc,
                    )
            raise

    @staticmethod
    def read_file(snapshot_id: str, path: str) -> bytes:
        """Download file content from a snapshot.

        Endpoint: GET /v4/datasetrw/snapshot/{snapshotId}/file/raw?path=
        """
        base_url = _resolve_api_host().rstrip("/")
        url = f"{base_url}/v4/datasetrw/snapshot/{snapshot_id}/file/raw"
        logger.info(
            "DatasetManager.read_file: GET %s params=%r snapshot_id=%r",
            url,
            {"path": path},
            snapshot_id,
        )
        with httpx.Client(timeout=60.0) as client:
            resp = client.get(
                url,
                params={"path": path},
                headers=_get_auth_headers(),
            )
            resp.raise_for_status()
        hdrs = getattr(resp, "headers", {}) or {}
        data = resp.content or b""
        logger.info(
            "DatasetManager.read_file: response status=%s content-type=%r len=%d",
            getattr(resp, "status_code", 200),
            (hdrs.get("content-type") or "")[:120],
            len(data),
        )
        return data

    @staticmethod
    def read_file_meta(snapshot_id: str, path: str) -> dict[str, Any]:
        """Get file metadata (size, last modified, etc.).

        Endpoint: GET /v4/datasetrw/snapshot/{snapshotId}/file/meta?path=
        """
        base_url = _resolve_api_host().rstrip("/")
        with httpx.Client(timeout=30.0) as client:
            resp = client.get(
                f"{base_url}/v4/datasetrw/snapshot/{snapshot_id}/file/meta",
                params={"path": path},
                headers=_get_auth_headers(),
            )
            resp.raise_for_status()
        return resp.json()

    @staticmethod
    def list_files(snapshot_id: str, path: str = "") -> list[dict[str, Any]]:
        """List files at a path within a snapshot.

        Endpoint: GET /v4/datasetrw/files/{snapshotId}?path=
        """
        base_url = _resolve_api_host().rstrip("/")
        url = f"{base_url}/v4/datasetrw/files/{snapshot_id}"
        logger.info(
            "DatasetManager.list_files: GET %s params=%r snapshot_id=%r",
            url,
            {"path": path},
            snapshot_id,
        )
        with httpx.Client(timeout=30.0) as client:
            resp = client.get(
                url,
                params={"path": path},
                headers=_get_auth_headers(),
            )
            resp.raise_for_status()

        data = resp.json()
        rows = data.get("rows", [])
        logger.info(
            "DatasetManager.list_files: rows=%d snapshot_id=%r path=%r",
            len(rows),
            snapshot_id,
            path,
        )

        path_prefix = (path.rstrip("/") + "/") if path else ""
        files: list[dict[str, Any]] = []
        for row in rows:
            name_info = row.get("name", {})
            size_info = row.get("size", {})
            filename = name_info.get("fileName") or name_info.get("label", "")
            is_dir = name_info.get("isDirectory", False)

            if path_prefix and filename.startswith(path_prefix):
                filename = filename[len(path_prefix):]

            files.append({
                "fileName": filename,
                "isDirectory": is_dir,
                "sizeInBytes": size_info.get("sizeInBytes") or name_info.get("sizeInBytes", 0),
                "lastModified": row.get("lastModified"),
            })
        names_out = [f["fileName"] for f in files]
        logger.info(
            "DatasetManager.list_files: normalized %d file entries fileNames=%r",
            len(files),
            names_out[:50],
        )
        return files

    @staticmethod
    def file_exists(snapshot_id: str, path: str) -> bool:
        """True iff the file exists (per the metadata endpoint)."""
        try:
            DatasetManager.read_file_meta(snapshot_id, path)
            return True
        except Exception:
            return False


