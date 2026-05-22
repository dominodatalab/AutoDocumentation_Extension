"""Integration tests -- real HTTP requests through Starlette routes.

Tests the full request -> route handler -> response path with:
- Real HTTP via httpx AsyncClient + Starlette app
- Monkeypatched DatasetManager (in-memory) for spec_store and other dataset I/O
- Real auth_context ContextVar propagation through middleware
- Mocked Domino API client (no live API calls)

These tests build a lightweight Starlette app that wires the same route
handlers and middleware as web_app_studio.py, without requiring FastHTML
(which needs Python 3.10+).
"""

from __future__ import annotations

import importlib.util
import json
import os
import sys
from pathlib import Path
from types import ModuleType
from unittest.mock import MagicMock

import httpx
import pytest
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.routing import Route
from starlette.testclient import TestClient

# Ensure auto_model_docs is importable
_repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_pkg_dir = os.path.join(_repo_root, "auto_model_docs")
for p in (_repo_root, _pkg_dir):
    if p not in sys.path:
        sys.path.insert(0, p)


# ---------------------------------------------------------------------------
# Module loader
# ---------------------------------------------------------------------------

def _load_module(name: str, filename: str) -> ModuleType:
    path = os.path.join(_pkg_dir, "studio", filename)
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


# ---------------------------------------------------------------------------
# Build test app
# ---------------------------------------------------------------------------

