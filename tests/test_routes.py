"""Tests for studio route handlers — routes_api.py, routes_job.py."""

from __future__ import annotations

import importlib.util
import json
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from types import ModuleType
from typing import Optional
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Ensure auto_model_docs is importable
_repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_pkg_dir = os.path.join(_repo_root, "auto_model_docs")
for p in (_repo_root, _pkg_dir):
    if p not in sys.path:
        sys.path.insert(0, p)


# ---------------------------------------------------------------------------
# Shared test types
# ---------------------------------------------------------------------------

@dataclass
class _MockJobRequest:
    spec_path: str = ""
    provider: str = "anthropic"
    model: str = "gpt-4"
    api_key: Optional[str] = None
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
class _MockDominoJobRecord:
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


# ---------------------------------------------------------------------------
# Import helper
# ---------------------------------------------------------------------------

def _load_module(name: str, path: str) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _drop_viewer(monkeypatch):
    """Override the autouse viewer stub so get_viewing_user() raises."""
    import auth_context
    def _raise():
        raise RuntimeError("no forwarded token")
    monkeypatch.setattr(auth_context, "get_viewing_user", _raise)


@pytest.fixture(autouse=True)
def _mock_studio_modules(monkeypatch):
    """Set up mock studio modules for route imports."""
    import auth_context
    from auth_context import User
    monkeypatch.setattr(
        auth_context, "get_viewing_user",
        lambda: User(id="test_user", user_name="test_user"),
    )
    mock_state = ModuleType("studio.state")
    mock_state._max_jobs = MagicMock(return_value=1)
    mock_state._resolve_request_project_id = MagicMock(return_value="proj-123")
    mock_state._resolve_request_dataset_ids = MagicMock(return_value=("ds-test", "snap-test"))
    mock_state._get_default_code_root = MagicMock(return_value=Path("/mnt/code"))
    mock_state.logger = MagicMock()
    mock_state.JobRequest = _MockJobRequest
    mock_state.DominoJobRecord = _MockDominoJobRecord
    mock_state.domino_client = MagicMock()
    import domino_client as _dc
    mock_state.domino_client.get_project_code_root = (
        _dc.get_project_code_root
    )
    mock_state.domino_job_store = MagicMock()
    mock_state.spec_store = MagicMock()
    mock_state.domino_datasets = MagicMock()
    mock_state.domino_datasets.get_dataset_detail.return_value = {"datasetPath": "/domino/datasets/local/autodoc"}
    mock_state.domino_datasets.ensure_dataset.return_value = {
        "id": "ds-test",
        "name": "autodoc",
        "datasetPath": "/domino/datasets/local/autodoc",
        "rwSnapshotId": "snap-test",
    }
    mock_state.domino_datasets.get_existing_autodoc_dataset.return_value = {
        "id": "ds-test",
        "name": "autodoc",
        "datasetPath": "/domino/datasets/local/autodoc",
        "rwSnapshotId": "snap-test",
    }

    def _noop_sync_builtins(_dataset_id: str, *args, **kwargs) -> None:
        return None

    monkeypatch.setattr(
        "spec_template_sync.sync_builtins_to_autodoc_dataset",
        _noop_sync_builtins,
    )

    def _resolve_mount_path(ensured):
        if not isinstance(ensured, dict):
            return "/domino/datasets/local/autodoc"
        p = (ensured.get("datasetPath") or "").strip()
        return p if p else "/domino/datasets/local/autodoc"

    mock_state.domino_datasets.resolve_dataset_mount_path = MagicMock(side_effect=_resolve_mount_path)

    # ui_components module
    mock_ui = ModuleType("studio.ui_components")
    def _safe_int(v):
        if v in (None, ""):
            return None
        try:
            return int(v)
        except (ValueError, TypeError):
            return None

    def _safe_float(v):
        if v in (None, ""):
            return None
        try:
            return float(v)
        except (ValueError, TypeError):
            return None

    mock_ui._sanitize_optional_int = _safe_int
    mock_ui._sanitize_optional_float = _safe_float
    mock_ui._db_record_to_dataclass = lambda row: _MockDominoJobRecord(
        id=row["id"], owner_id=row["owner_id"],
    )

    # job_engine module
    mock_job_engine = ModuleType("studio.job_engine")
    mock_job_engine._parse_request = AsyncMock(return_value=_MockJobRequest(
        spec_path="/spec.yaml",
        project_id="proj-123",
        code_root="/mnt/code",
        hardware_tier="tier-small",
        environment_id="env-1",
        environment_revision_id="rev-1",
    ))
    mock_job_engine._submit_domino_job = AsyncMock(
        return_value=("run-mock", "https://jobs.example/run-mock"),
    )

    # fasthtml.common — provide real Response import + FT component stubs
    from starlette.responses import Response as StarletteResponse, FileResponse as StarletteFileResponse
    mock_fh_common = ModuleType("fasthtml.common")
    fh_names = ("Div", "P", "A", "Span", "H3", "Select", "Option", "Input",
                "Label", "Table", "Thead", "Tbody", "Tr", "Th", "Td",
                "Ul", "Li", "Pre", "Button", "Details", "Summary")
    for name in fh_names:
        ctor = MagicMock(side_effect=lambda *a, _n=name, **kw: MagicMock(__ft_name__=_n))
        setattr(mock_fh_common, name, ctor)
    mock_fh_common.FT = type("FT", (), {})

    mock_fh = ModuleType("fasthtml")
    mock_fh.common = mock_fh_common

    # autodoc.core.models — DocumentSpec on routes_api (upload validation)
    mock_autodoc_models = ModuleType("autodoc.core.models")
    mock_autodoc_models.DocumentSpec = MagicMock()
    mock_autodoc_models.LANGUAGE_PROFILES = {}

    # authorization — default to "allow everything" so existing route tests pass.
    # Tests that want to exercise deny behaviour override these via side_effect.
    mock_authz = ModuleType("authorization")
    mock_authz.require_domino_job_start = MagicMock()
    mock_authz.require_domino_job_list = MagicMock()
    mock_authz.require_project_write = MagicMock()

    # studio package
    studio_pkg = ModuleType("studio")
    studio_pkg.__path__ = [os.path.join(_pkg_dir, "studio")]
    studio_pkg.__package__ = "studio"

    saved = {}
    mod_keys = (
        "studio", "studio.state", "studio.ui_components", "studio.job_engine",
        "studio.routes_api", "studio.routes_job",
        "fasthtml", "fasthtml.common",
        "autodoc", "autodoc.core", "autodoc.core.models",
        "authorization",
    )
    for key in mod_keys:
        saved[key] = sys.modules.get(key)

    sys.modules["studio"] = studio_pkg
    sys.modules["studio.state"] = mock_state
    sys.modules["studio.ui_components"] = mock_ui
    sys.modules["studio.job_engine"] = mock_job_engine
    sys.modules["fasthtml"] = mock_fh
    sys.modules["fasthtml.common"] = mock_fh_common
    sys.modules["autodoc"] = ModuleType("autodoc")
    sys.modules["autodoc.core"] = ModuleType("autodoc.core")
    sys.modules["autodoc.core.models"] = mock_autodoc_models
    sys.modules["authorization"] = mock_authz

    yield {
        "state": mock_state,
        "ui": mock_ui,
        "job_engine": mock_job_engine,
        "autodoc_models": mock_autodoc_models,
        "authz": mock_authz,
    }

    for key, val in saved.items():
        if val is None:
            sys.modules.pop(key, None)
        else:
            sys.modules[key] = val


