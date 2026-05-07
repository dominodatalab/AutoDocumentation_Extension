"""API routes: branches, hardware tiers, language detection, datasets, etc."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Optional

from starlette.requests import Request
from starlette.responses import FileResponse, Response

from autodoc.core.models import DocumentSpec
from authorization import require_project_write

from .state import (
    _get_default_code_root,
    _resolve_request_project_id,
    domino_client,
    domino_datasets,
)

logger = logging.getLogger(__name__)


def sanitize_dataset_subpath(raw: Optional[str]) -> str:
    if raw is None or not str(raw).strip():
        return ""
    parts: list[str] = []
    for seg in str(raw).replace("\\", "/").strip().strip("/").split("/"):
        if not seg or seg == ".":
            continue
        if seg == "..":
            raise ValueError("Invalid relativeDir")
        parts.append(seg)
    return "/".join(parts)


def register_api_routes(rt):
    """Register all /api/* routes on the given rt decorator."""

    async def api_branches(req: Request):
        project_id = _resolve_request_project_id(req)
        search = req.query_params.get("search", "")
        if project_id:
            branches = domino_client.list_branches_api(project_id, search=search)
            if branches:
                return Response(
                    json.dumps([{"name": b["name"], "value": b["name"]} for b in branches]),
                    media_type="application/json",
                )
        return Response(json.dumps([]), media_type="application/json")

    rt("/api/branches")(api_branches)

    async def api_hardware_tiers(req: Request):
        project_id = _resolve_request_project_id(req)
        tiers = domino_client.list_hardware_tiers(project_id=project_id)
        default_tier = domino_client.get_project_default_tier()
        result = []
        for t in tiers:
            tid = t.get("id", "")
            tname = t.get("name") or tid
            label = t.get("option_label") or tname
            is_default = t.get("isDefault", False) or tid == default_tier
            result.append({"id": tid, "label": label, "isDefault": is_default})
        return Response(json.dumps(result), media_type="application/json")

    rt("/api/hardware-tiers")(api_hardware_tiers)

    async def api_environment_revisions(req: Request):
        env_id = (req.query_params.get("environmentId") or "").strip()
        if not env_id:
            return Response(json.dumps([]), media_type="application/json")
        revs = domino_client.list_environment_revisions(env_id)
        result = []
        for i, r in enumerate(revs):
            rid = r.get("id", "")
            label = r.get("option_label") or rid
            result.append({"id": rid, "label": label, "isDefault": i == 0})
        return Response(json.dumps(result), media_type="application/json")

    rt("/api/environment-revisions")(api_environment_revisions)

    def api_detect_language(req: Request):
        from autodoc.core.models import detect_language as _detect_lang, LANGUAGE_PROFILES

        code_root_param = req.query_params.get("code_root", "")
        if code_root_param:
            code_root = Path(code_root_param)
        else:
            code_root = _get_default_code_root()

        profile, count = _detect_lang(code_root)
        if profile:
            return Response(
                json.dumps({
                    "language": profile.name,
                    "display_name": profile.display_name,
                    "file_count": count,
                }),
                media_type="application/json",
            )
        return Response(
            json.dumps({
                "language": None,
                "display_name": None,
                "file_count": 0,
                "supported": list(LANGUAGE_PROFILES.keys()),
            }),
            media_type="application/json",
        )

    rt("/api/detect-language")(api_detect_language)

    async def api_datasets(req: Request):
        """List writable datasets for the project.

        Each item includes datasetPath from Domino's datasets-v2 list response
        (see domino_datasets.list_datasets; includeStorageInfo on that API).
        """
        pid = _resolve_request_project_id(req)
        require_project_write(pid)
        try:
            datasets = domino_datasets.list_datasets(pid)
            return Response(json.dumps(datasets), media_type="application/json")
        except Exception as exc:
            return Response(
                json.dumps({"error": str(exc)}),
                status_code=500,
                media_type="application/json",
            )

    rt("/api/datasets")(api_datasets)

    async def api_dataset_files(req: Request):
        """Browse files in a dataset (directories + yaml only)."""
        dataset_id = req.query_params.get("datasetId", "")
        snapshot_id = req.query_params.get("snapshotId", "")
        path = req.query_params.get("path", "")
        pid = _resolve_request_project_id(req)
        require_project_write(pid)

        if not dataset_id:
            return Response(
                json.dumps({"error": "datasetId required"}),
                status_code=400,
                media_type="application/json",
            )

        if not snapshot_id:
            snapshot_id = domino_datasets.get_rw_snapshot_id(dataset_id)
        if not snapshot_id:
            return Response(
                json.dumps({"error": "Could not resolve snapshot for dataset"}),
                status_code=400,
                media_type="application/json",
            )

        try:
            files = domino_datasets.list_files(snapshot_id, path)
            return Response(json.dumps(files), media_type="application/json")
        except Exception as exc:
            return Response(
                json.dumps({"error": str(exc)}),
                status_code=500,
                media_type="application/json",
            )

    rt("/api/dataset-files")(api_dataset_files)

    async def api_upload_spec_to_dataset(req: Request):
        """Upload a spec file to a dataset."""
        pid = _resolve_request_project_id(req)
        require_project_write(pid)
        form = await req.form()
        file_upload = form.get("file")
        dataset_id = form.get("datasetId", "")

        if not file_upload or not hasattr(file_upload, "read"):
            return Response(
                json.dumps({"error": "file is required"}),
                status_code=400,
                media_type="application/json",
            )
        if not dataset_id:
            return Response(
                json.dumps({"error": "datasetId is required"}),
                status_code=400,
                media_type="application/json",
            )

        raw_filename = getattr(file_upload, "filename", "spec.yaml")
        filename = raw_filename.rsplit("/", 1)[-1].rsplit("\\", 1)[-1] or "spec.yaml"
        content = await file_upload.read()

        try:
            rel_dir = sanitize_dataset_subpath(
                str(form.get("relativeDir", "") or "").strip()
            )
        except ValueError as exc:
            return Response(
                json.dumps({"error": str(exc)}),
                status_code=400,
                media_type="application/json",
            )

        fn_low = filename.lower()
        if fn_low.endswith((".yaml", ".yml")):
            try:
                text = content.decode("utf-8")
            except UnicodeDecodeError:
                return Response(
                    json.dumps({
                        "error": "Spec file must be valid UTF-8",
                        "valid": False,
                        "errors": ["File is not valid UTF-8"],
                    }),
                    status_code=400,
                    media_type="application/json",
                )
            val_errors = DocumentSpec.validate_spec(text)
            if val_errors:
                return Response(
                    json.dumps({
                        "error": "Spec validation failed",
                        "valid": False,
                        "errors": val_errors,
                    }),
                    status_code=400,
                    media_type="application/json",
                )

        try:
            from dataset_manager import DatasetManager
            upload_path = f"{rel_dir}/{filename}" if rel_dir else filename
            DatasetManager.write_file(dataset_id, upload_path, content)
            return Response(
                json.dumps({
                    "path": upload_path,
                    "fileName": filename,
                    "valid": True,
                }),
                media_type="application/json",
            )
        except Exception as exc:
            return Response(
                json.dumps({"error": str(exc)}),
                status_code=500,
                media_type="application/json",
            )

    rt("/api/upload-spec-to-dataset")(api_upload_spec_to_dataset)

    def api_download_template():
        template_path = Path(__file__).resolve().parent.parent / "doc_spec.yaml"
        if not template_path.exists():
            return Response("Template not found", status_code=404)
        return FileResponse(
            str(template_path),
            media_type="application/x-yaml",
            filename="doc_spec_template.yaml",
        )

    rt("/api/download-template")(api_download_template)

    async def api_code_root_options(req: Request):
        pid = (_resolve_request_project_id(req) or "").strip()

        def _error_payload(reason: str) -> dict:
            return {
                "isGitBasedProject": None,
                "defaultRoot": "",
                "options": [],
                "error": reason,
            }

        if not pid:
            return Response(
                json.dumps(_error_payload("missing_project_id")),
                media_type="application/json",
            )
        info = domino_client.resolve_project(pid)
        if not info:
            return Response(
                json.dumps(_error_payload("project_resolve_failed")),
                media_type="application/json",
            )
        try:
            raw = domino_client.browse_code(info.owner_username, info.name, path_string="")
            payload = domino_client.code_root_options_from_browse_response(raw)
            payload["error"] = None
            return Response(json.dumps(payload), media_type="application/json")
        except Exception as exc:
            detail = str(exc)
            if hasattr(exc, "response") and exc.response is not None:
                try:
                    detail = f"{exc} body={exc.response.text[:1500]!r}"
                except Exception:
                    pass
            logger.warning("browseCode for code-root-options failed: %s", detail)
            return Response(
                json.dumps(_error_payload("browse_code_failed")),
                media_type="application/json",
            )

    rt("/api/code-root-options")(api_code_root_options)
