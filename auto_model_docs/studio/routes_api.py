"""API routes: branches, hardware tiers, language detection, datasets, etc."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Optional

from starlette.requests import Request
from starlette.responses import FileResponse, Response

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


_BUILTIN_TEMPLATE_FILES = [
    {
        "slug": "standard_ml",
        "name": "Standard ML Model Doc",
        "description": "Full documentation for production ML models with MLflow experiment tracking.",
        "icon": "model_training",
        "file": "doc_spec.yaml",
    },
    {
        "slug": "llm_eval",
        "name": "LLM Evaluation Report",
        "description": "Evaluation results for large language model deployments across benchmarks and tasks.",
        "icon": "psychology",
        "file": "doc_spec_llm_eval.yaml",
    },
    {
        "slug": "fairness",
        "name": "Fairness & Bias Report",
        "description": "Bias analysis, fairness metrics, and mitigation documentation for regulated use cases.",
        "icon": "balance",
        "file": "doc_spec_fairness.yaml",
    },
    {
        "slug": "executive",
        "name": "Executive Summary",
        "description": "High-level model summary written for non-technical stakeholders and leadership.",
        "icon": "summarize",
        "file": "doc_spec_executive.yaml",
    },
]

_TEMPLATES_DIR = Path(__file__).resolve().parent.parent


def _load_builtin_templates() -> list:
    """Load all built-in templates, parsing their YAML for section metadata."""
    import yaml as _yaml  # type: ignore

    result = []
    for meta in _BUILTIN_TEMPLATE_FILES:
        path = _TEMPLATES_DIR / meta["file"]
        try:
            raw = path.read_text(encoding="utf-8")
            parsed = _yaml.safe_load(raw)
        except Exception:
            continue

        sections_raw = parsed.get("sections", [])
        sections = []
        per_model = []
        for s in sections_raw:
            if isinstance(s, str):
                if ": per_model" in s:
                    name = s.replace(": per_model", "").strip()
                    sections.append(name)
                    per_model.append(name)
                else:
                    sections.append(s)
            elif isinstance(s, dict):
                name = s.get("name", "")
                sections.append(name)
                if s.get("per_model"):
                    per_model.append(name)

        result.append({
            "slug": meta["slug"],
            "name": parsed.get("card_title") or meta["name"],
            "description": parsed.get("card_description") or meta["description"],
            "icon": meta["icon"],
            "sections": sections,
            "per_model_sections": per_model,
            "yaml_content": raw,
            "filename": meta["file"],
        })
    return result


def register_api_routes(rt):
    """Register all /api/* routes on the given rt decorator."""

    async def api_branches(req: Request):
        project_id = req.query_params.get("projectId") or None
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
        project_id = req.query_params.get("projectId") or None
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

        Each dataset includes datasetPath from the detail API.
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

        try:
            from dataset_manager import DatasetManager
            upload_path = f"{rel_dir}/{filename}" if rel_dir else filename
            DatasetManager.write_file(dataset_id, upload_path, content)
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
        pid = (req.query_params.get("projectId") or "").strip()

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

    def api_builtin_templates(req: Request):
        """Return metadata and YAML content for all built-in spec templates."""
        templates = _load_builtin_templates()
        return Response(json.dumps(templates), media_type="application/json")

    rt("/api/built-in-templates")(api_builtin_templates)

    async def api_doc_content(req: Request):
        """Proxy the newest .docx from docs/ in the selected dataset snapshot.

        Query params: datasetId, snapshotId, projectId (optional).
        Returns the raw .docx bytes as application/octet-stream so the frontend
        can pass them to mammoth.js for inline HTML rendering.
        """
        from dataset_manager import DatasetManager

        snapshot_id = (req.query_params.get("snapshotId") or "").strip()
        if not snapshot_id:
            return Response("snapshotId required", status_code=400)

        try:
            files = DatasetManager.list_files(snapshot_id, "docs")
        except Exception as exc:
            logger.warning("api_doc_content: could not list docs/: %s", exc)
            return Response(f"Could not list docs/: {exc}", status_code=502)

        docx_files = [
            f for f in files
            if not f.get("isDirectory") and f.get("fileName", "").lower().endswith(".docx")
        ]
        if not docx_files:
            return Response("No .docx files found in docs/", status_code=404)

        # Sort by name desc — filenames embed timestamp (model_docs_YYYYMMDD_HHMMSS.docx)
        docx_files.sort(key=lambda f: f.get("fileName", ""), reverse=True)
        newest = docx_files[0]["fileName"]
        path = f"docs/{newest}"

        try:
            content = DatasetManager.read_file(snapshot_id, path)
        except Exception as exc:
            logger.warning("api_doc_content: could not read %s: %s", path, exc)
            return Response(f"Could not read {path}: {exc}", status_code=502)

        return Response(
            content,
            media_type="application/octet-stream",
            headers={"Content-Disposition": f'attachment; filename="{newest}"'},
        )

    rt("/api/doc-content")(api_doc_content)