def _build_test_app(tmp_path: Path, monkeypatch):
    """Construct a Starlette app wired with real route handlers.

    Uses in-memory DatasetManager mock for spec_store (and paths that read specs),
    mocked domino_client, and real auth_context propagation.
    """
    import domino_job_store as store
    import spec_store
    import auth_context
    import dataset_manager
    import artifact_layout

    _mem_files: dict[str, bytes] = {}
    _mem_files["spec.yaml"] = b"title: Test\n"
    _mem_files["spec-templates/doc_spec.yaml"] = (
        b"slug: standard_ml\n"
        b"card_title: Standard ML Model Doc\n"
        b"card_description: DownloadFromDataset\n"
        b"sections:\n"
        b"  - Executive Summary\n"
    )

    def _mem_write(dataset_id, path, content):
        _mem_files[path] = content

    def _mem_read(snapshot_id, path):
        if path not in _mem_files:
            raise FileNotFoundError(path)
        return _mem_files[path]

    def _mem_list(snapshot_id, path=""):
        prefix = (path.rstrip("/") + "/") if path else ""
        results = []
        for k in _mem_files:
            if prefix and not k.startswith(prefix):
                continue
            name = k[len(prefix):] if prefix else k
            if "/" in name:
                continue
            results.append({
                "fileName": name,
                "isDirectory": False,
                "sizeInBytes": len(_mem_files[k]),
            })
        return results

    def _mem_exists(snapshot_id, path):
        return path in _mem_files

    def _mem_meta(snapshot_id, path):
        if path not in _mem_files:
            raise FileNotFoundError(path)
        return {"sizeInBytes": len(_mem_files[path])}

    monkeypatch.setattr(dataset_manager.DatasetManager, "write_file", staticmethod(_mem_write))
    monkeypatch.setattr(dataset_manager.DatasetManager, "read_file", staticmethod(_mem_read))
    monkeypatch.setattr(dataset_manager.DatasetManager, "list_files", staticmethod(_mem_list))
    monkeypatch.setattr(dataset_manager.DatasetManager, "file_exists", staticmethod(_mem_exists))
    monkeypatch.setattr(dataset_manager.DatasetManager, "read_file_meta", staticmethod(_mem_meta))

    artifact_layout.init_layout()

    # Mock domino_client
    mock_client = MagicMock()
    mock_client.list_hardware_tiers.return_value = [
        {"id": "small", "name": "Small", "isDefault": True},
    ]
    mock_client.get_project_default_tier.return_value = "small"
    mock_client.submit_job.return_value = "run-integration"
    mock_client.build_job_url.return_value = "https://domino.test/jobs/run-integration"
    mock_client.get_job_status.return_value = {
        "domino_status": "Succeeded", "local_status": "succeeded",
    }
    monkeypatch.setenv("DOMINO_ENVIRONMENT_ID", "env-integration")
    monkeypatch.setenv("DOMINO_ENVIRONMENT_REVISION_ID", "rev-integration")
    mock_client.list_environment_revisions.return_value = [
        {"id": "rev-integration", "number": 1, "option_label": "#1"},
    ]
    mock_info = MagicMock()
    mock_info.name = "test-project"
    mock_info.owner_username = "test-owner"
    mock_info.main_repo_id = "repo-123"
    mock_client.resolve_project.return_value = mock_info
    mock_client.get_project_code_root.return_value = "/mnt/code"
    mock_client.set_ui_host = MagicMock()
    import domino_client as real_dc

    monkeypatch.setattr(
        real_dc,
        "build_autodoc_dataset_data_page_url",
        lambda pid, did: f"https://domino.test/u/test-owner/test-project/data/rw/upload/autodoc/{did}/docs",
    )
    mock_client.list_self_environments.return_value = []
    mock_client.list_environment_revisions.return_value = []

    mock_datasets = MagicMock()
    mock_datasets.list_datasets.return_value = [
        {"id": "ds-1", "name": "autodoc-specs", "rwSnapshotId": "snap-1", "datasetPath": "/domino/datasets/local/autodoc"},
        {
            "id": "ds-autodoc-uuid",
            "name": "autodoc",
            "rwSnapshotId": "snap-autodoc",
            "datasetPath": "/domino/datasets/local/autodoc",
        },
    ]
    mock_datasets.ensure_dataset = MagicMock(
        return_value={"id": "ds-1", "name": "autodoc-specs", "datasetPath": "/domino/datasets/local/autodoc"},
    )
    mock_datasets.get_existing_autodoc_dataset = MagicMock(
        return_value={
            "id": "ds-autodoc-uuid",
            "name": "autodoc",
            "rwSnapshotId": "snap-autodoc",
            "datasetPath": "/domino/datasets/local/autodoc",
        },
    )
    mock_datasets.resolve_dataset_mount_path = MagicMock(
        side_effect=lambda e: (e.get("datasetPath") or "").strip() or "/domino/datasets/local/autodoc",
    )
    mock_datasets.AUTODOC_SPECS_DATASET = "autodoc-specs"
    mock_datasets.build_spec_mount_path.return_value = "/mnt/data/autodoc-specs/spec.yaml"
    mock_datasets.get_rw_snapshot_id.return_value = "snap-1"
    mock_datasets.get_dataset_detail.return_value = {"datasetPath": "/domino/datasets/local/autodoc"}
    mock_datasets.list_files.return_value = []

    # Set up studio.state
    studio_pkg = ModuleType("studio")
    studio_pkg.__path__ = [os.path.join(_pkg_dir, "studio")]
    studio_pkg.__package__ = "studio"
    sys.modules["studio"] = studio_pkg

    mock_state = ModuleType("studio.state")
    mock_state.domino_client = mock_client
    mock_state.domino_job_store = store
    mock_state.spec_store = spec_store
    mock_state.domino_datasets = mock_datasets
    mock_state.auth_context = auth_context
    mock_state._max_jobs = lambda: 2
    mock_state._resolve_request_project_id = lambda req: "proj-integration"
    mock_state._resolve_request_dataset_ids = lambda req: ("ds-integration", "snap-integration")
    mock_state._get_default_code_root = lambda: Path("/mnt/code")
    mock_state.logger = MagicMock()

    from dataclasses import dataclass
    from typing import Optional

    @dataclass
    class JobRequest:
        spec_path: str = ""
        provider: str = "anthropic"
        model: str = ""
        api_key: Optional[str] = None
        base_url: Optional[str] = None
        code_root: str = ""
        max_files: int = 50
        workers: int = 4
        planning_workers: int = 4
        timeout: float = 120.0
        notebook: bool = False
        notebook_path: str = ""
        filtered_experiment_names: str = ""
        filtered_model_names: str = ""
        latest_only: bool = False
        verbose: bool = True
        hardware_tier: str = ""
        environment_id: str = ""
        environment_revision_id: str = ""
        api_key_source: str = "domino_env"
        project_id: str = ""
        provider_base_url: str = ""
        max_retries: int = 5
        initial_backoff: float = 10.0
        max_backoff: float = 120.0
        backoff_jitter: float = 0.2
        notebook_from_cache: bool = False

    @dataclass
    class DominoJobRecord:
        id: str
        owner_id: str
        domino_run_id: Optional[str] = None
        hardware_tier: Optional[str] = None
        status: str = "queued"
        domino_status: Optional[str] = None
        job_url: Optional[str] = None
        dataset_id: Optional[str] = None
        spec_path: Optional[str] = None
        submitted_at: Optional[str] = None
        completed_at: Optional[str] = None
        error: Optional[str] = None
        project_id: Optional[str] = None

    @dataclass
    class EnvironmentWarning:
        level: str
        message: str
        action: str

    mock_state.JobRequest = JobRequest
    mock_state.DominoJobRecord = DominoJobRecord
    mock_state.EnvironmentWarning = EnvironmentWarning

    sys.modules["studio.state"] = mock_state

    # Mock fasthtml.common — provide FT component stubs that return plain HTML strings
    mock_fh = ModuleType("fasthtml.common")

    def _make_ft(tag_name):
        def ft_fn(*children, **attrs):
            parts = [f"<{tag_name}"]
            for k, v in attrs.items():
                if k.startswith("hx_") or k.startswith("data_"):
                    k = k.replace("_", "-")
                if k == "cls":
                    k = "class"
                if k == "for_":
                    k = "for"
                if v is True:
                    parts.append(f" {k}")
                elif v is not False and v is not None:
                    parts.append(f' {k}="{v}"')
            parts.append(">")
            for child in children:
                if child is None:
                    continue
                parts.append(str(child))
            parts.append(f"</{tag_name}>")
            return "".join(parts)
        return ft_fn

    for tag in ("Div", "P", "A", "Span", "H2", "H3", "Select", "Option", "Input",
                "Label", "Table", "Thead", "Tbody", "Tr", "Th", "Td", "Ul", "Li",
                "Pre", "Button", "Details", "Summary", "Code"):
        setattr(mock_fh, tag, _make_ft(tag.lower()))

    class FT:
        pass
    mock_fh.FT = FT

    sys.modules["fasthtml"] = ModuleType("fasthtml")
    sys.modules["fasthtml.common"] = mock_fh

    # Mock autodoc.core.models (routes_api upload validation, etc.)
    mock_models = ModuleType("autodoc.core.models")
    mock_doc_spec = MagicMock()
    mock_doc_spec.validate_spec.return_value = []
    mock_models.DocumentSpec = mock_doc_spec
    mock_models.LANGUAGE_PROFILES = {}
    sys.modules["autodoc"] = ModuleType("autodoc")
    sys.modules["autodoc.core"] = ModuleType("autodoc.core")
    sys.modules["autodoc.core.models"] = mock_models

    # Mock authorization module — default to "allow everything" so integration
    # tests exercise route bodies. Tests that want to exercise deny behaviour
    # can override the require_* attributes on this mock post-build.
    mock_authz = ModuleType("authorization")
    mock_authz.require_domino_job_start = MagicMock()
    mock_authz.require_domino_job_stop = MagicMock()
    mock_authz.require_domino_job_list = MagicMock()
    mock_authz.require_project_write = MagicMock()
    sys.modules["authorization"] = mock_authz

    # Load route modules fresh
    for mod_name in ("studio.ui_components", "studio.job_engine",
                     "studio.routes_api", "studio.routes_job"):
        sys.modules.pop(mod_name, None)

    ui_mod = _load_module("studio.ui_components", "ui_components.py")
    je_mod = _load_module("studio.job_engine", "job_engine.py")
    api_mod = _load_module("studio.routes_api", "routes_api.py")
    job_mod = _load_module("studio.routes_job", "routes_job.py")

    # Collect route handlers
    handlers = {}

    def fake_rt(path):
        def decorator(fn):
            handlers[path] = fn
            return fn
        return decorator

    api_mod.register_api_routes(fake_rt)
    job_mod.register_job_routes(fake_rt)

    # Build Starlette routes from collected handlers
    import asyncio
    import inspect

    def _wrap(handler):
        """Wrap a route handler into a proper Starlette endpoint."""
        sig = inspect.signature(handler)
        params = list(sig.parameters.keys())

        def _call_sync(handler_fn, request):
            if not params:
                return handler_fn()
            try:
                bound = sig.bind(request)
            except TypeError:
                bound = sig.bind(request, **getattr(request, "path_params", {}))
            return handler_fn(*bound.args, **bound.kwargs)

        if inspect.iscoroutinefunction(handler):
            async def endpoint(request):
                if not params:
                    result = await handler()
                else:
                    try:
                        bound = sig.bind(request)
                    except TypeError:
                        bound = sig.bind(request, **getattr(request, "path_params", {}))
                    result = await handler(*bound.args, **bound.kwargs)
                if isinstance(result, Response):
                    return result
                return Response(str(result), media_type="text/html")
            return endpoint
        else:
            async def endpoint(request):
                result = _call_sync(handler, request)
                if isinstance(result, Response):
                    return result
                return Response(str(result), media_type="text/html")
            return endpoint

    routes = []
    for path, handler in handlers.items():
        # Starlette Route supports both GET and POST
        routes.append(Route(path, _wrap(handler), methods=["GET", "POST"]))

    app = Starlette(routes=routes)

    # Add auth middleware
    from starlette.middleware import Middleware
    from starlette.middleware.base import BaseHTTPMiddleware

    class AuthMiddleware(BaseHTTPMiddleware):
        async def dispatch(self, request, call_next):
            forwarded = request.headers.get("authorization")
            auth_context.set_request_auth_header(forwarded)
            try:
                response = await call_next(request)
            finally:
                auth_context.set_request_auth_header(None)
            return response

    app.add_middleware(AuthMiddleware)

    return {
        "app": app,
        "store": store,
        "spec_store": spec_store,
        "domino_client": mock_client,
        "domino_datasets": mock_datasets,
        "auth_context": auth_context,
        "doc_spec": mock_doc_spec,
        "authz": mock_authz,
        "_restore": None,
    }


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def integration_env(tmp_path, monkeypatch):
    """Provide a wired test app with real HTTP transport."""
    monkeypatch.setenv("DOMINO_API_HOST", "https://domino.test")
    monkeypatch.setenv("DOMINO_USER_API_KEY", "test-key")
    monkeypatch.setenv("AUTODOC_MAX_JOBS", "2")
    monkeypatch.setenv("DOMINO_DATASETS_DIR", str(tmp_path / "domino_datasets"))
    monkeypatch.setenv("DOMINO_PROJECT_NAME", "autodoc-extension")

    import auth_context as _auth_ctx
    from auth_context import User
    monkeypatch.setattr(
        _auth_ctx, "get_viewing_user",
        lambda: User(id="integration_user", user_name="integration_user"),
    )

    saved_modules = {}
    for key in ("studio", "studio.state", "studio.ui_components", "studio.job_engine",
                "studio.routes_api", "studio.routes_job",
                "fasthtml", "fasthtml.common", "autodoc", "autodoc.core", "autodoc.core.models"):
        saved_modules[key] = sys.modules.get(key)

    env = _build_test_app(tmp_path, monkeypatch)

    yield env

    import artifact_layout
    artifact_layout.reset_layout()

    for key, val in saved_modules.items():
        if val is None:
            sys.modules.pop(key, None)
        else:
            sys.modules[key] = val


