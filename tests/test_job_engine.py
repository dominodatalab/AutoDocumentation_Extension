"""Tests for studio/job_engine.py — polling, reconciliation, request parsing, submission."""

from __future__ import annotations

import asyncio
import importlib.util
import os
import sys
from dataclasses import dataclass
from types import ModuleType
from typing import Any, Optional
from unittest.mock import AsyncMock, MagicMock, patch

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
    spec_path: Optional[str] = None
    spec_content: Optional[str] = None
    provider: str = "anthropic"
    model: Optional[str] = None
    api_key: Optional[str] = None
    code_root: Optional[str] = None
    max_files: Optional[int] = None
    workers: Optional[int] = None
    planning_workers: Optional[int] = None
    timeout: Optional[float] = None
    notebook: bool = False
    notebook_path: Optional[str] = None
    experiment_names: Optional[str] = None
    model_names: Optional[str] = None
    latest_only: bool = False
    verbose: bool = True
    branch: Optional[str] = None
    hardware_tier: Optional[str] = None
    api_key_source: str = "domino_env"
    spec_filename: Optional[str] = None
    project_id: Optional[str] = None
    provider_base_url: Optional[str] = None
    language: str = "auto"
    max_retries: Optional[int] = None
    initial_backoff: Optional[float] = None
    max_backoff: Optional[float] = None
    backoff_jitter: Optional[float] = None
    notebook_from_cache: bool = False
    disable_project_filtering: bool = False


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
    req.form = AsyncMock(
        return_value={
            "provider": "anthropic",
            "provider_base_url": "https://a.example",
        }
    )
    jr = await je._parse_request(req)
    assert jr.provider_base_url == "https://a.example"

    req.form = AsyncMock(
        return_value={
            "provider": "openai",
            "provider_base_url": "https://ok/v1",
        }
    )
    jr2 = await je._parse_request(req)
    assert jr2.provider_base_url == "https://ok/v1"


@pytest.mark.asyncio
async def test_parse_request_language_defaults_to_auto_when_missing():
    je = _import_job_engine()
    from unittest.mock import MagicMock

    req = MagicMock()
    req.query_params = {"projectId": "proj-x"}
    req.form = AsyncMock(
        return_value={
            "provider": "anthropic",
        }
    )
    jr = await je._parse_request(req)
    assert jr.language == "auto"


