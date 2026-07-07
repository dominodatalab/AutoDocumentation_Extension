"""API routes: hardware tiers, datasets, etc."""

from __future__ import annotations

import json
import logging
from typing import Optional

from starlette.requests import Request
from starlette.responses import Response

from autodoc.core.models import DocumentSpec
from authorization import require_project_write
from dataset_manager import DatasetManager
import spec_template_sync

from .state import (
    _resolve_request_project_id,
    domino_client,
    domino_datasets,
)

logger = logging.getLogger(__name__)


def _autodoc_dataset_and_snapshot(project_id: str) -> tuple[dict, str]:
    logger.info("_autodoc_dataset_and_snapshot: start project_id=%r", project_id)
    require_project_write(project_id)
    ensured = domino_datasets.ensure_dataset(project_id)
    ds_id = str(ensured.get("id") or "").strip()
    logger.info(
        "_autodoc_dataset_and_snapshot: ensure_dataset returned id=%r name=%r rwSnapshotId=%r keys=%r",
        ds_id,
        (ensured.get("name") or "")[:80],
        ensured.get("rwSnapshotId"),
        sorted(ensured.keys()) if isinstance(ensured, dict) else type(ensured),
    )
    if not ds_id:
        raise RuntimeError("autodoc dataset has no id")
    snap = ensured.get("rwSnapshotId") or domino_datasets.get_rw_snapshot_id(ds_id)
    logger.info(
        "_autodoc_dataset_and_snapshot: resolved snapshot_id=%r (from ensured or get_rw_snapshot_id)",
        snap,
    )
    if not snap:
        raise RuntimeError("Could not resolve read-write snapshot for autodoc dataset")
    return ensured, str(snap)


