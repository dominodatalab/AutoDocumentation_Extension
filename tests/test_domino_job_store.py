"""Tests for domino_job_store.py — in-process job index."""

from __future__ import annotations

import os
import sys

import pytest

_repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_pkg_dir = os.path.join(_repo_root, "auto_model_docs")
for p in (_repo_root, _pkg_dir):
    if p not in sys.path:
        sys.path.insert(0, p)

import domino_job_store as store

DS = "ds-test"
SNAP = "snap-test"


@pytest.fixture(autouse=True)
def _reset_store():
    store.reset_store()
    yield
    store.reset_store()


class TestCreateAndGetJob:
    def test_create_returns_id(self):
        jid = store.create_job(DS, SNAP, "alice", "main", "small", "/spec.yaml", "", "")
        assert isinstance(jid, str) and len(jid) > 0

    def test_create_with_custom_id(self):
        jid = store.create_job(DS, SNAP, "alice", "main", "small", "/spec.yaml", "", "", job_id="custom-123")
        assert jid == "custom-123"

    def test_get_job_returns_dict(self):
        jid = store.create_job(DS, SNAP, "alice", "main", "small", "/spec.yaml", "", "")
        job = store.get_job(DS, SNAP, jid)
        assert job is not None
        assert job["owner_id"] == "alice"
        assert job["branch"] == "main"
        assert job["hardware_tier"] == "small"
        assert job["spec_path"] == "/spec.yaml"
        assert job["status"] == "queued"

    def test_get_job_not_found(self):
        assert store.get_job(DS, SNAP, "nonexistent") is None

    def test_create_with_command_and_project_id(self):
        jid = store.create_job(
            DS, SNAP, "bob", None, None, None, "", "",
            command="python main.py", project_id="proj-456",
        )
        job = store.get_job(DS, SNAP, jid)
        assert job["command"] == "python main.py"
        assert job["project_id"] == "proj-456"

    def test_create_with_nulls(self):
        jid = store.create_job(DS, SNAP, "alice", None, None, None, "", "")
        job = store.get_job(DS, SNAP, jid)
        assert job["branch"] is None

    def test_submitted_at_populated(self):
        jid = store.create_job(DS, SNAP, "alice", "main", "small", "/spec.yaml", "", "")
        job = store.get_job(DS, SNAP, jid)
        assert job["submitted_at"] is not None
        assert "T" in job["submitted_at"]

    def test_domino_run_id_initially_null(self):
        jid = store.create_job(DS, SNAP, "alice", "main", "small", "/spec.yaml", "", "")
        job = store.get_job(DS, SNAP, jid)
        assert job["domino_run_id"] is None


class TestUpdateJob:
    def test_update_status(self):
        jid = store.create_job(DS, SNAP, "alice", "main", "small", "/spec.yaml", "", "")
        store.update_job(DS, SNAP, jid, status="running", domino_status="Executing")
        job = store.get_job(DS, SNAP, jid)
        assert job["status"] == "running"
        assert job["domino_status"] == "Executing"

    def test_update_domino_run_id(self):
        jid = store.create_job(DS, SNAP, "alice", "main", "small", "/spec.yaml", "", "")
        store.update_job(DS, SNAP, jid, domino_run_id="run-abc", status="submitted")
        job = store.get_job(DS, SNAP, jid)
        assert job["domino_run_id"] == "run-abc"
        assert job["status"] == "submitted"

    def test_update_no_fields_is_noop(self):
        jid = store.create_job(DS, SNAP, "alice", "main", "small", "/spec.yaml", "", "")
        store.update_job(DS, SNAP, jid)
        assert store.get_job(DS, SNAP, jid)["status"] == "queued"

    def test_update_nonexistent_job_no_error(self):
        store.update_job(DS, SNAP, "ghost-id", status="failed")


class TestGetUserJobs:
    def test_returns_user_jobs_only(self):
        store.create_job(DS, SNAP, "alice", "main", "small", "/a.yaml", "", "")
        store.create_job(DS, SNAP, "bob", "main", "small", "/b.yaml", "", "")
        store.create_job(DS, SNAP, "alice", "dev", "large", "/c.yaml", "", "")
        assert len(store.get_user_jobs(DS, SNAP, "alice")) == 2

    def test_ordered_newest_first(self):
        store.create_job(DS, SNAP, "alice", "main", "s", "/a.yaml", "", "", job_id="job-1")
        store.create_job(DS, SNAP, "alice", "dev", "s", "/b.yaml", "", "", job_id="job-2")
        jobs = store.get_user_jobs(DS, SNAP, "alice")
        assert jobs[0]["id"] == "job-2"

    def test_limit(self):
        for i in range(10):
            store.create_job(DS, SNAP, "alice", "main", "s", "/spec.yaml", "", "")
        assert len(store.get_user_jobs(DS, SNAP, "alice", limit=3)) == 3

    def test_empty_for_unknown_user(self):
        assert store.get_user_jobs(DS, SNAP, "nobody") == []


