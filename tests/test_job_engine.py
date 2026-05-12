"""Tests for studio/job_engine.py — polling, reconciliation, request parsing, submission."""

from __future__ import annotations

import asyncio
import importlib.util
import os
import sys
from dataclasses import dataclass
from types import ModuleType
from typing import Any, Optional
from unittest.mock import AsyncMock, MagicMock

import pytest

# Ensure auto_model_docs is importable
_repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_pkg_dir = os.path.join(_repo_root, "auto_model_docs")
for p in (_repo_root, _pkg_dir):
    if p not in sys.path:
        sys.path.insert(0, p)


# ---------------------------------------------------------------------------
# Shared dataclasses (mirror state.py)
# ---------------------------------------------------------------------------

@dataclass
class JobRequest:
    spec_path: str
    provider: str
    model: str
    code_root: str
    max_files: int
    workers: int
    planning_workers: int
    timeout: float
    notebook: bool
    notebook_path: str
    filtered_experiment_names: str
    filtered_model_names: str
    latest_only: bool
    verbose: bool
    hardware_tier: str
    environment_id: str
    environment_revision_id: str
    project_id: str
    provider_base_url: str
    language: str
    max_retries: int
    initial_backoff: float
    max_backoff: float
    backoff_jitter: float
    notebook_from_cache: bool


_JR_DEFAULTS = {
    "spec_path": "",
    "provider": "anthropic",
    "model": "gpt-4",
    "code_root": "/mnt/code",
    "max_files": 50,
    "workers": 4,
    "planning_workers": 3,
    "timeout": 120.0,
    "notebook": False,
    "notebook_path": "",
    "filtered_experiment_names": "",
    "filtered_model_names": "",
    "latest_only": False,
    "verbose": False,
    "hardware_tier": "tier-default",
    "environment_id": "env-default",
    "environment_revision_id": "rev-default",
    "project_id": "",
    "provider_base_url": "",
    "language": "auto",
    "max_retries": 5,
    "initial_backoff": 10.0,
    "max_backoff": 120.0,
    "backoff_jitter": 0.2,
    "notebook_from_cache": False,
}


def _jr(**kwargs):
    return JobRequest(**{**_JR_DEFAULTS, **kwargs})


@dataclass
class DominoJobRecord:
    id: str
    owner_id: str
    domino_run_id: Optional[str] = None
    branch: Optional[str] = None
    hardware_tier: Optional[str] = None
    status: str = "queued"
    domino_status: Optional[str] = None
    job_url: Optional[str] = None
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


def _build_mock_state():
    """Create a module-like object for studio.state."""
    mock_state = ModuleType("studio.state")
    mock_state._get_username = MagicMock(return_value="test_user")
    mock_state._max_jobs = MagicMock(return_value=1)
    mock_state.logger = MagicMock()
    mock_state.JobRequest = JobRequest
    mock_state.DominoJobRecord = DominoJobRecord
    mock_state.domino_client = MagicMock()
    mock_state.domino_job_store = MagicMock()
    mock_state.spec_store = MagicMock()
    mock_state.domino_datasets = MagicMock()
    mock_state.domino_datasets.get_dataset_detail.return_value = {"datasetPath": "/domino/datasets/local/autodoc"}

    def _resolve_request_project_id(req):
        for key in ("projectId", "project_id"):
            raw = req.query_params.get(key)
            if raw:
                s = str(raw).strip()
                if s:
                    return s
        return None

    mock_state._resolve_request_project_id = _resolve_request_project_id
    return mock_state


def _build_mock_ui():
    """Create a module-like object for studio.ui_components."""
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
    mock_ui._db_record_to_dataclass = lambda row: DominoJobRecord(
        id=row["id"], owner_id=row["owner_id"],
        status=row.get("status", "queued"),
        domino_run_id=row.get("domino_run_id"),
    )
    return mock_ui