def _make_request(query_params=None, form_data=None, json_body=None, content_type=None):
    """Create a mock Starlette Request."""
    req = MagicMock()
    req.query_params = query_params or {}

    _ct = content_type or ("multipart/form-data" if form_data is not None else "application/json")
    req.headers = {"content-type": _ct}

    if form_data is not None:
        async def _form():
            return form_data
        req.form = _form
    else:
        async def _empty_form():
            return {}
        req.form = _empty_form

    _jb = json_body if json_body is not None else {}

    async def _json():
        return _jb
    req.json = _json

    return req


def _import_routes_api():
    sys.modules.pop("studio.routes_api", None)
    path = os.path.join(_pkg_dir, "studio", "routes_api.py")
    return _load_module("studio.routes_api", path)


def _import_routes_job():
    sys.modules.pop("studio.routes_job", None)
    path = os.path.join(_pkg_dir, "studio", "routes_job.py")
    return _load_module("studio.routes_job", path)


def _register(mod, register_fn_name="register_api_routes"):
    """Call a register_*_routes function and capture the handlers."""
    routes = {}

    def fake_rt(path):
        def decorator(fn):
            routes[path] = fn
            return fn
        return decorator

    getattr(mod, register_fn_name)(fake_rt)
    return routes


# ===========================================================================
# routes_api.py
# ===========================================================================

