"""Spec-related routes: validate, save, list."""

from __future__ import annotations

import json

from starlette.requests import Request
from starlette.responses import Response

from autodoc.core.models import DocumentSpec
from authorization import require_project_write

from .state import _resolve_request_project_id, _resolve_request_dataset_ids, spec_store


def _json(data, status_code: int = 200) -> Response:
    return Response(json.dumps(data), status_code=status_code, media_type="application/json")


def register_spec_routes(rt):
    """Register all spec-related routes on the given rt decorator."""

    async def validate_spec_route(req: Request):
        try:
            body = await req.json()
            content = body.get("spec_content") if isinstance(body, dict) else None
        except Exception:
            content = None

        if not content or not content.strip():
            return _json({"valid": False, "errors": ["No spec content provided"]})

        errors = DocumentSpec.validate_spec(content)
        return _json({"valid": not errors, "errors": errors or []})

    rt("/validate-spec")(validate_spec_route)

    async def spec_list(req: Request):
        pid = _resolve_request_project_id(req)
        require_project_write(pid)
        ds_id, snap_id = _resolve_request_dataset_ids(req)
        if not snap_id:
            return _json({"specs": []})
        specs = spec_store.list_specs(snap_id)
        return _json({"specs": specs or []})

    rt("/spec-list")(spec_list)