class TestCountActiveJobs:
    def test_counts_queued_submitted_running(self):
        store.create_job(DS, SNAP, "alice", "main", "s", "/spec.yaml", "", "", job_id="j1")
        store.create_job(DS, SNAP, "alice", "main", "s", "/spec.yaml", "", "", job_id="j2")
        store.update_job(DS, SNAP, "j2", status="running")
        assert store.count_active_jobs(DS, SNAP, "alice") == 2

    def test_excludes_terminal_statuses(self):
        store.create_job(DS, SNAP, "alice", "main", "s", "/spec.yaml", "", "", job_id="j1")
        store.update_job(DS, SNAP, "j1", status="succeeded")
        assert store.count_active_jobs(DS, SNAP, "alice") == 0

    def test_zero_for_unknown_user(self):
        assert store.count_active_jobs(DS, SNAP, "nobody") == 0


class TestGetOldestQueuedJob:
    def test_returns_oldest(self):
        store.create_job(DS, SNAP, "alice", "main", "s", "/spec.yaml", "", "", job_id="old")
        store.create_job(DS, SNAP, "alice", "main", "s", "/spec.yaml", "", "", job_id="new")
        oldest = store.get_oldest_queued_job(DS, SNAP, "alice")
        assert oldest["id"] == "old"

    def test_none_when_no_queued(self):
        store.create_job(DS, SNAP, "alice", "main", "s", "/spec.yaml", "", "", job_id="j1")
        store.update_job(DS, SNAP, "j1", status="succeeded")
        assert store.get_oldest_queued_job(DS, SNAP, "alice") is None

    def test_none_for_unknown_user(self):
        assert store.get_oldest_queued_job(DS, SNAP, "nobody") is None


class TestCancelQueuedJobs:
    def test_cancels_queued(self):
        store.create_job(DS, SNAP, "alice", "main", "s", "/spec.yaml", "", "", job_id="j1")
        store.cancel_queued_jobs(DS, SNAP, "alice")
        assert store.get_job(DS, SNAP, "j1")["status"] == "cancelled"

    def test_does_not_cancel_submitted(self):
        store.create_job(DS, SNAP, "alice", "main", "s", "/spec.yaml", "", "", job_id="j1")
        store.update_job(DS, SNAP, "j1", status="submitted", domino_run_id="run-1")
        store.cancel_queued_jobs(DS, SNAP, "alice")
        assert store.get_job(DS, SNAP, "j1")["status"] == "submitted"


class TestBucketsAndReconcile:
    def test_different_dataset_keys_isolated(self):
        store.create_job(DS, SNAP, "alice", "main", "s", "/a.yaml", "", "", job_id="j1")
        store.create_job("other-ds", SNAP, "alice", "main", "s", "/b.yaml", "", "", job_id="j2")
        assert len(store.get_user_jobs(DS, SNAP, "alice")) == 1
        assert store.get_job("other-ds", SNAP, "j2") is not None

    def test_reconcile_marks_missing_run_as_failed(self):
        jid = store.create_job(DS, SNAP, "alice", "main", "s", "/x.yaml", "", "", job_id="j1")
        store.update_job(DS, SNAP, jid, status="running")
        store.reconcile_stale_jobs(DS, SNAP)
        job = store.get_job(DS, SNAP, jid)
        assert job["status"] == "failed"
        assert job["domino_status"] == "App restarted"

    def test_get_active_jobs_filters_status(self):
        store.create_job(DS, SNAP, "alice", "main", "s", "/a.yaml", "", "", job_id="a")
        store.update_job(DS, SNAP, "a", status="submitted", domino_run_id="r1")
        store.create_job(DS, SNAP, "bob", "main", "s", "/b.yaml", "", "", job_id="b")
        store.update_job(DS, SNAP, "b", status="succeeded")
        active = store.get_active_jobs(DS, SNAP)
        assert len(active) == 1
        assert active[0]["id"] == "a"