class TestApiRoutes:
    @pytest.mark.asyncio
    async def test_hardware_tiers_returns_json(self, _mock_studio_modules):
        mod = _import_routes_api()
        routes = _register(mod, "register_api_routes")
        client = _mock_studio_modules["state"].domino_client
        client.list_hardware_tiers.return_value = [
            {"id": "tier-1", "name": "Small", "isDefault": True},
        ]
        client.get_project_default_tier.return_value = "tier-1"
        req = _make_request(query_params={"projectId": "proj-123"})
        result = await routes["/api/hardware-tiers"](req)
        client.list_hardware_tiers.assert_called_once()
        body = json.loads(result.body)
        assert isinstance(body, list)
        assert body[0]["id"] == "tier-1"
        assert body[0]["isDefault"] is True

    @pytest.mark.asyncio
    async def test_environment_revisions_returns_json(self, _mock_studio_modules):
        mod = _import_routes_api()
        routes = _register(mod, "register_api_routes")
        client = _mock_studio_modules["state"].domino_client
        client.list_environment_revisions.return_value = [
            {
                "id": "r1",
                "number": 2,
                "option_label": "#2: May 1, 2026",
            },
        ]
        req = _make_request(
            query_params={"projectId": "proj-123", "environmentId": "env-1"},
        )
        result = await routes["/api/environment-revisions"](req)
        client.list_environment_revisions.assert_called_once_with("env-1")
        body = json.loads(result.body)
        assert isinstance(body, list)
        assert body[0]["id"] == "r1"
        assert body[0]["isDefault"] is True

    @pytest.mark.asyncio
    async def test_environment_revisions_empty_when_no_env_id(self, _mock_studio_modules):
        mod = _import_routes_api()
        routes = _register(mod, "register_api_routes")
        req = _make_request(query_params={"projectId": "proj-123"})
        result = await routes["/api/environment-revisions"](req)
        body = json.loads(result.body)
        assert body == []

    @pytest.mark.asyncio
    async def test_datasets_returns_json(self, _mock_studio_modules):
        mod = _import_routes_api()
        routes = _register(mod, "register_api_routes")
        ds = _mock_studio_modules["state"].domino_datasets
        ds.list_datasets.return_value = [{"id": "ds-1", "name": "test-ds"}]
        req = _make_request(query_params={"projectId": "proj-123"})
        result = await routes["/api/datasets"](req)
        ds.list_datasets.assert_called_once()

    @pytest.mark.asyncio
    async def test_datasets_error_returns_500(self, _mock_studio_modules):
        mod = _import_routes_api()
        routes = _register(mod, "register_api_routes")
        ds = _mock_studio_modules["state"].domino_datasets
        ds.list_datasets.side_effect = RuntimeError("API error")
        req = _make_request(query_params={"projectId": "proj-123"})
        result = await routes["/api/datasets"](req)
        assert result.status_code == 500

    @pytest.mark.asyncio
    async def test_dataset_files_requires_dataset_id(self, _mock_studio_modules):
        mod = _import_routes_api()
        routes = _register(mod, "register_api_routes")
        req = _make_request(query_params={})
        result = await routes["/api/dataset-files"](req)
        assert result.status_code == 400

    @pytest.mark.asyncio
    async def test_dataset_files_returns_files(self, _mock_studio_modules):
        mod = _import_routes_api()
        routes = _register(mod, "register_api_routes")
        ds = _mock_studio_modules["state"].domino_datasets
        ds.get_rw_snapshot_id.return_value = "snap-1"
        ds.list_files.return_value = [{"fileName": "spec.yaml"}]
        req = _make_request(query_params={"datasetId": "ds-1", "projectId": "proj-123"})
        result = await routes["/api/dataset-files"](req)
        ds.list_files.assert_called_once()

    @pytest.mark.asyncio
    async def test_download_template(self, _mock_studio_modules, monkeypatch):
        monkeypatch.setattr(
            "dataset_manager.DatasetManager.read_file",
            staticmethod(lambda snap, path: b"title: FromDataset\n"),
        )
        mod = _import_routes_api()
        routes = _register(mod, "register_api_routes")
        req = _make_request(query_params={"projectId": "proj-123"})
        result = await routes["/api/download-template"](req)
        assert result.status_code == 200
        assert b"FromDataset" in result.body

    @pytest.mark.asyncio
    async def test_download_template_requires_project_id(self, _mock_studio_modules):
        _mock_studio_modules["state"]._resolve_request_project_id.return_value = None
        mod = _import_routes_api()
        routes = _register(mod, "register_api_routes")
        req = _make_request(query_params={})
        result = await routes["/api/download-template"](req)
        assert result.status_code == 400

    @pytest.mark.asyncio
    async def test_upload_spec_rejects_invalid_yaml(self, _mock_studio_modules, monkeypatch):
        # Force the gallery validator to raise ValueError as it would for a
        # YAML missing required fields.
        import spec_template_sync as _sts
        monkeypatch.setattr(
            _sts, "validate_gallery_template_yaml",
            lambda content: (_ for _ in ()).throw(ValueError("Missing required field: slug")),
        )
        mock_write = MagicMock()
        monkeypatch.setattr(
            "dataset_manager.DatasetManager.write_file",
            staticmethod(mock_write),
        )
        mod = _import_routes_api()
        routes = _register(mod, "register_api_routes")
        uf = MagicMock()
        uf.filename = "spec.yaml"

        async def _read():
            return b"sections: []\n"

        uf.read = _read
        req = _make_request(
            query_params={"projectId": "proj-123"},
            form_data={"file": uf},
        )
        result = await routes["/api/upload-spec-to-dataset"](req)
        assert result.status_code == 400
        body = json.loads(result.body)
        assert body["valid"] is False
        assert "Missing required field" in body["error"]
        mock_write.assert_not_called()

    @pytest.mark.asyncio
    async def test_upload_spec_succeeds_with_valid_yaml(self, _mock_studio_modules, monkeypatch):
        import spec_template_sync as _sts
        monkeypatch.setattr(_sts, "validate_gallery_template_yaml", lambda content: {"slug": "s"})
        monkeypatch.setattr(_sts, "dataset_rel_path", lambda f: f"spec-templates/{f}")
        mock_write = MagicMock()
        monkeypatch.setattr("dataset_manager.DatasetManager.write_file", staticmethod(mock_write))
        _mock_studio_modules["state"].domino_datasets.ensure_dataset.return_value = {"id": "ds-abc"}
        _mock_studio_modules["state"].domino_datasets.get_rw_snapshot_id.return_value = "snap-1"
        monkeypatch.setattr(_sts, "sync_builtins_to_autodoc_dataset", MagicMock())
        mod = _import_routes_api()
        routes = _register(mod, "register_api_routes")
        uf = MagicMock()
        uf.filename = "mytemplate.yaml"
        valid_yaml = b"slug: my-tpl\ncard_title: T\ncard_description: D\nsections:\n  - name: S1\n"

        async def _read():
            return valid_yaml

        uf.read = _read
        req = _make_request(
            query_params={"projectId": "proj-123"},
            form_data={"file": uf},
        )
        result = await routes["/api/upload-spec-to-dataset"](req)
        assert result.status_code == 200
        body = json.loads(result.body)
        assert body.get("valid") is True
        assert body.get("fileName") == "mytemplate.yaml"
        mock_write.assert_called_once_with("ds-abc", "spec-templates/mytemplate.yaml", valid_yaml)

    @pytest.mark.asyncio
    async def test_upload_spec_rejects_unparseable_yaml(self, _mock_studio_modules, monkeypatch):
        import spec_template_sync as _sts
        monkeypatch.setattr(
            _sts, "validate_gallery_template_yaml",
            lambda content: (_ for _ in ()).throw(ValueError("invalid YAML")),
        )
        mock_write = MagicMock()
        monkeypatch.setattr("dataset_manager.DatasetManager.write_file", staticmethod(mock_write))
        mod = _import_routes_api()
        routes = _register(mod, "register_api_routes")
        uf = MagicMock()
        uf.filename = "bad.yaml"

        async def _read():
            return b": : invalid\n"

        uf.read = _read
        req = _make_request(
            query_params={"projectId": "proj-123"},
            form_data={"file": uf},
        )
        result = await routes["/api/upload-spec-to-dataset"](req)
        assert result.status_code == 400
        body = json.loads(result.body)
        assert body["valid"] is False
        mock_write.assert_not_called()

    @pytest.mark.asyncio
    async def test_upload_spec_rejects_empty_sections(self, _mock_studio_modules, monkeypatch):
        import spec_template_sync as _sts
        monkeypatch.setattr(
            _sts, "validate_gallery_template_yaml",
            lambda content: (_ for _ in ()).throw(ValueError("Missing required field: sections (must be non-empty)")),
        )
        mock_write = MagicMock()
        monkeypatch.setattr("dataset_manager.DatasetManager.write_file", staticmethod(mock_write))
        mod = _import_routes_api()
        routes = _register(mod, "register_api_routes")
        uf = MagicMock()
        uf.filename = "nosec.yaml"

        async def _read():
            return b"slug: s\ncard_title: T\ncard_description: D\nsections: []\n"

        uf.read = _read
        req = _make_request(
            query_params={"projectId": "proj-123"},
            form_data={"file": uf},
        )
        result = await routes["/api/upload-spec-to-dataset"](req)
        assert result.status_code == 400
        body = json.loads(result.body)
        assert body["valid"] is False
        assert "sections" in body["error"]
        mock_write.assert_not_called()

    @pytest.mark.asyncio
    async def test_upload_spec_rejects_non_yaml_extension(self, _mock_studio_modules):
        mod = _import_routes_api()
        routes = _register(mod, "register_api_routes")
        uf = MagicMock()
        uf.filename = "spec.txt"

        async def _read():
            return b"slug: s\n"

        uf.read = _read
        req = _make_request(
            query_params={"projectId": "proj-123"},
            form_data={"file": uf},
        )
        result = await routes["/api/upload-spec-to-dataset"](req)
        assert result.status_code == 400
        body = json.loads(result.body)
        assert "yaml" in body["error"].lower()


    @pytest.mark.asyncio
    async def test_built_in_templates_empty_when_no_project(self, _mock_studio_modules):
        _mock_studio_modules["state"]._resolve_request_project_id.return_value = None
        mod = _import_routes_api()
        routes = _register(mod, "register_api_routes")
        req = _make_request(query_params={})
        result = await routes["/api/built-in-templates"](req)
        assert result.status_code == 200
        assert json.loads(result.body) == []

    @pytest.mark.asyncio
    async def test_built_in_templates_returns_json(self, _mock_studio_modules, monkeypatch):
        catalog_in = [{"slug": "standard_ml", "name": "N", "description": "D", "template_file": "doc_spec.yaml"}]
        expected_out = [
            {
                "slug": "standard_ml",
                "name": "N",
                "description": "D",
                "template_file": "doc_spec.yaml",
                "template_path": "/domino/datasets/local/autodoc/spec-templates/doc_spec.yaml",
                "uid": "/domino/datasets/local/autodoc/spec-templates/doc_spec.yaml",
            }
        ]

        def _fake_catalog(_snap):
            return catalog_in

        mock_sync = MagicMock()
        monkeypatch.setattr("spec_template_sync.sync_builtins_to_autodoc_dataset", mock_sync)
        monkeypatch.setattr("spec_template_sync.catalog_from_dataset", _fake_catalog)
        mod = _import_routes_api()
        routes = _register(mod, "register_api_routes")
        req = _make_request(query_params={"projectId": "proj-123"})
        result = await routes["/api/built-in-templates"](req)
        assert result.status_code == 200
        assert json.loads(result.body) == expected_out
        mock_sync.assert_called_once_with("ds-test", dest_snapshot_id="snap-test")

    @pytest.mark.asyncio
    async def test_built_in_template_yaml_rejects_unknown_file(self, _mock_studio_modules):
        mod = _import_routes_api()
        routes = _register(mod, "register_api_routes")
        req = _make_request(query_params={"projectId": "proj-123", "template_file": "../../../etc/passwd"})
        result = await routes["/api/built-in-template"](req)
        assert result.status_code == 404

    @pytest.mark.asyncio
    async def test_built_in_template_yaml_requires_template_file(self, _mock_studio_modules):
        mod = _import_routes_api()
        routes = _register(mod, "register_api_routes")
        req = _make_request(query_params={"projectId": "proj-123"})
        result = await routes["/api/built-in-template"](req)
        assert result.status_code == 400

    @pytest.mark.asyncio
    async def test_built_in_template_yaml_ignores_filename_query(self, _mock_studio_modules):
        mod = _import_routes_api()
        routes = _register(mod, "register_api_routes")
        req = _make_request(
            query_params={"projectId": "proj-123", "filename": "doc_spec.yaml"},
        )
        result = await routes["/api/built-in-template"](req)
        assert result.status_code == 400

    @pytest.mark.asyncio
    async def test_built_in_template_yaml_returns_body(self, _mock_studio_modules, monkeypatch):
        mock_read = MagicMock(return_value=b"title: X\n")
        monkeypatch.setattr("dataset_manager.DatasetManager.read_file", staticmethod(mock_read))
        mod = _import_routes_api()
        routes = _register(mod, "register_api_routes")
        req = _make_request(query_params={"projectId": "proj-123", "template_file": "doc_spec.yaml"})
        result = await routes["/api/built-in-template"](req)
        assert result.status_code == 200
        assert b"title: X" in result.body
        mock_read.assert_called_once()

    @pytest.mark.asyncio
    async def test_sync_spec_templates_ok(self, _mock_studio_modules, monkeypatch):
        mock_sync = MagicMock()
        monkeypatch.setattr("spec_template_sync.sync_builtins_to_autodoc_dataset", mock_sync)
        mod = _import_routes_api()
        routes = _register(mod, "register_api_routes")
        req = _make_request(query_params={"projectId": "proj-123"})
        result = await routes["/api/sync-spec-templates"](req)
        assert result.status_code == 200
        assert json.loads(result.body).get("ok") is True
        mock_sync.assert_called_once_with("ds-test", dest_snapshot_id="snap-test")

    @pytest.mark.asyncio
    async def test_add_spec_template_copies_and_validates(self, _mock_studio_modules, monkeypatch):
        mod = _import_routes_api()
        routes = _register(mod, "register_api_routes")

        # source snapshot id
        _mock_studio_modules["state"].domino_datasets.get_rw_snapshot_id.return_value = "snap-src"
        # destination autodoc dataset id
        _mock_studio_modules["state"].domino_datasets.ensure_dataset.return_value = {"id": "ds-dest"}

        src_yaml = b"slug: standard_ml\ncard_title: My Card\ncard_description: D\nsections: [a]\n"

        monkeypatch.setattr(
            "dataset_manager.DatasetManager.read_file",
            staticmethod(lambda snap, path: src_yaml),
        )
        write_mock = MagicMock()
        monkeypatch.setattr(
            "dataset_manager.DatasetManager.write_file",
            staticmethod(write_mock),
        )

        req = _make_request(
            query_params={"projectId": "proj-123"},
            json_body={
                "sourceDatasetId": "ds-src",
                "sourceSnapshotId": "snap-src",
                "sourcePath": "some/doc.yaml",
                "filename": "doc.yaml",
            },
        )

        result = await routes["/api/add-spec-template"](req)
        assert result.status_code == 200
        body = json.loads(result.body)
        assert body.get("ok") is True

        # Writes to spec-templates/<filename>
        assert write_mock.call_count == 1
        args = write_mock.call_args[0]
        assert args[0] == "ds-dest"
        assert args[1].endswith("/doc.yaml")

    @pytest.mark.asyncio
    async def test_add_spec_template_rejects_missing_fields(self, _mock_studio_modules, monkeypatch):
        mod = _import_routes_api()
        routes = _register(mod, "register_api_routes")

        _mock_studio_modules["state"].domino_datasets.get_rw_snapshot_id.return_value = "snap-src"
        _mock_studio_modules["state"].domino_datasets.ensure_dataset.return_value = {"id": "ds-dest"}

        bad_yaml = b"card_title: Missing slug\nsections: []\n"
        monkeypatch.setattr(
            "dataset_manager.DatasetManager.read_file",
            staticmethod(lambda snap, path: bad_yaml),
        )
        write_mock = MagicMock()
        monkeypatch.setattr(
            "dataset_manager.DatasetManager.write_file",
            staticmethod(write_mock),
        )

        req = _make_request(
            query_params={"projectId": "proj-123"},
            json_body={
                "sourceDatasetId": "ds-src",
                "sourceSnapshotId": "snap-src",
                "sourcePath": "some/doc.yaml",
                "filename": "doc.yaml",
            },
        )

        result = await routes["/api/add-spec-template"](req)
        assert result.status_code == 400
        body = json.loads(result.body)
        assert "Missing required field" in body.get("error", "")
        write_mock.assert_not_called()