@pytest.fixture(autouse=True)
def _mock_studio():
    """Provide mocked studio.state and studio.ui_components."""
    mock_state = _build_mock_state()
    mock_ui = _build_mock_ui()

    studio_pkg = ModuleType("studio")
    studio_pkg.__path__ = [os.path.join(_pkg_dir, "studio")]
    studio_pkg.__package__ = "studio"

    saved = {}
    for key in ("studio", "studio.state", "studio.ui_components", "studio.job_engine"):
        saved[key] = sys.modules.get(key)

    sys.modules["studio"] = studio_pkg
    sys.modules["studio.state"] = mock_state
    sys.modules["studio.ui_components"] = mock_ui

    yield mock_state

    for key, val in saved.items():
        if val is None:
            sys.modules.pop(key, None)
        else:
            sys.modules[key] = val


def _import_job_engine():
    """Force-(re)load job_engine from its source file."""
    sys.modules.pop("studio.job_engine", None)
    je_path = os.path.join(_pkg_dir, "studio", "job_engine.py")
    return _load_module("studio.job_engine", je_path)


# ---------------------------------------------------------------------------
# _parse_request
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_parse_request_provider_base_url_preserved():
    je = _import_job_engine()
    from unittest.mock import MagicMock

    req = MagicMock()
    req.query_params = {"projectId": "proj-x"}
    req.json = AsyncMock(
        return_value={
            "provider": "anthropic",
            "model": "claude-3-5-sonnet-20240620",
            "provider_base_url": "https://a.example",
        }
    )
    jr = await je._parse_request(req)
    assert jr.provider_base_url == "https://a.example"

    req.json = AsyncMock(
        return_value={
            "provider": "openai",
            "model": "gpt-4o",
            "provider_base_url": "https://ok/v1",
        }
    )
    jr2 = await je._parse_request(req)
    assert jr2.provider_base_url == "https://ok/v1"


@pytest.mark.asyncio
async def test_parse_request_verbose_checkbox():
    je = _import_job_engine()
    from unittest.mock import MagicMock

    req = MagicMock()
    req.query_params = {"projectId": "proj-x"}
    req.json = AsyncMock(
        return_value={
            "provider": "anthropic",
            "model": "gpt-4",
            "verbose": "true",
        }
    )
    jr = await je._parse_request(req)
    assert jr.verbose is True

    req.json = AsyncMock(
        return_value={
            "provider": "anthropic",
            "model": "gpt-4",
        }
    )
    jr2 = await je._parse_request(req)
    assert jr2.verbose is False


@pytest.mark.asyncio
async def test_parse_request_notebook_off_clears_path_and_from_cache():
    je = _import_job_engine()
    from unittest.mock import MagicMock

    req = MagicMock()
    req.query_params = {"projectId": "proj-x"}
    req.json = AsyncMock(
        return_value={
            "provider": "anthropic",
            "model": "gpt-4",
            "notebook_path": "/out/x.ipynb",
            "notebook_from_cache": True,
        }
    )
    jr = await je._parse_request(req)
    assert jr.notebook is False
    assert jr.notebook_path == ""
    assert jr.notebook_from_cache is False


@pytest.mark.asyncio
async def test_parse_request_notebook_on_keeps_path_and_from_cache():
    je = _import_job_engine()
    from unittest.mock import MagicMock

    req = MagicMock()
    req.query_params = {"projectId": "proj-x"}
    req.json = AsyncMock(
        return_value={
            "provider": "anthropic",
            "model": "gpt-4",
            "notebook": True,
            "notebook_path": "/out/x.ipynb",
            "notebook_from_cache": True,
        }
    )
    jr = await je._parse_request(req)
    assert jr.notebook is True
    assert jr.notebook_path == "/out/x.ipynb"
    assert jr.notebook_from_cache is True


@pytest.mark.asyncio
async def test_parse_request_raises_when_model_missing():
    je = _import_job_engine()
    from unittest.mock import MagicMock

    req = MagicMock()
    req.query_params = {"projectId": "proj-x"}
    req.json = AsyncMock(return_value={"provider": "anthropic"})
    with pytest.raises(RuntimeError, match="model is required"):
        await je._parse_request(req)


