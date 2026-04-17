"""Governance API fixtures and modelId attachment matching."""

from __future__ import annotations

import json
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

from domino_auth import cli_auth, configure_auth
import domino_client
from domino_client import compute_policy, get_findings, list_bundles

FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures" / "governance"
PROJECT_ID = "aaaaaaaa-bbbb-cccc-dddd-000000000001"
PRIMARY_MODEL_ID = "fraud-detector-v1"
PRIMARY_BUNDLE_ID = "7f746bd1-3c88-4d89-97d0-9eba1bfb38b0"
SHARED_MODEL_ID = "churn-predictor-v1"
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
    configure_auth(cli_auth)
    monkeypatch.setenv("DOMINO_API_HOST", "https://domino.example.com")
    monkeypatch.setenv("DOMINO_USER_API_KEY", "test-key")


def test_fixture_files_exist():
    for name in (
        "bundles-list.json",
        "bundle-computed-policy.json",
        "findings-open.json",
    ):
        assert (FIXTURES_DIR / name).is_file()


def test_list_bundles_fixture_parses():
    payload = _load("bundles-list.json")
    with patch.object(domino_client, "_governance_request", return_value=payload):
        bundles = list_bundles(PROJECT_ID, api_host="https://domino.example.com")
    assert len(bundles) == 5
    assert bundles[0].id == PRIMARY_BUNDLE_ID
    assert bundles[0].attachments[0].identifier["name"] == PRIMARY_MODEL_ID


def test_model_id_matches_single_bundle():
    payload = _load("bundles-list.json")
    matched = bundles_for_model_id(payload, PRIMARY_MODEL_ID)
    assert len(matched) == 1
    assert matched[0]["id"] == PRIMARY_BUNDLE_ID


def test_model_id_matches_two_bundles_for_shared_model():
    payload = _load("bundles-list.json")
    matched = bundles_for_model_id(payload, SHARED_MODEL_ID)
    assert len(matched) == 2
    ids = {b["id"] for b in matched}
    assert ids == {
        "b2222222-2222-2222-2222-222222222201",
        "b2222222-2222-2222-2222-222222222202",
    }


def test_compute_policy_fixture_latest_results_only():
    payload = _load("bundle-computed-policy.json")
    with patch.object(domino_client, "_governance_request", return_value=payload):
        computed = compute_policy(
            PRIMARY_BUNDLE_ID,
            "a1111111-1111-1111-1111-111111111101",
            api_host="https://domino.example.com",
        )
    assert computed is not None
    assert computed.bundle.name == "fraud-detector-v1-governance-bundle"
    assert len(computed.results) == 2
    assert all(r.is_latest for r in computed.results)
    assert computed.results[0].artifact_content == {"value": "Yes"}


def test_findings_fixture_open_status_api_string():
    payload = _load("findings-open.json")
    with patch.object(domino_client, "_governance_request", return_value=payload):
        findings = get_findings(PRIMARY_BUNDLE_ID, api_host="https://domino.example.com")
    assert len(findings) == 2
    statuses = {f.status for f in findings}
    assert OPEN_FINDING_STATUS in statuses
    assert "Done" in statuses
    open_findings = [f for f in findings if f.status == OPEN_FINDING_STATUS]
    assert len(open_findings) == 1
    assert open_findings[0].name == "Validation methodology not documented"
