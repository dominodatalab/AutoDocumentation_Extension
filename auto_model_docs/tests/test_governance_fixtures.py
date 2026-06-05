"""A0: governance API fixtures and modelId attachment matching."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest

_repo_root = Path(__file__).resolve().parents[2]
_pkg_dir = _repo_root / "auto_model_docs"
for p in (str(_repo_root), str(_pkg_dir)):
    if p not in sys.path:
        sys.path.insert(0, p)

from governance_client import compute_policy, get_findings, list_bundles

FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures" / "governance"
PROJECT_ID = "6a21c81b3bff9f0d3ae561b1"
MLFLOW3_MODEL_ID = "mlflow3-logged-and-registered1"
MLFLOW3_BUNDLE_ID = "7f746bd1-3c88-4d89-97d0-9eba1bfb38b0"
MIXED_MODEL_ID = "mlflow3-mixed-logged-and-registered1"
OPEN_FINDING_STATUS = "To do"


def _load(name: str) -> Any:
    with (FIXTURES_DIR / name).open(encoding="utf-8") as f:
        return json.load(f)


def _model_version_name(attachment: dict[str, Any]) -> str | None:
    if attachment.get("type") != "ModelVersion":
        return None
    identifier = attachment.get("identifier") or {}
    if not isinstance(identifier, dict):
        return None
    name = identifier.get("name")
    return str(name) if name else None


def bundles_for_model_id(bundles_payload: dict[str, Any], model_id: str) -> list[dict[str, Any]]:
    matched = []
    for bundle in bundles_payload.get("data") or []:
        if not isinstance(bundle, dict):
            continue
        for att in bundle.get("attachments") or []:
            if isinstance(att, dict) and _model_version_name(att) == model_id:
                matched.append(bundle)
                break
    return matched


@pytest.fixture(autouse=True)
def _env(monkeypatch):
    monkeypatch.setenv("DOMINO_API_HOST", "https://domino.example.com")
    monkeypatch.setenv("DOMINO_USER_API_KEY", "test-key")


def test_fixture_files_exist():
    for name in (
        "bundles-list-modeldocs-target-bgp.json",
        "compute-policy-mlflow3-bundle.json",
        "findings-todo.json",
    ):
        assert (FIXTURES_DIR / name).is_file()


def test_list_bundles_fixture_parses():
    payload = _load("bundles-list-modeldocs-target-bgp.json")
    with patch("governance_client._domino_request", return_value=payload):
        bundles = list_bundles(PROJECT_ID)
    assert len(bundles) == 5
    assert bundles[0].id == MLFLOW3_BUNDLE_ID
    assert bundles[0].attachments[0].identifier["name"] == MLFLOW3_MODEL_ID


def test_model_id_matches_single_bundle():
    payload = _load("bundles-list-modeldocs-target-bgp.json")
    matched = bundles_for_model_id(payload, MLFLOW3_MODEL_ID)
    assert len(matched) == 1
    assert matched[0]["id"] == MLFLOW3_BUNDLE_ID


def test_model_id_matches_two_bundles_for_mixed_model():
    payload = _load("bundles-list-modeldocs-target-bgp.json")
    matched = bundles_for_model_id(payload, MIXED_MODEL_ID)
    assert len(matched) == 2
    ids = {b["id"] for b in matched}
    assert ids == {
        "b2222222-2222-2222-2222-222222222201",
        "b2222222-2222-2222-2222-222222222202",
    }


def test_compute_policy_fixture_latest_results_only():
    payload = _load("compute-policy-mlflow3-bundle.json")
    with patch("governance_client._domino_request", return_value=payload):
        computed = compute_policy(MLFLOW3_BUNDLE_ID, "a1111111-1111-1111-1111-111111111101")
    assert computed is not None
    assert computed.bundle.name == "mlflow3-logged-and-registered1-governance-bundle"
    assert len(computed.results) == 2
    assert all(r.is_latest for r in computed.results)
    assert computed.results[0].artifact_content == {"value": "Yes"}


def test_findings_fixture_open_status_api_string():
    payload = _load("findings-todo.json")
    with patch("governance_client._domino_request", return_value=payload):
        findings = get_findings(MLFLOW3_BUNDLE_ID)
    assert len(findings) == 2
    statuses = {f.status for f in findings}
    assert OPEN_FINDING_STATUS in statuses
    assert "Done" in statuses
    open_findings = [f for f in findings if f.status == OPEN_FINDING_STATUS]
    assert len(open_findings) == 1
    assert open_findings[0].name == "Validation methodology not documented"