@pytest.mark.asyncio
async def test_parse_request_raises_when_provider_missing():
    je = _import_job_engine()
    from unittest.mock import MagicMock

    req = MagicMock()
    req.query_params = {"projectId": "proj-x"}
    req.json = AsyncMock(return_value={})
    with pytest.raises(RuntimeError, match="provider is required"):
        await je._parse_request(req)


@pytest.mark.asyncio
async def test_parse_request_language_defaults_to_auto_when_missing():
    je = _import_job_engine()
    from unittest.mock import MagicMock

    req = MagicMock()
    req.query_params = {"projectId": "proj-x"}
    req.json = AsyncMock(
        return_value={
            "provider": "anthropic",
            "model": "gpt-4",
        }
    )
    jr = await je._parse_request(req)
    assert jr.language == "auto"


@pytest.mark.asyncio
async def test_parse_request_language_always_auto_ignores_body():
    je = _import_job_engine()
    from unittest.mock import MagicMock

    req = MagicMock()
    req.query_params = {"projectId": "proj-x"}
    req.json = AsyncMock(
        return_value={
            "provider": "anthropic",
            "model": "gpt-4",
            "language": "sas",
        }
    )
    jr = await je._parse_request(req)
    assert jr.language == "auto"

    req.json = AsyncMock(
        return_value={
            "provider": "anthropic",
            "model": "gpt-4",
            "language": "fortran",
        }
    )
    jr2 = await je._parse_request(req)
    assert jr2.language == "auto"


@pytest.mark.asyncio
async def test_parse_request_project_id_only_from_query():
    je = _import_job_engine()
    from unittest.mock import MagicMock

    req = MagicMock()
    req.query_params = {"projectId": "from-query"}
    req.json = AsyncMock(
        return_value={
            "target_project": "form-should-not-win",
            "project_id": "hidden-should-not-win",
            "provider": "anthropic",
            "model": "gpt-4",
        }
    )
    jr = await je._parse_request(req)
    assert jr.project_id == "from-query"

    req.query_params = {"project_id": "snake-query"}
    jr2 = await je._parse_request(req)
    assert jr2.project_id == "snake-query"


@pytest.mark.asyncio
async def test_parse_request_environment_from_env_not_body(monkeypatch):
    je = _import_job_engine()
    from unittest.mock import MagicMock

    monkeypatch.setenv("DOMINO_ENVIRONMENT_ID", "env-from-env")
    monkeypatch.setenv("DOMINO_ENVIRONMENT_REVISION_ID", "rev-from-env")
    req = MagicMock()
    req.query_params = {"projectId": "proj-x"}
    req.json = AsyncMock(
        return_value={
            "provider": "anthropic",
            "model": "gpt-4",
            "environment_id": "env123",
            "environment_revision_id": "rev456",
        }
    )
    jr = await je._parse_request(req)
    assert jr.environment_id == "env-from-env"
    assert jr.environment_revision_id == "rev-from-env"


@pytest.mark.asyncio
async def test_parse_request_raises_when_no_query_project_id():
    je = _import_job_engine()
    from unittest.mock import MagicMock

    req = MagicMock()
    req.query_params = {}
    req.json = AsyncMock(
        return_value={
            "target_project": "only-form-not-enough",
            "provider": "anthropic",
            "model": "gpt-4",
        }
    )
    with pytest.raises(RuntimeError, match="project ID"):
        await je._parse_request(req)


# ---------------------------------------------------------------------------
# _build_job_command
# ---------------------------------------------------------------------------

_DS = "/domino/datasets/autodoc"


