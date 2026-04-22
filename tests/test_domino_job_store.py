"""Tests for domino_job_store.py -- JSON index backed by DatasetManager."""

from __future__ import annotations

import json
import os
import sys

import pytest

_repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_pkg_dir = os.path.join(_repo_root, "auto_model_docs")
for p in (_repo_root, _pkg_dir):
    if p not in sys.path:
        sys.path.insert(0, p)

import dataset_ctx
import dataset_manager
import domino_job_store as store


class _MemFs:
    """Tiny byte-addressed in-memory filesystem shared by patched statics."""

    def __init__(self):
        self._files: dict[str, bytes] = {}

    def exists(self, path: str) -> bool:
        return path in self._files

    def read(self, path: str) -> bytes:
        if path not in self._files:
            raise FileNotFoundError(path)
        return self._files[path]

    def write(self, path: str, content: bytes) -> None:
        self._files[path] = content


@pytest.fixture(autouse=True)
def _mock_store(monkeypatch):
    """Patch DatasetManager static methods to read/write an in-memory fs."""
    fs = _MemFs()

    monkeypatch.setattr(
        dataset_manager.DatasetManager, "write_file",
        staticmethod(lambda dsid, path, content: fs.write(path, content)),
    )
    monkeypatch.setattr(
        dataset_manager.DatasetManager, "read_file",
        staticmethod(lambda snap, path: fs.read(path)),
    )
    monkeypatch.setattr(
        dataset_manager.DatasetManager, "file_exists",
        staticmethod(lambda snap, path: fs.exists(path)),
    )
    monkeypatch.setattr(
        dataset_manager.DatasetManager, "list_files",
        staticmethod(lambda snap, path="": []),
    )
    monkeypatch.setattr(
        dataset_manager.DatasetManager, "read_file_meta",
        staticmethod(lambda snap, path: {"sizeInBytes": len(fs.read(path))}),
    )

    dataset_ctx.set_dataset_ctx("ds-test", "snap-test")
    yield fs
    dataset_ctx.clear_dataset_ctx()


class TestCreateAndGetJob:
    def test_create_returns_id(self):
        jid = store.create_job("alice", "main", "small", "/spec.yaml")
        assert isinstance(jid, str)
        assert len(jid) > 0

    def test_create_with_custom_id(self):
        jid = store.create_job("alice", "main", "small", "/spec.yaml", job_id="custom-123")
        assert jid == "custom-123"

    def test_get_job_returns_dict(self):
        jid = store.create_job("alice", "main", "small", "/spec.yaml")
        job = store.get_job(jid)
        assert job is not None
        assert job["owner_id"] == "alice"
        assert job["branch"] == "main"
        assert job["hardware_tier"] == "small"
        assert job["spec_path"] == "/spec.yaml"
        assert job["status"] == "queued"

    def test_get_job_not_found(self):
        assert store.get_job("nonexistent") is None

    def test_create_with_command_and_project_id(self):
        jid = store.create_job(
            "bob", None, None, None,
            command="python main.py", project_id="proj-456",
        )
        job = store.get_job(jid)
        assert job["command"] == "python main.py"
        assert job["project_id"] == "proj-456"

    def test_create_with_nulls(self):
        jid = store.create_job("alice", None, None, None)
        job = store.get_job(jid)
        assert job["branch"] is None

    def test_submitted_at_populated(self):
        jid = store.create_job("alice", "main", "small", "/spec.yaml")
        job = store.get_job(jid)
        assert job["submitted_at"] is not None
        assert "T" in job["submitted_at"]

    def test_domino_run_id_initially_null(self):
        jid = store.create_job("alice", "main", "small", "/spec.yaml")
        job = store.get_job(jid)
        assert job["domino_run_id"] is None


