"""Tests for web_app_studio ASGI app wiring."""

from __future__ import annotations

import os
import sys

import pytest
from starlette.testclient import TestClient

_repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_pkg_dir = os.path.join(_repo_root, "auto_model_docs")
for p in (_repo_root, _pkg_dir):
    if p not in sys.path:
        sys.path.insert(0, p)

pytest.importorskip("fasthtml")

import web_app_studio  # noqa: E402


def test_startup_calls_ensure_database_once(monkeypatch):
    called = 0

    def fake() -> None:
        nonlocal called
        called += 1

    monkeypatch.setattr(web_app_studio, "ensure_database", fake)
    with TestClient(web_app_studio.app):
        pass
    assert called == 1

def test_index_shows_job_store_config_error_without_datasets_env(monkeypatch):
    monkeypatch.delenv("DOMINO_DATASETS_DIR", raising=False)
    monkeypatch.delenv("DOMINO_PROJECT_NAME", raising=False)
    with TestClient(web_app_studio.app) as client:
        resp = client.get("/?projectId=proj-123")
    assert resp.status_code == 200
    assert "Job history not configured" in resp.text
    assert "DOMINO_DATASETS_DIR" in resp.text