class TestBuildJobCommand:
    def test_minimal_command(self):
        je = _import_job_engine()
        req = _jr(
            provider="anthropic",
            code_root="/mnt/code",
            notebook=True,
            verbose=True,
        )
        cmd = je._build_job_command(req, "/path/spec.yaml", _DS)
        assert cmd[0] == "python"
        assert "--spec" in cmd
        assert "/path/spec.yaml" in cmd
        assert "--dataset-path" in cmd
        assert _DS in cmd
        assert "--provider" in cmd
        assert "--notebook" in cmd
        assert "--verbose" in cmd
        assert "--language" in cmd
        i = cmd.index("--language")
        assert cmd[i + 1] == "auto"
        cr = cmd.index("--code-root")
        assert cmd[cr + 1] == "/mnt/code"
        assert "--max-files" in cmd
        assert "--max-retries" in cmd
        assert cmd[cmd.index("--max-retries") + 1] == "5"
        assert "--backoff-jitter" in cmd
        assert "--model" in cmd
        assert cmd[cmd.index("--model") + 1] == "gpt-4"

    def test_notebook_unchecked_omits_flag(self):
        je = _import_job_engine()
        req = _jr(
            provider="anthropic",
            code_root="/mnt/code",
            notebook=False,
            verbose=False,
        )
        cmd = je._build_job_command(req, "/spec.yaml", _DS)
        assert "--notebook" not in cmd
        assert "--verbose" not in cmd

    def test_provider_base_url_in_command_for_either_provider(self):
        je = _import_job_engine()
        cmd_anth = je._build_job_command(
            _jr(
                provider="anthropic",
                provider_base_url="https://proxy/v1",
                project_id="p",
                code_root="/c",
                notebook=False,
                verbose=False,
            ),
            "/spec.yaml",
            _DS,
        )
        assert "--provider-base-url" in cmd_anth
        assert "https://proxy/v1" in cmd_anth
        cmd_open = je._build_job_command(
            _jr(
                provider="openai",
                provider_base_url="https://proxy/v1",
                project_id="p",
                code_root="/c",
                notebook=False,
                verbose=False,
            ),
            "/spec.yaml",
            _DS,
        )
        assert "--provider-base-url" in cmd_open
        assert "https://proxy/v1" in cmd_open

    def test_all_options(self):
        je = _import_job_engine()
        req = _jr(
            provider="openai",
            model="gpt-4",
            code_root="/code",
            max_files=10,
            workers=4,
            planning_workers=2,
            timeout=30.0,
            filtered_experiment_names="exp1,exp2",
            filtered_model_names="model1",
            latest_only=True,
            verbose=True,
            notebook=True,
            max_retries=5,
            initial_backoff=10.0,
            max_backoff=120.0,
            backoff_jitter=0.2,
        )
        cmd = je._build_job_command(req, "/spec.yaml", _DS)
        assert "--model" in cmd and "gpt-4" in cmd
        assert "--code-root" in cmd
        assert "--output" not in cmd
        assert "--max-files" in cmd and "10" in cmd
        assert "--generation-workers" in cmd
        assert "--planning-workers" in cmd
        assert "--timeout" in cmd
        assert "--filtered-experiments" in cmd
        assert "--filtered-models" in cmd
        assert "--latest-only" in cmd

    def test_omits_filtered_flags_when_empty_or_whitespace(self):
        je = _import_job_engine()
        for fe, fm in [("", ""), ("  ", " \t")]:
            req = _jr(
                provider="anthropic",
                code_root="/mnt/code",
                notebook=False,
                verbose=False,
                filtered_experiment_names=fe,
                filtered_model_names=fm,
            )
            cmd = je._build_job_command(req, "/spec.yaml", _DS)
            assert "--filtered-experiments" not in cmd
            assert "--filtered-models" not in cmd

    def test_build_requires_spec_and_dataset_paths(self):
        je = _import_job_engine()
        req = _jr(
            provider="anthropic",
            code_root="/c",
            notebook=False,
            verbose=False,
        )
        with pytest.raises(ValueError, match="spec_path"):
            je._build_job_command(req, "", _DS)
        with pytest.raises(ValueError, match="dataset_path"):
            je._build_job_command(req, "/spec.yaml", "")

    def test_command_str_joins_parts(self):
        je = _import_job_engine()
        req = _jr(
            provider="anthropic",
            code_root="/mnt/code",
            notebook=False,
            verbose=False,
        )
        cmd_str = je._build_job_command_str(req, "/spec.yaml", _DS)
        assert isinstance(cmd_str, str)
        assert "python" in cmd_str
        assert "--spec" in cmd_str
        assert "/spec.yaml" in cmd_str


# ---------------------------------------------------------------------------
# _validate_job_inputs
# ---------------------------------------------------------------------------