class TestUpdateJob:
    def test_update_status(self):
        jid = store.create_job("alice", "main", "small", "/spec.yaml")
        store.update_job(jid, status="running", domino_status="Executing")
        job = store.get_job(jid)
        assert job["status"] == "running"
        assert job["domino_status"] == "Executing"

    def test_update_domino_run_id(self):
        jid = store.create_job("alice", "main", "small", "/spec.yaml")
        store.update_job(jid, domino_run_id="run-abc", status="submitted")
        job = store.get_job(jid)
        assert job["domino_run_id"] == "run-abc"
        assert job["status"] == "submitted"

    def test_update_no_fields_is_noop(self):
        jid = store.create_job("alice", "main", "small", "/spec.yaml")
        store.update_job(jid)
        assert store.get_job(jid)["status"] == "queued"

    def test_update_nonexistent_job_no_error(self):
        store.update_job("ghost-id", status="failed")  # should not raise


class TestGetUserJobs:
    def test_returns_user_jobs_only(self):
        store.create_job("alice", "main", "small", "/a.yaml")
        store.create_job("bob", "main", "small", "/b.yaml")
        store.create_job("alice", "dev", "large", "/c.yaml")
        assert len(store.get_user_jobs("alice")) == 2

    def test_ordered_newest_first(self):
        store.create_job("alice", "main", "s", "/a.yaml", job_id="job-1")
        store.create_job("alice", "dev", "s", "/b.yaml", job_id="job-2")
        jobs = store.get_user_jobs("alice")
        assert jobs[0]["id"] == "job-2"

    def test_limit(self):
        for i in range(10):
            store.create_job("alice", "main", "s", "/spec.yaml")
        assert len(store.get_user_jobs("alice", limit=3)) == 3

    def test_empty_for_unknown_user(self):
        assert store.get_user_jobs("nobody") == []


class TestCountActiveJobs:
    def test_counts_queued_submitted_running(self):
        store.create_job("alice", "main", "s", "/spec.yaml", job_id="j1")
        store.create_job("alice", "main", "s", "/spec.yaml", job_id="j2")
        store.update_job("j2", status="running")
        assert store.count_active_jobs("alice") == 2

    def test_excludes_terminal_statuses(self):
        store.create_job("alice", "main", "s", "/spec.yaml", job_id="j1")
        store.update_job("j1", status="succeeded")
        assert store.count_active_jobs("alice") == 0

    def test_zero_for_unknown_user(self):
        assert store.count_active_jobs("nobody") == 0


class TestGetOldestQueuedJob:
    def test_returns_oldest(self):
        store.create_job("alice", "main", "s", "/spec.yaml", job_id="old")
        store.create_job("alice", "main", "s", "/spec.yaml", job_id="new")
        oldest = store.get_oldest_queued_job("alice")
        assert oldest["id"] == "old"

    def test_none_when_no_queued(self):
        store.create_job("alice", "main", "s", "/spec.yaml", job_id="j1")
        store.update_job("j1", status="succeeded")
        assert store.get_oldest_queued_job("alice") is None

    def test_none_for_unknown_user(self):
        assert store.get_oldest_queued_job("nobody") is None


class TestCancelQueuedJobs:
    def test_cancels_queued(self):
        store.create_job("alice", "main", "s", "/spec.yaml", job_id="j1")
        store.cancel_queued_jobs("alice")
        assert store.get_job("j1")["status"] == "cancelled"

    def test_does_not_cancel_submitted(self):
        store.create_job("alice", "main", "s", "/spec.yaml", job_id="j1")
        store.update_job("j1", status="submitted", domino_run_id="run-1")
        store.cancel_queued_jobs("alice")
        assert store.get_job("j1")["status"] == "submitted"


class TestIndexPersistence:
    def test_index_stored_in_dataset(self, _mock_store):
        store.create_job("alice", "main", "small", "/spec.yaml")
        assert _mock_store.exists(".autodoc/jobs_index.json")
        content = json.loads(_mock_store.read(".autodoc/jobs_index.json"))
        assert len(content) == 1
        assert content[0]["owner_id"] == "alice"

    def test_survives_read_cycle(self, _mock_store):
        store.create_job("alice", "main", "s", "/a.yaml", job_id="j1")
        store.create_job("bob", "main", "s", "/b.yaml", job_id="j2")
        assert store.get_job("j1")["owner_id"] == "alice"
        assert store.get_job("j2")["owner_id"] == "bob"