@pytest.mark.asyncio
async def test_parse_request_language_allowed_and_invalid():
    je = _import_job_engine()
    from unittest.mock import MagicMock

    req = MagicMock()
    req.query_params = {"projectId": "proj-x"}
    req.form = AsyncMock(
        return_value={
            "provider": "anthropic",
            "language": "sas",
        }
    )
    jr = await je._parse_request(req)
    assert jr.language == "sas"

    req.form = AsyncMock(
        return_value={
            "provider": "anthropic",
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
    req.form = AsyncMock(
        return_value={
            "target_project": "form-should-not-win",
            "project_id": "hidden-should-not-win",
            "provider": "anthropic",
        }
    )
    jr = await je._parse_request(req)
    assert jr.project_id == "from-query"

    req.query_params = {"project_id": "snake-query"}
    jr2 = await je._parse_request(req)
    assert jr2.project_id == "snake-query"


@pytest.mark.asyncio
async def test_parse_request_raises_when_no_query_project_id():
    je = _import_job_engine()
    from unittest.mock import MagicMock

    req = MagicMock()
    req.query_params = {}
    req.form = AsyncMock(
        return_value={
            "target_project": "only-form-not-enough",
            "provider": "anthropic",
        }
    )
    with pytest.raises(RuntimeError, match="project ID"):
        await je._parse_request(req)


# ---------------------------------------------------------------------------
# _build_job_command
# ---------------------------------------------------------------------------

_DS = "/domino/datasets/autodoc"

_ADV = dict(
    max_files=50,
    workers=4,
    planning_workers=3,
    timeout=120.0,
    max_retries=5,
    initial_backoff=10.0,
    max_backoff=120.0,
    backoff_jitter=0.2,
    notebook_from_cache=False,
    disable_project_filtering=False,
)


class TestBuildJobCommand:
    def test_minimal_command(self):
        je = _import_job_engine()
        req = JobRequest(
            provider="anthropic",
            code_root="/mnt/code",
            notebook=True,
            verbose=True,
            **_ADV,
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

    def test_notebook_unchecked_omits_flag(self):
        je = _import_job_engine()
        req = JobRequest(
            provider="anthropic",
            code_root="/mnt/code",
            notebook=False,
            verbose=False,
            **_ADV,
        )
        cmd = je._build_job_command(req, "/spec.yaml", _DS)
        assert "--notebook" not in cmd
        assert "--verbose" not in cmd

    def test_provider_base_url_in_command_for_either_provider(self):
        je = _import_job_engine()
        cmd_anth = je._build_job_command(
            JobRequest(
                provider="anthropic",
                provider_base_url="https://proxy/v1",
                project_id="p",
                code_root="/c",
                notebook=False,
                verbose=False,
                **_ADV,
            ),
            "/spec.yaml",
            _DS,
        )
        assert "--provider-base-url" in cmd_anth
        assert "https://proxy/v1" in cmd_anth
        cmd_open = je._build_job_command(
            JobRequest(
                provider="openai",
                provider_base_url="https://proxy/v1",
                project_id="p",
                code_root="/c",
                notebook=False,
                verbose=False,
                **_ADV,
            ),
            "/spec.yaml",
            _DS,
        )
        assert "--provider-base-url" in cmd_open
        assert "https://proxy/v1" in cmd_open

    def test_all_options(self):
        je = _import_job_engine()
        req = JobRequest(
            provider="openai", model="gpt-4", code_root="/code",
            max_files=10, workers=4, planning_workers=2,
            timeout=30.0, experiment_names="exp1,exp2", model_names="model1",
            latest_only=True, verbose=True, notebook=True,
            max_retries=5,
            initial_backoff=10.0,
            max_backoff=120.0,
            backoff_jitter=0.2,
            disable_project_filtering=True,
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
        assert "--disable-project-filtering" in cmd

    def test_build_requires_spec_and_dataset_paths(self):
        je = _import_job_engine()
        req = JobRequest(
            provider="anthropic",
            code_root="/c",
            notebook=False,
            verbose=False,
            **_ADV,
        )
        with pytest.raises(ValueError, match="spec_path"):
            je._build_job_command(req, None, _DS)
        with pytest.raises(ValueError, match="dataset_path"):
            je._build_job_command(req, "/spec.yaml", "")

    def test_build_requires_generation_settings(self):
        je = _import_job_engine()
        req = JobRequest(
            provider="anthropic",
            code_root="/c",
            notebook=False,
            verbose=False,
            max_files=50,
            workers=4,
            planning_workers=3,
            timeout=None,
            max_retries=5,
            initial_backoff=10.0,
            max_backoff=120.0,
            backoff_jitter=0.2,
        )
        with pytest.raises(ValueError, match="internal"):
            je._build_job_command(req, "/spec.yaml", _DS)

    def test_command_str_joins_parts(self):
        je = _import_job_engine()
        req = JobRequest(
            provider="anthropic",
            code_root="/mnt/code",
            notebook=False,
            verbose=False,
            **_ADV,
        )
        cmd_str = je._build_job_command_str(req, "/spec.yaml", _DS)
        assert isinstance(cmd_str, str)
        assert "python" in cmd_str
        assert "--spec" in cmd_str
        assert "/spec.yaml" in cmd_str


# ---------------------------------------------------------------------------
# _submit_domino_job
# ---------------------------------------------------------------------------

class TestSubmitDominoJob:
    @pytest.mark.asyncio
    async def test_submit_immediate_when_under_limit(self, _mock_studio):
        je = _import_job_engine()
        store = _mock_studio.domino_job_store
        client = _mock_studio.domino_client

        store.create_job.return_value = "job-1"
        store.count_active_jobs.return_value = 1
        client.submit_job.return_value = "run-abc"
        client.build_job_url.return_value = "https://domino/jobs/run-abc"
        store.get_job.return_value = {
            "id": "job-1", "owner_id": "test_user", "status": "submitted",
            "domino_run_id": "run-abc",
        }

        req = JobRequest(
            spec_path="/spec.yaml",
            provider="anthropic",
            project_id="proj-123",
            code_root="/mnt/code",
            **_ADV,
        )
        result = await je._submit_domino_job(req, "test_user", "ds-1", "snap-1")
        assert result.id == "job-1"
        client.submit_job.assert_called_once()

    @pytest.mark.asyncio
    async def test_queued_when_over_limit(self, _mock_studio):
        je = _import_job_engine()
        store = _mock_studio.domino_job_store

        store.create_job.return_value = "job-2"
        store.count_active_jobs.return_value = 2
        store.get_job.return_value = {
            "id": "job-2", "owner_id": "test_user", "status": "queued",
            "domino_run_id": None,
        }

        req = JobRequest(
            spec_path="/spec.yaml",
            provider="anthropic",
            project_id="proj-123",
            code_root="/mnt/code",
            **_ADV,
        )
        result = await je._submit_domino_job(req, "test_user", "ds-1", "snap-1")
        assert result.status == "queued"
        _mock_studio.domino_client.submit_job.assert_not_called()

    @pytest.mark.asyncio
    async def test_raises_when_no_spec(self, _mock_studio):
        je = _import_job_engine()
        req = JobRequest(provider="anthropic", project_id="proj-123")
        with pytest.raises(ValueError, match="spec file is required"):
            await je._submit_domino_job(req, "test_user", "ds-1", "snap-1")

    @pytest.mark.asyncio
    async def test_submission_failure_marks_job_failed(self, _mock_studio):
        je = _import_job_engine()
        store = _mock_studio.domino_job_store
        client = _mock_studio.domino_client

        store.create_job.return_value = "job-3"
        store.count_active_jobs.return_value = 1
        client.submit_job.side_effect = RuntimeError("API down")
        store.get_job.return_value = {
            "id": "job-3", "owner_id": "test_user", "status": "failed",
            "domino_run_id": None,
        }

        req = JobRequest(
            spec_path="/spec.yaml",
            provider="anthropic",
            project_id="proj-123",
            code_root="/mnt/code",
            **_ADV,
        )
        result = await je._submit_domino_job(req, "test_user", "ds-1", "snap-1")
        assert result.status == "failed"

    @pytest.mark.asyncio
    async def test_dataset_spec_path_resolved(self, _mock_studio):
        je = _import_job_engine()
        store = _mock_studio.domino_job_store
        client = _mock_studio.domino_client
        datasets = _mock_studio.domino_datasets

        datasets.get_dataset_detail.return_value = {"datasetPath": "/mnt/data/my-dataset"}
        datasets.get_dataset_mount_prefix.return_value = "/mnt/data"
        store.create_job.return_value = "job-4"
        store.count_active_jobs.return_value = 1
        client.submit_job.return_value = "run-xyz"
        client.build_job_url.return_value = "https://domino/jobs/run-xyz"
        store.get_job.return_value = {
            "id": "job-4", "owner_id": "test_user", "status": "submitted",
            "domino_run_id": "run-xyz",
        }

        import dataset_manager
        with patch.object(
            dataset_manager.DatasetManager, "file_exists",
            staticmethod(lambda snap, path: True),
        ):
            req = JobRequest(
                spec_path="dataset://my-dataset/spec.yaml",
                provider="anthropic",
                project_id="proj-123",
                code_root="/mnt/code",
                **_ADV,
            )
            await je._submit_domino_job(req, "test_user", "ds-test", "snap-test")
        call_args = store.create_job.call_args
        spec_in_db = call_args[1].get("spec_path") or call_args[0][4]
        assert "/mnt/data/my-dataset/spec.yaml" in spec_in_db

    @pytest.mark.asyncio
    async def test_dataset_spec_deleted_externally_raises(self, _mock_studio):
        je = _import_job_engine()
        _mock_studio.domino_datasets.get_dataset_detail.return_value = {"datasetPath": "/mnt/data/autodoc"}
        _mock_studio.domino_datasets.get_dataset_mount_prefix.return_value = "/mnt/data"

        import dataset_manager
        with patch.object(
            dataset_manager.DatasetManager, "file_exists",
            staticmethod(lambda snap, path: False),
        ):
            req = JobRequest(
                spec_path="dataset://autodoc/specs/doc_spec.yaml",
                provider="anthropic",
                project_id="proj-123",
                code_root="/mnt/code",
                **_ADV,
            )
            with pytest.raises(ValueError, match="no longer exists"):
                await je._submit_domino_job(req, "test_user", "ds-test", "snap-test")
        _mock_studio.domino_job_store.create_job.assert_not_called()

    @pytest.mark.asyncio
    async def test_non_dataset_spec_path_skips_verification(self, _mock_studio):
        je = _import_job_engine()
        store = _mock_studio.domino_job_store
        client = _mock_studio.domino_client

        store.create_job.return_value = "job-5"
        store.count_active_jobs.return_value = 1
        client.submit_job.return_value = "run-abc"
        client.build_job_url.return_value = "https://domino/jobs/run-abc"
        store.get_job.return_value = {
            "id": "job-5", "owner_id": "test_user", "status": "submitted",
        }

        req = JobRequest(
            spec_path="/mnt/data/autodoc/specs/doc_spec.yaml",
            provider="anthropic",
            project_id="proj-123",
            code_root="/mnt/code",
            **_ADV,
        )
        await je._submit_domino_job(req, "test_user", "ds-1", "snap-1")
        client.submit_job.assert_called_once()


# ---------------------------------------------------------------------------
# _reconcile_stale_jobs
# ---------------------------------------------------------------------------

class TestReconcileStaleJobs:
    def test_marks_stale_jobs_as_failed(self, _mock_studio):
        je = _import_job_engine()
        store = _mock_studio.domino_job_store

        je._reconcile_stale_jobs("ds-1", "snap-1")
        store.reconcile_stale_jobs.assert_called_once()

    def test_handles_exception_gracefully(self, _mock_studio):
        je = _import_job_engine()
        _mock_studio.domino_job_store.reconcile_stale_jobs.side_effect = RuntimeError("error")
        je._reconcile_stale_jobs("ds-1", "snap-1")


# ---------------------------------------------------------------------------
# sync_jobs_for (request-driven replacement for the background poller)
# ---------------------------------------------------------------------------

class TestSyncJobsFor:
    def test_refreshes_active_jobs_for_owner(self, _mock_studio):
        je = _import_job_engine()
        store = _mock_studio.domino_job_store
        client = _mock_studio.domino_client

        store.get_active_jobs.return_value = [
            {"id": "job-1", "owner_id": "alice", "domino_run_id": "run-1",
             "status": "submitted", "domino_status": "Queued"},
            {"id": "job-2", "owner_id": "bob", "domino_run_id": "run-2",
             "status": "submitted", "domino_status": "Queued"},
        ]
        store.count_active_jobs.return_value = 0
        store.get_oldest_queued_job.return_value = None
        client.get_job_status.return_value = {
            "domino_status": "Succeeded",
            "local_status": "succeeded",
        }

        je.sync_jobs_for("alice", "ds-1", "snap-1")

        client.get_job_status.assert_called_once_with("run-1")
        store.update_job.assert_called()

    def test_promotes_queued_jobs_for_owner(self, _mock_studio):
        je = _import_job_engine()
        store = _mock_studio.domino_job_store
        client = _mock_studio.domino_client

        store.get_active_jobs.return_value = []
        store.count_active_jobs.return_value = 0
        store.get_oldest_queued_job.return_value = {
            "id": "queued-1", "command": "python main.py",
            "branch": "main", "hardware_tier": None,
            "project_id": "proj-123",
        }
        client.submit_job.return_value = "run-promoted"
        client.build_job_url.return_value = "https://domino/jobs/run-promoted"

        je.sync_jobs_for("alice", "ds-1", "snap-1")

        client.submit_job.assert_called_once()
        store.update_job.assert_called()

    def test_swallows_errors(self, _mock_studio):
        je = _import_job_engine()
        _mock_studio.domino_job_store.get_active_jobs.side_effect = RuntimeError("boom")
        je.sync_jobs_for("alice", "ds-1", "snap-1")