# ===========================================================================
# routes_job.py
# ===========================================================================

class TestJobRoutes:
    @pytest.mark.asyncio
    async def test_run_submits_job(self, _mock_studio_modules):
        mod = _import_routes_job()
        routes = _register(mod, "register_job_routes")
        _mock_studio_modules["state"].domino_job_store.get_user_jobs.return_value = []
        ds = _mock_studio_modules["state"].domino_datasets
        store = _mock_studio_modules["state"].domino_job_store
        req = _make_request()
        result = await routes["/run"](req)
        ds.get_existing_autodoc_dataset.assert_called_once_with("proj-123")
        _mock_studio_modules["job_engine"]._submit_domino_job.assert_called_once()
        store.record_job.assert_called_once_with(
            "test_user",
            "proj-123",
            domino_run_id="run-mock",
            job_url="https://jobs.example/run-mock",
            hardware_tier="tier-small",
            spec_path="/spec.yaml",
        )
        assert result.status_code == 200
        body = json.loads(result.body.decode())
        assert body.get("ok") is True

    @pytest.mark.asyncio
    async def test_run_validation_error_returns_400(self, _mock_studio_modules):
        mod = _import_routes_job()
        routes = _register(mod, "register_job_routes")
        _mock_studio_modules["job_engine"]._submit_domino_job.side_effect = ValueError("bad input")
        req = _make_request()
        result = await routes["/run"](req)
        assert result.status_code == 400
        body = json.loads(result.body.decode())
        assert body.get("error") == "bad input"
        _mock_studio_modules["state"].domino_job_store.record_job.assert_not_called()

    @pytest.mark.asyncio
    async def test_run_handles_submission_error(self, _mock_studio_modules):
        mod = _import_routes_job()
        routes = _register(mod, "register_job_routes")
        _mock_studio_modules["job_engine"]._submit_domino_job.side_effect = RuntimeError("fail")
        store = _mock_studio_modules["state"].domino_job_store
        store.get_user_jobs.return_value = []
        req = _make_request()
        result = await routes["/run"](req)
        _mock_studio_modules["state"].domino_datasets.get_existing_autodoc_dataset.assert_called_once()
        store.record_job.assert_not_called()
        assert result.status_code == 500
        body = json.loads(result.body.decode())
        assert "error" in body

    @pytest.mark.asyncio
    async def test_run_fetch_dataset_failure_returns_500(self, _mock_studio_modules):
        mod = _import_routes_job()
        routes = _register(mod, "register_job_routes")
        _mock_studio_modules["state"].domino_datasets.get_existing_autodoc_dataset.side_effect = RuntimeError(
            "datasets api down",
        )
        req = _make_request()
        result = await routes["/run"](req)
        assert result.status_code == 500
        _mock_studio_modules["job_engine"]._submit_domino_job.assert_not_called()
        _mock_studio_modules["authz"].require_domino_job_start.assert_not_called()
        _mock_studio_modules["state"].domino_datasets.resolve_dataset_mount_path.assert_not_called()

    @pytest.mark.asyncio
    async def test_run_missing_autodoc_dataset_returns_404(self, _mock_studio_modules):
        mod = _import_routes_job()
        routes = _register(mod, "register_job_routes")
        _mock_studio_modules["state"].domino_datasets.get_existing_autodoc_dataset.return_value = None
        req = _make_request()
        result = await routes["/run"](req)
        assert result.status_code == 404
        body = json.loads(result.body.decode())
        assert body.get("error") == "Autodoc dataset not found for this project."
        _mock_studio_modules["job_engine"]._submit_domino_job.assert_not_called()
        _mock_studio_modules["authz"].require_domino_job_start.assert_not_called()
        _mock_studio_modules["state"].domino_datasets.resolve_dataset_mount_path.assert_not_called()

    @pytest.mark.asyncio
    async def test_run_resolve_mount_failure_returns_500(self, _mock_studio_modules):
        mod = _import_routes_job()
        routes = _register(mod, "register_job_routes")
        _mock_studio_modules["state"].domino_datasets.resolve_dataset_mount_path.side_effect = RuntimeError("no mount")
        req = _make_request()
        result = await routes["/run"](req)
        assert result.status_code == 500
        _mock_studio_modules["job_engine"]._submit_domino_job.assert_not_called()
        _mock_studio_modules["authz"].require_domino_job_start.assert_not_called()

    @pytest.mark.asyncio
    async def test_job_history(self, _mock_studio_modules):
        mod = _import_routes_job()
        routes = _register(mod, "register_job_routes")
        _mock_studio_modules["state"].domino_job_store.get_user_jobs.return_value = [
            {"id": "j1", "status": "running", "hardware_tier": "small"}
        ]
        _mock_studio_modules["state"].domino_datasets.list_datasets.return_value = []
        req = _make_request(query_params={"projectId": "proj-123"})
        result = await routes["/job-history"](req)
        body = json.loads(result.body)
        assert "jobs" in body
        assert len(body["jobs"]) == 1
        assert body["jobs"][0].get("document_url") == ""
        assert "document_url" not in body
        _mock_studio_modules["state"].domino_job_store.get_user_jobs.assert_called_with(
            "proj-123", "test_user", limit=50
        )
        _mock_studio_modules["state"].domino_datasets.list_datasets.assert_called_once_with("proj-123")

    @pytest.mark.asyncio
    async def test_job_history_document_url_uses_autodoc_dataset(self, _mock_studio_modules):
        mod = _import_routes_job()
        routes = _register(mod, "register_job_routes")
        _mock_studio_modules["state"].domino_job_store.get_user_jobs.return_value = [
            {"id": "j1", "status": "succeeded"}
        ]
        _mock_studio_modules["state"].domino_datasets.list_datasets.return_value = [
            {"id": "other", "name": "other-ds"},
            {"id": "ds-autodoc", "name": "autodoc"},
        ]
        req = _make_request(query_params={"projectId": "proj-123"})
        with patch(
            "domino_client.build_autodoc_dataset_data_page_url",
            return_value="https://domino/u/o/p/data/rw/upload/autodoc/ds-autodoc/docs",
        ) as mock_b:
            result = await routes["/job-history"](req)
        body = json.loads(result.body)
        assert body["jobs"][0]["document_url"] == "https://domino/u/o/p/data/rw/upload/autodoc/ds-autodoc/docs"
        assert "document_url" not in body
        mock_b.assert_called_once_with("proj-123", "ds-autodoc")

    @pytest.mark.asyncio
    async def test_cancel_queued_jobs(self, _mock_studio_modules):
        mod = _import_routes_job()
        routes = _register(mod, "register_job_routes")
        _mock_studio_modules["state"].domino_job_store.get_user_jobs.return_value = []
        _mock_studio_modules["state"].domino_datasets.list_datasets.return_value = []
        req = _make_request(query_params={"projectId": "proj-123"})
        result = await routes["/cancel-queued-jobs"](req)
        _mock_studio_modules["state"].domino_job_store.cancel_queued_jobs.assert_called_with(
            "proj-123", "test_user"
        )
        body = json.loads(result.body)
        assert body["ok"] is True
        assert "document_url" not in body

    @pytest.mark.asyncio
    async def test_job_history_no_forwarded_token_returns_empty(self, _mock_studio_modules, monkeypatch):
        _drop_viewer(monkeypatch)
        mod = _import_routes_job()
        routes = _register(mod, "register_job_routes")
        req = _make_request(query_params={"projectId": "proj-123"})
        result = await routes["/job-history"](req)
        body = json.loads(result.body)
        assert body["jobs"] == []
        assert "document_url" not in body

    @pytest.mark.asyncio
    async def test_cancel_queued_jobs_no_forwarded_token_is_noop(self, _mock_studio_modules, monkeypatch):
        _drop_viewer(monkeypatch)
        mod = _import_routes_job()
        routes = _register(mod, "register_job_routes")
        req = _make_request(query_params={"projectId": "proj-123"})
        result = await routes["/cancel-queued-jobs"](req)
        _mock_studio_modules["state"].domino_job_store.cancel_queued_jobs.assert_not_called()
        body = json.loads(result.body)
        assert body["ok"] is False
        assert "document_url" not in body

    @pytest.mark.asyncio
    async def test_run_no_forwarded_token_is_noop(self, _mock_studio_modules, monkeypatch):
        _drop_viewer(monkeypatch)
        mod = _import_routes_job()
        routes = _register(mod, "register_job_routes")
        req = _make_request()
        result = await routes["/run"](req)
        _mock_studio_modules["job_engine"]._submit_domino_job.assert_not_called()
        _mock_studio_modules["state"].domino_datasets.get_existing_autodoc_dataset.assert_not_called()
        _mock_studio_modules["state"].domino_job_store.record_job.assert_not_called()
        assert result.status_code == 401
        body = json.loads(result.body.decode())
        assert body.get("error")


class TestSanitizeDatasetSubpath:
    def test_empty(self):
        from studio.routes_api import sanitize_dataset_subpath

        assert sanitize_dataset_subpath("") == ""
        assert sanitize_dataset_subpath(None) == ""

    def test_normalizes_slashes(self):
        from studio.routes_api import sanitize_dataset_subpath

        assert sanitize_dataset_subpath("a/b") == "a/b"
        assert sanitize_dataset_subpath("/a/b/") == "a/b"
        assert sanitize_dataset_subpath("a//b") == "a/b"

    def test_rejects_dotdot(self):
        from studio.routes_api import sanitize_dataset_subpath

        with pytest.raises(ValueError, match="Invalid"):
            sanitize_dataset_subpath("a/../b")
