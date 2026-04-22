"""API routes: branches, hardware tiers, language detection, datasets, etc."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Optional

from fasthtml.common import *
from starlette.requests import Request
from starlette.responses import FileResponse, Response

from authorization import require_project_write

from .state import (
    _get_default_code_root,
    _resolve_request_project_id,
    bootstrap_dataset_ctx,
    domino_client,
    domino_datasets,
)

logger = logging.getLogger(__name__)


def register_api_routes(rt):
    """Register all /api/* routes on the given rt decorator."""

    async def api_branches(req: Request):
        """Return an HTML fragment for branch selection.

        Fetches branches from the target project's git repo via the
        Domino API.  Falls back to a text input if the API fails.
        """
        project_id = req.query_params.get("projectId") or None
        search = req.query_params.get("search", "")
        if project_id:
            branches = domino_client.list_branches_api(project_id, search=search)
            if branches:
                options = [Option(b["name"], value=b["name"]) for b in branches]
                return Select(*options, name="branch", id="field-branch")
        # Fallback: free-text input
        return Input(name="branch", id="field-branch", type="text", value="", placeholder="Default branch")

    rt("/api/branches")(api_branches)

    async def api_hardware_tiers(req: Request):
        """Return an HTML <select> fragment with available hardware tiers."""
        project_id = req.query_params.get("projectId") or None
        tiers = domino_client.list_hardware_tiers(project_id=project_id)
        default_tier = domino_client.get_project_default_tier()
        options = []
        for t in tiers:
            tid = t.get("id", "")
            tname = t.get("name") or tid
            is_default = t.get("isDefault", False) or tid == default_tier
            options.append(Option(tname, value=tid, selected=is_default))
        if not options:
            options = [Option("(default)", value="")]
        return Select(*options, name="hardware_tier", id="field-hardware_tier")

    rt("/api/hardware-tiers")(api_hardware_tiers)

    def api_detect_language(req: Request):
        """Detect project language by counting source files in code_root."""
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
        """List writable datasets for the project."""
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

        # Resolve snapshot ID if not provided
        if not snapshot_id:
            snapshot_id = domino_datasets.get_rw_snapshot_id(dataset_id, pid)
        if not snapshot_id:
            return Response(
                json.dumps({"error": "Could not resolve snapshot for dataset"}),
                status_code=400,
                media_type="application/json",
            )

        try:
            files = domino_datasets.list_files(snapshot_id, path, pid)
            return Response(json.dumps(files), media_type="application/json")
        except Exception as exc:
            return Response(
                json.dumps({"error": str(exc)}),
                status_code=500,
                media_type="application/json",
            )

    rt("/api/dataset-files")(api_dataset_files)

    async def api_ensure_autodoc_specs(req: Request):
        """Ensure the autodoc dataset exists, return its metadata.

        Uses the unified 'autodoc' dataset (not the legacy 'autodoc-specs').
        Specs live under the specs/ subdirectory within this dataset.
        """
        pid = _resolve_request_project_id(req)
        require_project_write(pid)
        try:
            from dataset_manager import AUTODOC_DATASET_NAME
            ds = domino_datasets.ensure_dataset(
                pid,
                name=AUTODOC_DATASET_NAME,
                description="Auto Model Docs artifacts",
            )
            if not ds.get("id"):
                raise RuntimeError("Dataset was created/found but has no ID — check Domino Datasets API response")
            if not ds.get("rwSnapshotId"):
                ds["rwSnapshotId"] = domino_datasets.get_rw_snapshot_id(ds["id"], pid)
            return Response(json.dumps(ds), media_type="application/json")
        except Exception as exc:
            return Response(
                json.dumps({"error": str(exc)}),
                status_code=500,
                media_type="application/json",
            )

    rt("/api/ensure-autodoc-specs")(api_ensure_autodoc_specs)

    async def api_upload_spec_to_dataset(req: Request):
        """Upload a spec file via the DatasetStore."""
        pid = _resolve_request_project_id(req)
        require_project_write(pid)
        form = await req.form()
        file_upload = form.get("file")

        if not file_upload or not hasattr(file_upload, "read"):
            return Response(
                json.dumps({"error": "file is required"}),
                status_code=400,
                media_type="application/json",
            )

        raw_filename = getattr(file_upload, "filename", "spec.yaml")
        # Sanitize: strip path components to prevent directory traversal
        filename = raw_filename.rsplit("/", 1)[-1].rsplit("\\", 1)[-1] or "spec.yaml"
        content = await file_upload.read()

        try:
            from artifact_layout import get_layout
            from dataset_ctx import get_dataset_ctx
            from dataset_manager import DatasetManager
            bootstrap_dataset_ctx(pid)
            upload_path = f"{get_layout().specs_dir}/{filename}"
            DatasetManager.write_file(
                get_dataset_ctx().dataset_id, upload_path, content
            )
            return Response(
                json.dumps({"path": upload_path, "fileName": filename}),
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
        """Serve the bundled doc_spec.yaml as a downloadable reference template."""
        # doc_spec.yaml is in auto_model_docs/ (parent of studio/)
        template_path = Path(__file__).resolve().parent.parent / "doc_spec.yaml"
        if not template_path.exists():
            return Response("Template not found", status_code=404)
        return FileResponse(
            str(template_path),
            media_type="application/x-yaml",
            filename="doc_spec_template.yaml",
        )

    rt("/api/download-template")(api_download_template)

    async def api_resolve_project(req: Request):
        """Return resolved project name for a given project ID."""
        pid = req.query_params.get("projectId", "").strip()
        if not pid:
            return Div(id="project-id-resolved")
        info = domino_client.resolve_project(pid)
        if info:
            return Div(
                f"{info.owner_username}/{info.name}",
                id="project-id-resolved",
                cls="resolved",
                data_project_name=info.name,
            )
        return Div(
            "Could not resolve project ID",
            id="project-id-resolved",
            cls="error",
        )

    rt("/api/resolve-project")(api_resolve_project)
