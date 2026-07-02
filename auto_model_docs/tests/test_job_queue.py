"""Tests for local job queue in domino_job_store and job_engine."""

from __future__ import annotations

import json
import os
import sys
from unittest.mock import MagicMock, patch

_repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_pkg_dir = os.path.join(_repo_root, "auto_model_docs")
for p in (_repo_root, _pkg_dir):
    if p not in sys.path:
        sys.path.insert(0, p)

import domino_job_store as store
from studio.job_engine import build_queue_payload, submit_from_queue_payload, submit_or_enqueue
from studio.state import JobRequest


def _jr(**kwargs):
    defaults = {
        "spec_path": "/spec.yaml",
        "provider": "anthropic",
        "model": "claude-sonnet-4-20250514",
        "code_root": "/mnt/code",
        "max_files": 50,
        "workers": 4,
        "planning_workers": 3,
        "timeout": 120.0,
        "notebook": True,
        "notebook_path": "",
        "filtered_experiment_names": "",
        "filtered_model_names": "",
        "latest_only": False,
        "verbose": False,
        "hardware_tier": "small",
        "environment_id": "env-1",
        "environment_revision_id": "rev-1",
        "project_id": "proj-a",
        "provider_base_url": "",
        "max_retries": 5,
        "initial_backoff": 10.0,
        "max_backoff": 120.0,
        "backoff_jitter": 0.2,
        "notebook_from_cache": False,
        "bundle_id": "",
        "governance_api_host": "",
        "branch": "",
        "prompts_file": "",
    }
    defaults.update(kwargs)
    return JobRequest(**defaults)


def test_build_queue_payload_includes_launch_fields():
    req = _jr()
    payload = build_queue_payload(req, "/spec.yaml")
    assert payload["project_id"] == "proj-a"
    assert payload["tier_id"] == "small"
    assert payload["environment_id"] == "env-1"
    assert "cli.sh" in payload["command_str"]


def test_enqueue_when_active_slots_full(monkeypatch, tmp_path):
    root = tmp_path / "ds"
    root.mkdir()
    monkeypatch.setenv("DOMINO_DATASETS_DIR", str(root))
    monkeypatch.setenv("DOMINO_PROJECT_NAME", "studio-app")
    monkeypatch.setenv("AUTODOC_MAX_JOBS", "1")

    mock_client = MagicMock()
    mock_client.get_job_status.return_value = {"local_status": "running", "domino_status": "Running"}
    monkeypatch.setattr(store, "_domino_client", lambda: mock_client)

    store.record_job(
        "alice",
        "proj-a",
        domino_run_id="run-active",
        job_url="http://job/active",
        hardware_tier="small",
        spec_path="/a.yaml",
        status="running",
    )

    req = _jr()
    with patch("studio.job_engine.launch_domino_job_run") as mock_launch:
        result = submit_or_enqueue("alice", req)
    mock_launch.assert_not_called()
    assert result["queued"] is True
    jobs = store.get_user_jobs("proj-a", "alice", limit=10)
    assert len(jobs) == 2
    queued = [j for j in jobs if j["status"] == "queued" and not j["domino_run_id"]]
    assert len(queued) == 1


def test_dispatch_promotes_queued_job_when_slot_opens(monkeypatch, tmp_path):
    root = tmp_path / "ds"
    root.mkdir()
    monkeypatch.setenv("DOMINO_DATASETS_DIR", str(root))
    monkeypatch.setenv("DOMINO_PROJECT_NAME", "studio-app")

    payload = {
        "command_str": "cli.sh --spec /queued.yaml",
        "branch": None,
        "tier_id": "small",
        "project_id": "proj-a",
        "environment_id": "env-1",
        "environment_revision_id": "rev-1",
    }
    store.enqueue_job(
        "alice",
        "proj-a",
        hardware_tier="small",
        spec_path="/queued.yaml",
        queue_payload=json.dumps(payload),
    )

    def _submit(p):
        assert p["command_str"] == payload["command_str"]
        return "run-promoted", "http://job/promoted"

    mock_client = MagicMock()
    mock_client.get_job_status.return_value = {"local_status": "submitted", "domino_status": "Queued"}
    monkeypatch.setattr(store, "_domino_client", lambda: mock_client)

    promoted = store.dispatch_queued_jobs("proj-a", "alice", 1, _submit)
    assert promoted == 1
    jobs = store.get_user_jobs("proj-a", "alice", limit=10)
    assert jobs[0]["domino_run_id"] == "run-promoted"
    assert jobs[0]["status"] == "submitted"


def test_cancel_queued_jobs_removes_only_local_queue(monkeypatch, tmp_path):
    root = tmp_path / "ds"
    root.mkdir()
    monkeypatch.setenv("DOMINO_DATASETS_DIR", str(root))
    monkeypatch.setenv("DOMINO_PROJECT_NAME", "studio-app")

    mock_client = MagicMock()
    mock_client.get_job_status.return_value = {"local_status": "running", "domino_status": "Running"}
    monkeypatch.setattr(store, "_domino_client", lambda: mock_client)

    store.record_job(
        "alice",
        "proj-a",
        domino_run_id="run-active",
        job_url="http://job/active",
        hardware_tier="small",
        spec_path="/a.yaml",
        status="running",
    )
    store.enqueue_job(
        "alice",
        "proj-a",
        hardware_tier="small",
        spec_path="/queued.yaml",
        queue_payload=json.dumps({"command_str": "cli.sh --spec /queued.yaml"}),
    )

    removed = store.cancel_queued_jobs("proj-a", "alice")
    assert removed == 1
    jobs = store.get_user_jobs("proj-a", "alice", limit=10)
    assert len(jobs) == 1
    assert jobs[0]["domino_run_id"] == "run-active"


def test_no_cross_project_leak(monkeypatch, tmp_path):
    root = tmp_path / "ds"
    root.mkdir()
    monkeypatch.setenv("DOMINO_DATASETS_DIR", str(root))
    monkeypatch.setenv("DOMINO_PROJECT_NAME", "studio-app")

    store.enqueue_job(
        "alice",
        "proj-a",
        hardware_tier="small",
        spec_path="/a.yaml",
        queue_payload=json.dumps({"command_str": "cli.sh --spec /a.yaml"}),
    )
    store.enqueue_job(
        "alice",
        "proj-b",
        hardware_tier="small",
        spec_path="/b.yaml",
        queue_payload=json.dumps({"command_str": "cli.sh --spec /b.yaml"}),
    )

    assert store.cancel_queued_jobs("proj-a", "alice") == 1
    jobs_a = store.get_user_jobs("proj-a", "alice", limit=10)
    jobs_b = store.get_user_jobs("proj-b", "alice", limit=10)
    assert jobs_a == []
    assert len(jobs_b) == 1
    assert jobs_b[0]["spec_path"] == "/b.yaml"


def test_submit_from_queue_payload_calls_launch(monkeypatch):
    monkeypatch.setattr(
        "studio.job_engine.launch_domino_job_run",
        lambda *a, **k: ("run-1", "http://job/1"),
    )
    run_id, job_url = submit_from_queue_payload(
        {
            "command_str": "cli.sh --spec /x.yaml",
            "branch": "main",
            "tier_id": "small",
            "project_id": "proj-a",
            "environment_id": "env-1",
            "environment_revision_id": "rev-1",
        }
    )
    assert run_id == "run-1"
    assert job_url == "http://job/1"