@pytest.fixture
def client(integration_env):
    """Provide a synchronous Starlette TestClient."""
    return TestClient(integration_env["app"])


# ===========================================================================
# API route integration tests
# ===========================================================================

class TestApiRoutesIntegration:

    def test_datasets_endpoint(self, client, integration_env):
        resp = client.get("/api/datasets?projectId=proj-integration")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert len(data) == 2
        names = {d["name"] for d in data}
        assert "autodoc-specs" in names
        assert "autodoc" in names

    def test_datasets_error_returns_500(self, client, integration_env):
        integration_env["domino_datasets"].list_datasets.side_effect = RuntimeError("API down")
        resp = client.get("/api/datasets?projectId=proj-integration")
        assert resp.status_code == 500
        assert "error" in resp.json()
        integration_env["domino_datasets"].list_datasets.side_effect = None
        integration_env["domino_datasets"].list_datasets.return_value = [
            {"id": "ds-1", "name": "autodoc-specs", "rwSnapshotId": "snap-1", "datasetPath": "/domino/datasets/local/autodoc"},
            {
                "id": "ds-autodoc-uuid",
                "name": "autodoc",
                "rwSnapshotId": "snap-autodoc",
                "datasetPath": "/domino/datasets/local/autodoc",
            },
        ]

    def test_dataset_files_requires_dataset_id(self, client):
        resp = client.get("/api/dataset-files")
        assert resp.status_code == 400

    def test_dataset_files_with_id(self, client, integration_env):
        integration_env["domino_datasets"].list_files.return_value = [
            {"fileName": "spec.yaml", "isDirectory": False},
        ]
        resp = client.get("/api/dataset-files?datasetId=ds-1&projectId=proj-integration")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["fileName"] == "spec.yaml"

    def test_download_template(self, client):
        resp = client.get("/api/download-template?projectId=proj-integration")
        assert resp.status_code == 200
        assert b"slug: standard_ml" in resp.content

    def test_hardware_tiers(self, client):
        resp = client.get("/api/hardware-tiers?projectId=proj-integration")
        assert resp.status_code == 200


