"""API routes: hardware tiers, datasets, etc."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Optional

from starlette.requests import Request
from starlette.responses import FileResponse, Response

from autodoc.core.models import DocumentSpec
from authorization import require_project_write
from dataset_manager import DatasetManager

from .state import (
    _resolve_request_project_id,
    domino_client,
    domino_datasets,
)

logger = logging.getLogger(__name__)


def _autodoc_dataset_and_snapshot(project_id: str) -> tuple[dict, str]:
    require_project_write(project_id)
    ensured = domino_datasets.ensure_dataset(project_id)
    ds_id = str(ensured.get("id") or "").strip()
    if not ds_id:
        raise RuntimeError("autodoc dataset has no id")
    snap = ensured.get("rwSnapshotId") or domino_datasets.get_rw_snapshot_id(ds_id)
    if not snap:
        raise RuntimeError("Could not resolve read-write snapshot for autodoc dataset")
    return ensured, str(snap)


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
            import spec_template_sync

            upload_path = f"{rel_dir}/{filename}" if rel_dir else filename
            DatasetManager.write_file(dataset_id, upload_path, content)
            if fn_low.endswith((".yaml", ".yml")):
                try:
                    spec_template_sync.sync_builtins_to_autodoc_dataset(dataset_id)
                except Exception:
                    logger.warning("sync built-ins after spec upload failed", exc_info=True)
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
        template_path = Path(__file__).resolve().parent.parent / "spec-templates" / "doc_spec.yaml"
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

    async def api_built_in_templates(req: Request):
        import spec_template_sync

        pid = (_resolve_request_project_id(req) or "").strip()
        if not pid:
            return Response(json.dumps([]), media_type="application/json")
        try:
            _, snap = _autodoc_dataset_and_snapshot(pid)
        except Exception as exc:
            return Response(
                json.dumps({"error": str(exc)}),
                status_code=500,
                media_type="application/json",
            )
        try:
            catalog = spec_template_sync.catalog_from_dataset(snap)
            return Response(json.dumps(catalog), media_type="application/json")
        except Exception:
            logger.exception("built-in-templates catalog failed")
            return Response(
                json.dumps({"error": "catalog failed"}),
                status_code=500,
                media_type="application/json",
            )

    rt("/api/built-in-templates")(api_built_in_templates)

    async def api_built_in_template_yaml(req: Request, filename: str):
        import spec_template_sync

        pid = (_resolve_request_project_id(req) or "").strip()
        if not pid:
            return Response("projectId required", status_code=400)
        base = (filename or "").strip().replace("\\", "/").split("/")[-1]
        if base not in spec_template_sync.allowed_template_filenames():
            return Response("Not found", status_code=404)
        try:
            _, snap = _autodoc_dataset_and_snapshot(pid)
            raw = DatasetManager.read_file(snap, spec_template_sync.dataset_rel_path(base))
        except Exception as exc:
            logger.warning("built-in-template read failed: %s", exc, exc_info=True)
            return Response(str(exc), status_code=500)
        return Response(content=raw, media_type="text/yaml; charset=utf-8")

    rt("/api/built-in-template/{filename}")(api_built_in_template_yaml)

    async def api_sync_spec_templates(req: Request):
        import spec_template_sync

        pid = (_resolve_request_project_id(req) or "").strip()
        if not pid:
            return Response(
                json.dumps({"error": "projectId required"}),
                status_code=400,
                media_type="application/json",
            )
        try:
            ensured, _snap = _autodoc_dataset_and_snapshot(pid)
            ds_id = str(ensured.get("id") or "").strip()
            spec_template_sync.sync_builtins_to_autodoc_dataset(ds_id)
            return Response(json.dumps({"ok": True}), media_type="application/json")
        except Exception as exc:
            logger.exception("sync-spec-templates failed")
            return Response(
                json.dumps({"error": str(exc)}),
                status_code=500,
                media_type="application/json",
            )

    rt("/api/sync-spec-templates")(api_sync_spec_templates)
