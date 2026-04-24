"""Spec-related routes: validate, save, list."""

from __future__ import annotations

from fasthtml.common import *
from starlette.requests import Request
from starlette.responses import Response

from autodoc.core.models import DocumentSpec
from authorization import require_project_write

from .state import _resolve_request_project_id, _resolve_request_dataset_ids, spec_store


def register_spec_routes(rt):
    """Register all spec-related routes on the given rt decorator."""

    async def validate_spec_route(req: Request):
        form = await req.form()
        spec_upload = form.get("spec_upload")
        content = None
        if spec_upload and hasattr(spec_upload, "read"):
            raw = await spec_upload.read()
            content = raw.decode("utf-8", errors="replace")
        else:
            content = form.get("spec_content")

        if not content or not content.strip():
            return Div(
                Span("No spec content to validate.", cls="spec-validation-empty"),
                id="spec-validation-result",
            )

        errors = DocumentSpec.validate_spec(content)
        if errors:
            error_items = [Li(e) for e in errors]
            return Div(
                Div(
                    Span("Spec validation failed", cls="spec-selected-value"),
                    Ul(*error_items, cls="spec-validation-error-list"),
                    cls="spec-validation-error",
                ),
                id="spec-validation-result",
            )

        return Div(
            Span("Spec is valid", cls="spec-validation-success"),
            id="spec-validation-result",
        )

    rt("/validate-spec")(validate_spec_route)

    async def save_spec_route(req: Request):
        pid = _resolve_request_project_id(req)
        require_project_write(pid)
        ds_id, snap_id = _resolve_request_dataset_ids(req)
        if not ds_id:
            return Response("datasetId required", status_code=400)
        form = await req.form()
        filename = form.get("spec_filename", "spec.yaml")
        content = form.get("spec_content", "")
        saved = spec_store.save_spec(ds_id, filename, content)
        return Response(str(saved), media_type="text/plain")

    rt("/save-spec")(save_spec_route)

    async def spec_list(req: Request):
        pid = _resolve_request_project_id(req)
        require_project_write(pid)
        ds_id, snap_id = _resolve_request_dataset_ids(req)
        if not snap_id:
            return Div(P("No dataset selected.", cls="history-empty"), id="spec-list-content")
        specs = spec_store.list_specs(snap_id)
        if not specs:
            return Div(P("No saved spec files.", cls="history-empty"), id="spec-list-content")
        items = []
        for s in specs:
            items.append(
                Div(
                    Span(s["name"], style="font-family: monospace;"),
                    Span(f"{s['size_kb']} KB", style="color: var(--outline); margin: 0 0.75rem;"),
                    cls="spec-list-item",
                )
            )
        return Div(*items, id="spec-list-content", cls="spec-list-modal")

    rt("/spec-list")(spec_list)