# ===========================================================================
# Spec upload validation (via /api/upload-spec-to-dataset)
# ===========================================================================

class TestSpecUploadIntegration:

    def test_upload_invalid_yaml_returns_400(self, client, integration_env, monkeypatch):
        # YAML missing required gallery fields (slug, card_title, card_description, sections).
        mock_write = MagicMock()
        monkeypatch.setattr(
            "dataset_manager.DatasetManager.write_file",
            staticmethod(mock_write),
        )
        resp = client.post(
            "/api/upload-spec-to-dataset?projectId=proj-integration",
            files={"file": ("spec.yaml", b"foo: bar\n", "application/x-yaml")},
        )
        assert resp.status_code == 400
        body = resp.json()
        assert body.get("valid") is False
        assert "Missing required field" in body.get("error", "")
        mock_write.assert_not_called()


# ===========================================================================
# Job route integration tests
# ===========================================================================

class TestJobRoutesIntegration:

    def test_job_history_empty(self, client):
        resp = client.get("/job-history?projectId=proj-integration")
        assert resp.status_code == 200
        body = resp.json()
        assert body.get("jobs") == []
        assert "document_url" not in body

    def test_submit_job_calls_domino(self, client, integration_env):
        """POST /run submits to Domino and records the run for the current user."""
        store = integration_env["store"]
        mock_client = integration_env["domino_client"]

        resp = client.post(
            "/run?projectId=proj-integration",
            json={
                "spec_path": "/domino/datasets/local/autodoc/spec.yaml",
                "provider": "anthropic",
                "model": "claude-sonnet-4-20250514",
                "code_root": "/mnt/code",
                "hardware_tier": "small",
                "environment_id": "env-int",
                "environment_revision_id": "rev-int",
            },
        )
        assert resp.status_code == 200
        assert resp.json().get("ok") is True
        integration_env["domino_datasets"].get_existing_autodoc_dataset.assert_called_with("proj-integration")
        integration_env["domino_datasets"].resolve_dataset_mount_path.assert_called_once()
        mock_client.submit_job.assert_called()
        jobs = store.get_user_jobs("proj-integration", "integration_user", limit=50)
        assert len(jobs) == 1
        assert jobs[0]["domino_run_id"] == "run-integration"

    def test_cancel_queued_jobs(self, client):
        resp = client.post("/cancel-queued-jobs?projectId=proj-integration")
        assert resp.status_code == 200
        body = resp.json()
        assert body.get("ok") is True
        assert body.get("jobs") == []
        assert "document_url" not in body