class TestValidateJobInputs:
    def test_accepts_defaults(self):
        je = _import_job_engine()
        req = _jr(
            spec_path="/spec.yaml",
            provider="anthropic",
            project_id="proj-123",
            code_root="/mnt/code",
        )
        je._validate_job_inputs(req, "/spec.yaml")

    def test_rejects_unknown_provider(self):
        je = _import_job_engine()
        req = _jr(
            spec_path="/spec.yaml",
            provider="google",
            project_id="proj-123",
            code_root="/mnt/code",
        )
        with pytest.raises(ValueError, match="anthropic or openai"):
            je._validate_job_inputs(req, "/spec.yaml")

    def test_rejects_empty_model(self):
        je = _import_job_engine()
        req = _jr(
            spec_path="/spec.yaml",
            provider="anthropic",
            project_id="proj-123",
            code_root="/mnt/code",
            model="",
        )
        with pytest.raises(ValueError, match="Model is required"):
            je._validate_job_inputs(req, "/spec.yaml")

    def test_rejects_bad_language(self):
        je = _import_job_engine()
        req = _jr(
            spec_path="/spec.yaml",
            provider="anthropic",
            project_id="proj-123",
            code_root="/mnt/code",
            language="cobol",
        )
        with pytest.raises(ValueError, match="Language is not supported"):
            je._validate_job_inputs(req, "/spec.yaml")

    def test_rejects_max_files_out_of_range(self):
        je = _import_job_engine()
        req = _jr(
            spec_path="/spec.yaml",
            provider="anthropic",
            project_id="proj-123",
            code_root="/mnt/code",
            max_files=0,
        )
        with pytest.raises(ValueError, match="max_files"):
            je._validate_job_inputs(req, "/spec.yaml")

    def test_rejects_workers_zero(self):
        je = _import_job_engine()
        req = _jr(
            spec_path="/spec.yaml",
            provider="anthropic",
            project_id="proj-123",
            code_root="/mnt/code",
            workers=0,
        )
        with pytest.raises(ValueError, match="generation workers"):
            je._validate_job_inputs(req, "/spec.yaml")

    def test_rejects_timeout_non_positive(self):
        je = _import_job_engine()
        req = _jr(
            spec_path="/spec.yaml",
            provider="anthropic",
            project_id="proj-123",
            code_root="/mnt/code",
            timeout=0.0,
        )
        with pytest.raises(ValueError, match="timeout"):
            je._validate_job_inputs(req, "/spec.yaml")

    def test_rejects_max_backoff_below_initial(self):
        je = _import_job_engine()
        req = _jr(
            spec_path="/spec.yaml",
            provider="anthropic",
            project_id="proj-123",
            code_root="/mnt/code",
            initial_backoff=50.0,
            max_backoff=10.0,
        )
        with pytest.raises(ValueError, match="max_backoff"):
            je._validate_job_inputs(req, "/spec.yaml")

    def test_rejects_negative_backoff_jitter(self):
        je = _import_job_engine()
        req = _jr(
            spec_path="/spec.yaml",
            provider="anthropic",
            project_id="proj-123",
            code_root="/mnt/code",
            backoff_jitter=-0.1,
        )
        with pytest.raises(ValueError, match="backoff_jitter"):
            je._validate_job_inputs(req, "/spec.yaml")


# ---------------------------------------------------------------------------
# _submit_domino_job
# ---------------------------------------------------------------------------