def _active_autodoc_snapshot_for_spec_templates(project_id: str) -> str:
    import spec_template_sync

    logger.info("_active_autodoc_snapshot_for_spec_templates: start project_id=%r", project_id)
    ensured, initial_snap = _autodoc_dataset_and_snapshot(project_id)
    ds_id = str(ensured.get("id") or "").strip()
    logger.info(
        "_active_autodoc_snapshot_for_spec_templates: sync_builtins_to_autodoc_dataset dataset_id=%r",
        ds_id,
    )
    if not ds_id:
        raise RuntimeError("autodoc dataset has no id")
    spec_template_sync.sync_builtins_to_autodoc_dataset(ds_id, dest_snapshot_id=initial_snap)
    logger.info("_active_autodoc_snapshot_for_spec_templates: sync_builtins finished")
    fresh = domino_datasets.get_rw_snapshot_id(ds_id)
    logger.info(
        "_active_autodoc_snapshot_for_spec_templates: get_rw_snapshot_id returned %r (type=%s)",
        fresh,
        type(fresh).__name__,
    )
    if isinstance(fresh, str) and fresh.strip():
        logger.info(
            "_active_autodoc_snapshot_for_spec_templates: using fresh snapshot_id=%r",
            fresh.strip(),
        )
        return fresh.strip()
    snap = str(ensured.get("rwSnapshotId") or "").strip()
    logger.info(
        "_active_autodoc_snapshot_for_spec_templates: fallback ensured.rwSnapshotId=%r initial_snap=%r",
        snap,
        initial_snap,
    )
    if not snap:
        raise RuntimeError("Could not resolve read-write snapshot for autodoc dataset")
    return snap


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

    async def api_environments_default(req: Request):
        row = domino_client.get_default_environment()
        if not row:
            return Response(json.dumps({"id": "", "label": ""}), media_type="application/json")
        eid = str(row.get("id") or "")
        label = (row.get("name") or eid).strip()
        return Response(json.dumps({"id": eid, "label": label}), media_type="application/json")

    rt("/api/environments/default")(api_environments_default)

    async def api_environments(req: Request):
        rows = domino_client.list_self_environments() or []
        result = []
        for row in rows:
            eid = row.get("id", "")
            label = row.get("name") or eid
            result.append({"id": eid, "label": label})
        return Response(json.dumps(result), media_type="application/json")

    rt("/api/environments")(api_environments)

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

    def _governance_bundle_json(bundle) -> dict:
        return {
            "id": str(bundle.id),
            "name": bundle.name or "",
            "policyName": bundle.policy_name or "",
            "stage": bundle.stage or "",
            "state": bundle.state or "",
            "attachments": [
                {
                    "type": att.type,
                    "identifier": att.identifier if isinstance(att.identifier, dict) else {},
                }
                for att in (bundle.attachments or [])
            ],
        }

    async def api_governance_bundles(req: Request):
        pid = (_resolve_request_project_id(req) or "").strip()
        api_host = (req.query_params.get("apiHost") or "").strip()
        if not pid:
            return Response(
                json.dumps({"error": "projectId required", "bundles": []}),
                status_code=400,
                media_type="application/json",
            )
        if not api_host:
            return Response(
                json.dumps({"error": "apiHost required", "bundles": []}),
                status_code=400,
                media_type="application/json",
            )
        try:
            api_host = domino_client.normalize_governance_api_host(api_host)
        except ValueError as exc:
            return Response(
                json.dumps({"error": str(exc), "bundles": []}),
                status_code=400,
                media_type="application/json",
            )
        try:
            require_project_write(pid)
            bundles = domino_client.list_bundles(pid, api_host=api_host)
            payload = {"bundles": [_governance_bundle_json(b) for b in bundles]}
            return Response(json.dumps(payload), media_type="application/json")
        except Exception as exc:
            logger.exception("api_governance_bundles failed")
            return Response(
                json.dumps({"error": str(exc), "bundles": []}),
                status_code=500,
                media_type="application/json",
            )

    rt("/api/governance/bundles")(api_governance_bundles)

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

    async def api_code_root(req: Request):
        pid = _resolve_request_project_id(req)
        require_project_write(pid)
        try:
            info = domino_client.get_code_source_info(pid)
            return Response(
                json.dumps({"isGit": info["is_git"], "repoId": info["repo_id"], "location": info["location"]}),
                media_type="application/json",
            )
        except Exception as exc:
            return Response(json.dumps({"error": str(exc)}), status_code=500, media_type="application/json")

    rt("/api/code-root")(api_code_root)

    async def api_code_paths(req: Request):
        pid = _resolve_request_project_id(req)
        require_project_write(pid)
        try:
            result = domino_client.get_code_paths(pid)
            return Response(json.dumps(result), media_type="application/json")
        except Exception as exc:
            return Response(json.dumps({"error": str(exc)}), status_code=500, media_type="application/json")

    rt("/api/code-paths")(api_code_paths)

    async def api_code_files(req: Request):
        pid = _resolve_request_project_id(req)
        require_project_write(pid)
        is_git = req.query_params.get("isGit", "").lower() in ("true", "1")
        repo_id = req.query_params.get("repoId", "").strip()
        path = req.query_params.get("path", "").strip()
        try:
            if is_git:
                if not repo_id:
                    return Response(json.dumps({"error": "repoId required for git projects"}), status_code=400, media_type="application/json")
                files = domino_client.browse_gbp_code(pid, repo_id, path)
            else:
                proj = domino_client.resolve_project(pid)
                if not proj:
                    return Response(json.dumps({"error": "Could not resolve project"}), status_code=500, media_type="application/json")
                files = domino_client.browse_dfs_code(proj.owner_username, proj.name, path)
            return Response(json.dumps(files), media_type="application/json")
        except Exception as exc:
            return Response(json.dumps({"error": str(exc)}), status_code=500, media_type="application/json")

    rt("/api/code-files")(api_code_files)

    async def api_upload_spec_to_dataset(req: Request):
        """Save a spec template YAML into the project's autodoc dataset.

        Accepts multipart form with:
          - file: the YAML content (filename used as the destination basename)
          - filename (optional): override basename
        Destination dataset is the project's autodoc dataset (resolved via
        ensure_dataset). Destination path is spec_template_sync.dataset_rel_path(basename).
        """
        import spec_template_sync

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

        raw_filename = (
            str(form.get("filename", "") or "").strip()
            or getattr(file_upload, "filename", "")
            or "spec.yaml"
        )
        basename = raw_filename.rsplit("/", 1)[-1].rsplit("\\", 1)[-1] or "spec.yaml"
        content = await file_upload.read()

        fn_low = basename.lower()
        if not fn_low.endswith((".yaml", ".yml")):
            return Response(
                json.dumps({"error": "filename must end in .yaml or .yml"}),
                status_code=400,
                media_type="application/json",
            )

        try:
            content.decode("utf-8")
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

        try:
            spec_template_sync.validate_gallery_template_yaml(content)
        except ValueError as exc:
            msg = str(exc)
            missing_prefix = "Missing required field:"
            if missing_prefix in msg:
                fields = []
                for part in msg.split(";"):
                    part = part.strip()
                    if part.startswith(missing_prefix):
                        fields.append(part[len(missing_prefix):].strip())
                if fields:
                    return Response(
                        json.dumps({
                            "error": "Missing required field: " + ", ".join(fields),
                            "kind": "missing_fields",
                            "valid": False,
                        }),
                        status_code=400,
                        media_type="application/json",
                    )
            return Response(
                json.dumps({"error": msg, "valid": False}),
                status_code=400,
                media_type="application/json",
            )

        try:
            ensured = domino_datasets.ensure_dataset(pid)
            dataset_id = str(ensured.get("id") or "").strip()
            if not dataset_id:
                return Response(
                    json.dumps({"error": "autodoc dataset has no id"}),
                    status_code=500,
                    media_type="application/json",
                )
            dest_rel = spec_template_sync.dataset_rel_path(basename)
            DatasetManager.write_file(dataset_id, dest_rel, content)
            try:
                dest_snap = domino_datasets.get_rw_snapshot_id(dataset_id)
                spec_template_sync.sync_builtins_to_autodoc_dataset(
                    dataset_id,
                    dest_snapshot_id=dest_snap,
                )
            except Exception:
                logger.warning("sync built-ins after spec upload failed", exc_info=True)
            return Response(
                json.dumps({
                    "path": dest_rel,
                    "fileName": basename,
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

    async def api_add_spec_template(req: Request):
        """
        JSON-only: copy a YAML spec template from a source dataset into the
        destination "spec-templates" directory of the autodoc dataset.
        """
        pid = (_resolve_request_project_id(req) or "").strip()
        require_project_write(pid)

        try:
            payload = await req.json()
        except Exception:
            return Response(json.dumps({"error": "Invalid JSON"}), status_code=400, media_type="application/json")

        if not isinstance(payload, dict):
            return Response(json.dumps({"error": "Invalid JSON payload"}), status_code=400, media_type="application/json")

        source_type = str(payload.get("sourceType") or "dataset").strip()
        source_dataset_id = str(payload.get("sourceDatasetId") or "").strip()
        source_snapshot_id = str(payload.get("sourceSnapshotId") or "").strip()
        source_path = str(payload.get("sourcePath") or "").strip()
        source_repo_id = str(payload.get("sourceRepoId") or "").strip()
        filename = str(payload.get("filename") or "").strip() or source_path.rsplit("/", 1)[-1]

        if not source_path:
            return Response(json.dumps({"error": "sourcePath is required"}), status_code=400, media_type="application/json")
        if not filename:
            return Response(json.dumps({"error": "filename is required"}), status_code=400, media_type="application/json")

        if source_type == "dataset" and not source_dataset_id:
            return Response(json.dumps({"error": "sourceDatasetId is required"}), status_code=400, media_type="application/json")

        # Destination: autodoc dataset for this project.
        ensured = domino_datasets.ensure_dataset(pid)
        dest_dataset_id = str(ensured.get("id") or "").strip()
        if not dest_dataset_id:
            return Response(json.dumps({"error": "Destination autodoc dataset has no id"}), status_code=500, media_type="application/json")

        try:
            if source_type == "gbp_git":
                if not source_repo_id:
                    return Response(json.dumps({"error": "sourceRepoId is required for gbp_git"}), status_code=400, media_type="application/json")
                raw = domino_client.read_gbp_file_raw(pid, source_repo_id, source_path)
            elif source_type == "dfs_code":
                raw = domino_client.download_artifact_at_head(pid, source_path)
            else:
                if not source_snapshot_id:
                    source_snapshot_id = domino_datasets.get_rw_snapshot_id(source_dataset_id)
                if not source_snapshot_id:
                    return Response(
                        json.dumps({"error": "Could not resolve source snapshot for dataset"}),
                        status_code=400,
                        media_type="application/json",
                    )
                raw = DatasetManager.read_file(source_snapshot_id, source_path)
        except Exception as exc:
            return Response(json.dumps({"error": f"Could not read source template: {exc}"}), status_code=500, media_type="application/json")

        try:
            spec_template_sync.validate_gallery_template_yaml(raw)
        except ValueError as exc:
            msg = str(exc)
            missing_prefix = "Missing required field:"
            if missing_prefix in msg:
                fields = []
                for part in msg.split(";"):
                    part = part.strip()
                    if part.startswith(missing_prefix):
                        fields.append(part[len(missing_prefix):].strip())
                if fields:
                    friendly = "Missing required field: " + ", ".join(fields)
                    return Response(
                        json.dumps({"error": friendly, "kind": "missing_fields"}),
                        status_code=400,
                        media_type="application/json",
                    )
            return Response(
                json.dumps({"error": str(exc)}),
                status_code=400,
                media_type="application/json",
            )

        # Write into spec-templates/<filename> inside the autodoc dataset.
        dest_rel = spec_template_sync.dataset_rel_path(filename)
        try:
            DatasetManager.write_file(dest_dataset_id, dest_rel, raw)
        except Exception as exc:
            return Response(json.dumps({"error": f"Could not write template: {exc}"}), status_code=500, media_type="application/json")

        return Response(json.dumps({"ok": True}), media_type="application/json")

    rt("/api/add-spec-template")(api_add_spec_template)

    async def api_download_template(req: Request):
        import spec_template_sync

        pid = (_resolve_request_project_id(req) or "").strip()
        if not pid:
            return Response("projectId required", status_code=400)
        try:
            snap = _active_autodoc_snapshot_for_spec_templates(pid)
            rel = spec_template_sync.dataset_rel_path("doc_spec.yaml")
            logger.info("api_download_template: snapshot_id=%r path=%r", snap, rel)
            raw = DatasetManager.read_file(
                snap,
                rel,
            )
            logger.info("api_download_template: read %d bytes", len(raw or b""))
        except FileNotFoundError:
            return Response("Template not found", status_code=404)
        except Exception as exc:
            logger.warning("download-template read failed: %s", exc, exc_info=True)
            return Response(str(exc), status_code=500)
        return Response(
            content=raw,
            media_type="application/x-yaml",
            headers={"Content-Disposition": 'attachment; filename="doc_spec_template.yaml"'},
        )

    rt("/api/download-template")(api_download_template)


    async def api_built_in_templates(req: Request):
        import spec_template_sync

        pid = (_resolve_request_project_id(req) or "").strip()
        logger.info(
            "api_built_in_templates: request query_params=%r resolved_project_id=%r",
            dict(req.query_params),
            pid or None,
        )
        if not pid:
            logger.info("api_built_in_templates: no project id, returning empty catalog")
            return Response(json.dumps([]), media_type="application/json")
        try:
            ensured, snap = _autodoc_dataset_and_snapshot(pid)
            ds_id = str(ensured.get("id") or "").strip()
            if ds_id:
                spec_template_sync.sync_builtins_to_autodoc_dataset(
                    ds_id, dest_snapshot_id=snap
                )
                fresh = domino_datasets.get_rw_snapshot_id(ds_id)
                if isinstance(fresh, str) and fresh.strip():
                    snap = fresh.strip()
            mount_path = domino_datasets.resolve_dataset_mount_path(ensured)
            logger.info(
                "api_built_in_templates: catalog_from_dataset snapshot_id=%r mount_path=%r",
                snap,
                mount_path,
            )
        except Exception as exc:
            logger.exception("api_built_in_templates: failed before catalog project_id=%r", pid)
            return Response(
                json.dumps({"error": str(exc)}),
                status_code=500,
                media_type="application/json",
            )
        try:
            catalog = spec_template_sync.catalog_from_dataset(snap)
            out: list[dict] = []
            for c in catalog or []:
                tpl_file = str(c.get("template_file") or "").strip()
                rel = spec_template_sync.dataset_rel_path(tpl_file) if tpl_file else ""
                template_path = mount_path.rstrip("/") + ("/" + rel if rel else "")
                uid = template_path
                out.append({**c, "template_path": template_path, "uid": uid})
            logger.info(
                "api_built_in_templates: success entries=%d uids=%r",
                len(out),
                [c.get("uid") for c in out] if out else [],
            )
            return Response(json.dumps(out), media_type="application/json")
        except Exception:
            logger.exception("api_built_in_templates: catalog_from_dataset raised project_id=%r snap=%r", pid, snap)
            return Response(
                json.dumps({"error": "catalog failed"}),
                status_code=500,
                media_type="application/json",
            )

    rt("/api/built-in-templates")(api_built_in_templates)

    async def api_built_in_template_yaml(req: Request):
        import spec_template_sync

        pid = (_resolve_request_project_id(req) or "").strip()
        if not pid:
            return Response("projectId required", status_code=400)
        raw_param = (req.query_params.get("template_file") or "").strip()
        base = raw_param.replace("\\", "/").split("/")[-1]
        if not base:
            return Response("template_file required", status_code=400)
        if not base.lower().endswith((".yaml", ".yml")):
            return Response("Not found", status_code=404)
        try:
            logger.info(
                "api_built_in_template_yaml: project_id=%r template_file=%r base=%r",
                pid,
                raw_param,
                base,
            )
            snap = _active_autodoc_snapshot_for_spec_templates(pid)
            rel = spec_template_sync.dataset_rel_path(base)
            logger.info(
                "api_built_in_template_yaml: read_file snapshot_id=%r path=%r",
                snap,
                rel,
            )
            raw = DatasetManager.read_file(snap, rel)
            logger.info("api_built_in_template_yaml: read %d bytes", len(raw or b""))
        except Exception as exc:
            logger.warning("built-in-template read failed: %s", exc, exc_info=True)
            return Response(str(exc), status_code=500)
        return Response(content=raw, media_type="text/yaml; charset=utf-8")

    rt("/api/built-in-template")(api_built_in_template_yaml)

    async def api_built_in_template_sections(req: Request):
        import spec_template_sync
        import yaml

        pid = (_resolve_request_project_id(req) or "").strip()
        if not pid:
            return Response("projectId required", status_code=400)
        raw_param = (req.query_params.get("template_file") or "").strip()
        base = raw_param.replace("\\", "/").split("/")[-1]
        if not base:
            return Response("template_file required", status_code=400)
        if not base.lower().endswith((".yaml", ".yml")):
            return Response("Not found", status_code=404)
        try:
            snap = _active_autodoc_snapshot_for_spec_templates(pid)
            rel = spec_template_sync.dataset_rel_path(base)
            raw = DatasetManager.read_file(snap, rel)
        except Exception as exc:
            logger.warning("built-in-template-sections read failed: %s", exc, exc_info=True)
            return Response(str(exc), status_code=500)
        text = (raw or b"").decode("utf-8", errors="replace").lstrip("\ufeff")
        try:
            parsed = yaml.safe_load(text)
        except yaml.YAMLError:
            parsed = None
        sections: list[str] = []
        per_model: list[str] = []

        def _split_per_model(name: str) -> str:
            if ":" in name:
                head, _, tail = name.rpartition(":")
                if tail.strip().lower() == "per_model":
                    cleaned = head.strip()
                    if cleaned:
                        per_model.append(cleaned)
                        return cleaned
            return name

        if isinstance(parsed, dict):
            raw_sections = parsed.get("sections")
            if isinstance(raw_sections, list):
                for entry in raw_sections:
                    if isinstance(entry, str):
                        sections.append(_split_per_model(entry))
                    elif isinstance(entry, dict):
                        title = entry.get("title") or entry.get("name") or entry.get("id")
                        if isinstance(title, str) and title.strip():
                            sections.append(_split_per_model(title.strip()))
            elif isinstance(raw_sections, dict):
                for key in raw_sections.keys():
                    if isinstance(key, str):
                        sections.append(_split_per_model(key))
            raw_per_model = parsed.get("per_model_sections")
            if isinstance(raw_per_model, list):
                for entry in raw_per_model:
                    if isinstance(entry, str) and entry not in per_model:
                        per_model.append(entry)
        payload = {"sections": sections, "per_model_sections": per_model}
        return Response(json.dumps(payload), media_type="application/json")

    rt("/api/built-in-template-sections")(api_built_in_template_sections)

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
            spec_template_sync.sync_builtins_to_autodoc_dataset(ds_id, dest_snapshot_id=_snap)
            return Response(json.dumps({"ok": True}), media_type="application/json")
        except Exception as exc:
            logger.exception("sync-spec-templates failed")
            return Response(
                json.dumps({"error": str(exc)}),
                status_code=500,
                media_type="application/json",
            )

    rt("/api/sync-spec-templates")(api_sync_spec_templates)

    async def api_preview_doc(req: Request):
        pid = _resolve_request_project_id(req)
        if not pid:
            return Response(json.dumps({"error": "Project ID is required."}), status_code=400, media_type="application/json")
        run_id = (req.query_params.get("runId") or "").strip()
        if not run_id:
            return Response(json.dumps({"error": "runId is required."}), status_code=400, media_type="application/json")
        try:
            require_project_write(pid)
            short = run_id[:8]
            artifact_path = f"docs/{short}/model_docs.docx"
            docx_bytes = domino_client.download_artifact_at_head(pid, artifact_path)
            if docx_bytes is None:
                return Response(json.dumps({"error": "Document not found.", "ready": False}), status_code=404, media_type="application/json")
            import mammoth
            import io
            result = mammoth.convert_to_html(io.BytesIO(docx_bytes))
            return Response(
                json.dumps({"html": result.value, "ready": True}),
                media_type="application/json",
            )
        except Exception as exc:
            logger.warning("api_preview_doc failed", exc_info=True)
            return Response(json.dumps({"error": str(exc)}), status_code=500, media_type="application/json")

    rt("/api/preview-doc")(api_preview_doc)
