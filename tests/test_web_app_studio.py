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

def test_index_shows_datasets_error_without_datasets_env(monkeypatch):
    monkeypatch.delenv("DOMINO_DATASETS_DIR", raising=False)
    monkeypatch.delenv("DOMINO_PROJECT_NAME", raising=False)
    with TestClient(web_app_studio.app) as client:
        resp = client.get("/?projectId=proj-123")
    assert resp.status_code == 200
    assert "Dataset access required" in resp.text
    assert "administrator" in resp.text.lower()
    assert "DOMINO_DATASETS_DIR" not in resp.text


def test_index_shows_project_datasets_error(monkeypatch, tmp_path):
    root = tmp_path / "domino_datasets"
    root.mkdir()
    monkeypatch.setenv("DOMINO_DATASETS_DIR", str(root))
    monkeypatch.setenv("DOMINO_PROJECT_NAME", "autodoc-extension")
    def _deny_dataset(_project_id):
        raise RuntimeError("denied")

    monkeypatch.setattr(web_app_studio.domino_datasets, "ensure_dataset", _deny_dataset)
    with TestClient(web_app_studio.app) as client:
        resp = client.get("/?projectId=proj-123")
    assert resp.status_code == 200
    assert "Cannot access project datasets" in resp.text
    assert "administrator" in resp.text.lower()


def test_index_shows_llm_api_key_notice(monkeypatch, tmp_path):
    root = tmp_path / "domino_datasets"
    root.mkdir()
    monkeypatch.setenv("DOMINO_DATASETS_DIR", str(root))
    monkeypatch.setenv("DOMINO_PROJECT_NAME", "autodoc-extension")
    monkeypatch.setattr(
        web_app_studio.domino_datasets,
        "ensure_dataset",
        lambda project_id: {"id": "ds-1"},
    )
    with TestClient(web_app_studio.app) as client:
        resp = client.get("/?projectId=proj-123")
    assert resp.status_code == 200
    assert "Environment variables ANTHROPIC_API_KEY or OPENAI_API_KEY required." in resp.text