class TestSubmitDominoJob:
    @pytest.mark.asyncio
    async def test_calls_domino_without_job_store(self, _mock_studio):
        je = _import_job_engine()
        client = _mock_studio.domino_client
        client.submit_job.return_value = "run-abc"
        client.build_job_url.return_value = "https://domino/jobs/run-abc"

        req = _jr(
            spec_path="/spec.yaml",
            provider="anthropic",
            project_id="proj-123",
            code_root="/mnt/code",
        )
        rid, url = await je._submit_domino_job(req, "/domino/datasets/local/autodoc")
        assert rid == "run-abc"
        assert url == "https://domino/jobs/run-abc"
        client.submit_job.assert_called_once()
        cmd = client.submit_job.call_args[0][0]
        assert "/domino/datasets/local/autodoc" in cmd
        client.build_job_url.assert_called_once_with("run-abc", project_id="proj-123")

    @pytest.mark.asyncio
    async def test_raises_when_no_spec(self, _mock_studio):
        je = _import_job_engine()
        req = _jr(provider="anthropic", project_id="proj-123")
        with pytest.raises(ValueError, match="spec file is required"):
            await je._submit_domino_job(req, "/domino/datasets/local/autodoc")

    @pytest.mark.asyncio
    async def test_launch_failure_propagates(self, _mock_studio):
        je = _import_job_engine()
        client = _mock_studio.domino_client
        client.submit_job.side_effect = RuntimeError("API down")

        req = _jr(
            spec_path="/spec.yaml",
            provider="anthropic",
            project_id="proj-123",
            code_root="/mnt/code",
        )
        with pytest.raises(RuntimeError, match="API down"):
            await je._submit_domino_job(req, "/domino/datasets/local/autodoc")

    @pytest.mark.asyncio
    async def test_raises_when_missing_hardware_tier(self, _mock_studio):
        je = _import_job_engine()
        req = _jr(
            spec_path="/spec.yaml",
            provider="anthropic",
            project_id="proj-123",
            code_root="/mnt/code",
            hardware_tier="",
        )
        with pytest.raises(ValueError, match="Hardware tier"):
            await je._submit_domino_job(req, "/domino/datasets/local/autodoc")

    @pytest.mark.asyncio
    async def test_raises_when_missing_environment(self, _mock_studio):
        je = _import_job_engine()
        req = _jr(
            spec_path="/spec.yaml",
            provider="anthropic",
            project_id="proj-123",
            code_root="/mnt/code",
            environment_id="",
        )
        with pytest.raises(ValueError, match="Environment is required"):
            await je._submit_domino_job(req, "/domino/datasets/local/autodoc")

    @pytest.mark.asyncio
    async def test_raises_when_missing_environment_revision(self, _mock_studio):
        je = _import_job_engine()
        req = _jr(
            spec_path="/spec.yaml",
            provider="anthropic",
            project_id="proj-123",
            code_root="/mnt/code",
            environment_revision_id="",
        )
        with pytest.raises(ValueError, match="Environment revision"):
            await je._submit_domino_job(req, "/domino/datasets/local/autodoc")

    @pytest.mark.asyncio
    async def test_raises_when_mount_path_empty(self, _mock_studio):
        je = _import_job_engine()
        req = _jr(
            spec_path="/spec.yaml",
            provider="anthropic",
            project_id="proj-123",
            code_root="/mnt/code",
        )
        with pytest.raises(ValueError, match="mount path"):
            await je._submit_domino_job(req, "")
        with pytest.raises(ValueError, match="mount path"):
            await je._submit_domino_job(req, "   ")

    @pytest.mark.asyncio
    async def test_absolute_spec_path_in_command(self, _mock_studio):
        je = _import_job_engine()
        client = _mock_studio.domino_client
        client.submit_job.return_value = "run-abc"
        client.build_job_url.return_value = "https://domino/jobs/run-abc"

        req = _jr(
            spec_path="/mnt/data/autodoc/specs/doc_spec.yaml",
            provider="anthropic",
            project_id="proj-123",
            code_root="/mnt/code",
        )
        await je._submit_domino_job(req, "/domino/datasets/local/autodoc")
        cmd = client.submit_job.call_args[0][0]
        assert "doc_spec.yaml" in cmd

    @pytest.mark.asyncio
    async def test_requires_spec_path_field(self, _mock_studio):
        je = _import_job_engine()
        spec_store = _mock_studio.spec_store

        req = _jr(
            spec_path="",
            provider="anthropic",
            project_id="proj-123",
            code_root="/mnt/code",
        )
        with pytest.raises(ValueError, match="spec file is required"):
            await je._submit_domino_job(req, "/domino/datasets/local/autodoc")
        spec_store.save_spec.assert_not_called()


