"""Stateless facade for Domino Dataset file I/O.

All methods on DatasetManager are @staticmethod; the class deliberately has
no instance or class members. Callers pass the ids (dataset_id, snapshot_id)
that each individual endpoint needs. There is no cache, no singleton, and no
shared state across requests.
"""

from __future__ import annotations

import base64
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


def _try_base64_decode_utf8(s: str) -> str | None:
    raw = s.replace("\n", "").replace("\r", "").strip()
    if not raw:
        return None
    try:
        decoded = base64.b64decode(raw, validate=False)
    except Exception:
        return None
    try:
        return decoded.decode("utf-8")
    except UnicodeDecodeError:
        return None


_PREVIEW_BODY_KEYS = (
    "content",
    "fileContent",
    "body",
    "text",
    "data",
    "yaml",
    "spec",
    "blob",
    "raw",
    "value",
)


def _decode_preview_json_string(s: str) -> str | None:
    u = s.lstrip("\ufeff")
    if not u.strip():
        return None
    lead = u.lstrip()
    if not lead or lead[0] not in "{[":
        return u
    try:
        inner = json.loads(u)
    except Exception:
        return u
    if isinstance(inner, (dict, list)):
        hit = _preview_payload_to_file_text(inner)
        return hit or u
    if isinstance(inner, str):
        nested = _decode_preview_json_string(inner)
        return nested or u
    return u


def _preview_payload_to_file_text(obj: Any) -> str | None:
    if isinstance(obj, dict):
        for nk in ("file", "result", "payload", "preview"):
            inner = obj.get(nk)
            if isinstance(inner, (dict, list)):
                hit = _preview_payload_to_file_text(inner)
                if hit:
                    return hit
        for key in _PREVIEW_BODY_KEYS:
            val = obj.get(key)
            if isinstance(val, str) and val.strip():
                hit = _decode_preview_json_string(val)
                if hit:
                    return hit
            if isinstance(val, (dict, list)):
                hit = _preview_payload_to_file_text(val)
                if hit:
                    return hit
        for key in ("contentBase64", "base64Content", "fileContentBase64", "encodedContent"):
            val = obj.get(key)
            if isinstance(val, str) and val.strip():
                dec = _try_base64_decode_utf8(val)
                if dec is not None:
                    return dec
        data_val = obj.get("data")
        if isinstance(data_val, str) and data_val.strip():
            hit = _decode_preview_json_string(data_val)
            if hit:
                return hit
        for _k, v in obj.items():
            if isinstance(v, (dict, list)):
                hit = _preview_payload_to_file_text(v)
                if hit:
                    return hit
            if isinstance(v, str) and v.strip():
                lead = v.lstrip("\ufeff").lstrip()
                if lead and lead[0] in "{[":
                    hit = _decode_preview_json_string(v)
                    if hit:
                        return hit
    if isinstance(obj, list):
        for item in obj:
            hit = _preview_payload_to_file_text(item)
            if hit:
                return hit
    return None


def _bytes_from_snapshot_preview_response(resp: httpx.Response) -> bytes:
    content = resp.content or b""
    ctype = (resp.headers.get("content-type") or "").lower()
    if "json" not in ctype and content[:1] != b"{":
        return content
    try:
        text = content.decode("utf-8")
        payload = json.loads(text)
    except Exception:
        return content
    if isinstance(payload, str) and payload.strip():
        hit = _decode_preview_json_string(payload)
        if hit:
            return hit.encode("utf-8")
        return payload.lstrip("\ufeff").encode("utf-8")
    if isinstance(payload, dict):
        hit = _preview_payload_to_file_text(payload)
        if hit:
            return hit.encode("utf-8")
    if isinstance(payload, list):
        hit = _preview_payload_to_file_text(payload)
        if hit:
            return hit.encode("utf-8")
    return content


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

        Endpoint: GET /v4/datasetrw/snapshot/{snapshotId}/file/preview?path=
        """
        base_url = _resolve_api_host().rstrip("/")
        with httpx.Client(timeout=60.0) as client:
            resp = client.get(
                f"{base_url}/v4/datasetrw/snapshot/{snapshot_id}/file/preview",
                params={"path": path},
                headers=_get_auth_headers(),
            )
            resp.raise_for_status()
        data = resp.content or b""
        ctype = (resp.headers.get("content-type") or "").lower()
        for _ in range(8):
            fake = httpx.Response(200, headers={"content-type": ctype or "application/json"}, content=data)
            nxt = _bytes_from_snapshot_preview_response(fake)
            if nxt == data:
                return data
            data = nxt
            ctype = ""
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
        with httpx.Client(timeout=30.0) as client:
            resp = client.get(
                f"{base_url}/v4/datasetrw/files/{snapshot_id}",
                params={"path": path},
                headers=_get_auth_headers(),
            )
            resp.raise_for_status()

        data = resp.json()
        rows = data.get("rows", [])

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
        return files

    @staticmethod
    def file_exists(snapshot_id: str, path: str) -> bool:
        """True iff the file exists (per the metadata endpoint)."""
        try:
            DatasetManager.read_file_meta(snapshot_id, path)
            return True
        except Exception:
            return False