# ===========================================================================
# Auth context middleware integration
# ===========================================================================

class TestAuthorizationIntegration:
    """End-to-end: authz deny should return 403 from sensitive routes."""

    @staticmethod
    def _deny(authz, attr):
        from starlette.exceptions import HTTPException
        getattr(authz, attr).side_effect = HTTPException(status_code=403, detail="denied")

    def test_run_denied_returns_403(self, client, integration_env):
        self._deny(integration_env["authz"], "require_domino_job_start")
        resp = client.post(
            "/run?projectId=proj-integration",
            json={
                "spec_path": "/domino/datasets/local/autodoc/spec.yaml",
                "provider": "anthropic",
                "model": "claude-sonnet-4-20250514",
                "code_root": "/mnt/code",
                "hardware_tier": "small",
                "environment_id": "env-int",
                "environment_revision_id": "rev-int",
            },
        )
        assert resp.status_code == 403
        assert resp.json().get("error")
        integration_env["domino_datasets"].get_existing_autodoc_dataset.assert_called_with("proj-integration")

    def test_job_history_denied_returns_403(self, client, integration_env):
        self._deny(integration_env["authz"], "require_domino_job_list")
        resp = client.get("/job-history?projectId=proj-integration")
        assert resp.status_code == 403

    def test_cancel_queued_denied_returns_403(self, client, integration_env):
        self._deny(integration_env["authz"], "require_domino_job_list")
        resp = client.post("/cancel-queued-jobs?projectId=proj-integration")
        assert resp.status_code == 403

    def test_datasets_denied_returns_403(self, client, integration_env):
        self._deny(integration_env["authz"], "require_project_write")
        resp = client.get("/api/datasets?projectId=proj-integration")
        assert resp.status_code == 403

    def test_upload_spec_denied_returns_403(self, client, integration_env):
        self._deny(integration_env["authz"], "require_project_write")
        resp = client.post(
            "/api/upload-spec-to-dataset?projectId=proj-integration",
            files={"file": ("spec.yaml", b"title: Test\n", "application/x-yaml")},
        )
        assert resp.status_code == 403



