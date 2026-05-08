"""Tests for domino_job_store.py."""

from __future__ import annotations

import os
import sys
from unittest.mock import MagicMock

_repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_pkg_dir = os.path.join(_repo_root, "auto_model_docs")
for p in (_repo_root, _pkg_dir):
    if p not in sys.path:
        sys.path.insert(0, p)

import domino_job_store as store


def test_get_user_jobs_empty_without_env():
    assert store.get_user_jobs("proj", "alice", limit=10) == []


def test_record_job_skips_without_env():
    store.record_job(
        "alice",
        "proj",
        domino_run_id="r1",
        job_url="http://x",
        branch="",
        hardware_tier="t",
        spec_path="/s.yaml",
    )


def test_cancel_queued_jobs_noop():
    store.cancel_queued_jobs("proj", "alice")


def test_roundtrip_and_refresh(monkeypatch, tmp_path):
    root = tmp_path / "ds"
    root.mkdir()
    monkeypatch.setenv("DOMINO_DATASETS_DIR", str(root))

    mock_client = MagicMock()
    mock_client.get_job_status.return_value = {"local_status": "succeeded", "domino_status": "Succeeded"}
    monkeypatch.setattr(store, "_domino_client", lambda: mock_client)

    store.record_job(
        "u1",
        "proj-a",
        domino_run_id="run-1",
        job_url="http://job",
        branch="main",
        hardware_tier="small",
        spec_path="/x.yaml",
    )
    jobs = store.get_user_jobs("proj-a", "u1", limit=10)
    assert len(jobs) == 1
    assert jobs[0]["domino_run_id"] == "run-1"
    assert jobs[0]["status"] == "succeeded"
    mock_client.get_job_status.assert_called_once_with("run-1")


def test_no_cross_user_leak(monkeypatch, tmp_path):
    root = tmp_path / "ds"
    root.mkdir()
    monkeypatch.setenv("DOMINO_DATASETS_DIR", str(root))
    mock_client = MagicMock()
    mock_client.get_job_status.return_value = {"local_status": "running", "domino_status": "Running"}
    monkeypatch.setattr(store, "_domino_client", lambda: mock_client)

    store.record_job(
        "alice",
        "proj-x",
        domino_run_id="r1",
        job_url="",
        branch="",
        hardware_tier="",
        spec_path="",
    )
    assert store.get_user_jobs("proj-x", "bob", limit=10) == []
    assert len(store.get_user_jobs("proj-x", "alice", limit=10)) == 1