class TestAuthMiddlewareIntegration:

    def test_jwt_cleared_after_request(self, client, integration_env):
        """Auth middleware should clear the JWT after each request."""
        ac = integration_env["auth_context"]
        assert ac.get_request_auth_header() is None

        client.get(
            "/api/datasets?projectId=proj-integration",
            headers={"Authorization": "Bearer integration-jwt"},
        )

        # After request completes, JWT should be cleared
        assert ac.get_request_auth_header() is None

    def test_requests_without_auth_succeed(self, client):
        resp = client.get("/api/hardware-tiers?projectId=proj-integration")
        assert resp.status_code == 200


# ===========================================================================
# Cross-cutting integration
# ===========================================================================

class TestCrossCuttingIntegration:

    def test_run_always_submits_to_domino(self, client, integration_env):
        """POST /run always calls Domino submit; no local queue on the /run path."""
        mock_client = integration_env["domino_client"]
        before = mock_client.submit_job.call_count
        resp = client.post(
            "/run?projectId=proj-integration",
            json={
                "spec_path": "/domino/datasets/local/autodoc/spec.yaml",
                "provider": "anthropic",
                "model": "claude-sonnet-4-20250514",
                "code_root": "/mnt/code",
                "hardware_tier": "small",
                "environment_id": "env-int",
                "environment_revision_id": "rev-int",
                "max_files": 50,
                "workers": 4,
                "planning_workers": 3,
                "timeout": 120,
                "max_retries": 5,
                "initial_backoff": 10,
                "max_backoff": 120,
                "backoff_jitter": 0.2,
                "verbose": True,
            },
        )
        assert resp.status_code == 200
        assert resp.json().get("ok") is True
        assert mock_client.submit_job.call_count == before + 1

    def test_cancel_then_history_empty_without_storage(self, client):
        client.post("/cancel-queued-jobs?projectId=proj-integration")
        resp = client.get("/job-history?projectId=proj-integration")
        assert resp.status_code == 200
        body = resp.json()
        assert body.get("jobs") == []
        assert "document_url" not in body
