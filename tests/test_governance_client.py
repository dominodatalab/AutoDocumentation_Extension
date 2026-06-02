"""Tests for governance_client — read-only wrappers around the rai-guardrails-service API.

All tests mock _domino_request so no live API is needed.
"""

from __future__ import annotations

import os
import sys
from typing import Any
from unittest.mock import patch

import pytest

_repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_pkg_dir = os.path.join(_repo_root, "auto_model_docs")
for p in (_repo_root, _pkg_dir):
    if p not in sys.path:
        sys.path.insert(0, p)

import governance_client as gc
from governance_client import (
    list_bundles,
    get_bundle,
    compute_policy,
    get_findings,
)
from autodoc.core.models import (
    ArtifactResult,
    BundleAttachment,
    BundleSummary,
    ComputedPolicy,
    GovernanceFinding,
)


@pytest.fixture(autouse=True)
def _env(monkeypatch):
    monkeypatch.setenv("DOMINO_API_HOST", "https://domino.example.com")
    monkeypatch.setenv("DOMINO_USER_API_KEY", "test-key")


# ---------------------------------------------------------------------------
# Fixtures: sample API payloads
# ---------------------------------------------------------------------------

_ATTACHMENT = {
    "id": "att-1",
    "type": "ModelVersion",
    "identifier": {"name": "churn-model", "version": 3},
    "source": "DFS",
}

_BUNDLE = {
    "id": "bundle-abc",
    "name": "Churn Bundle",
    "projectId": "proj-123",
    "policyId": "policy-xyz",
    "policyName": "Credit Risk Policy",
    "state": "Active",
    "evidenceRestricted": False,
    "stage": "Stage 1",
    "classificationValue": "High",
    "attachments": [_ATTACHMENT],
    "createdAt": "2026-01-01T00:00:00Z",
}

_FINDING = {
    "id": "finding-1",
    "bundleId": "bundle-abc",
    "name": "Missing data source documentation",
    "severity": "S2",
    "status": "To do",
    "description": "The data source is not documented.",
    "assignee": {"id": "user-1", "name": "Alice"},
    "approver": {"id": "user-2", "name": "Bob"},
    "dueDate": "2026-06-30T00:00:00Z",
}

_RESULT = {
    "id": "result-1",
    "evidenceId": "ev-1",
    "bundleId": "bundle-abc",
    "artifactId": "art-1",
    "artifactContent": {"value": "Yes"},
    "isLatest": True,
}

_POLICY = {
    "id": "policy-xyz",
    "name": "Credit Risk Policy",
    "stages": [
        {
            "id": "stage-1",
            "name": "Stage 1",
            "evidenceSet": [
                {
                    "id": "ev-1",
                    "name": "Model Training",
                    "artifacts": [
                        {
                            "id": "art-1",
                            "artifactType": "input",
                            "details": {"text": "Was the model validated?", "type": "Radio"},
                        }
                    ],
                }
            ],
        }
    ],
}

_COMPUTED_POLICY = {
    "bundle": _BUNDLE,
    "policy": _POLICY,
    "results": [_RESULT],
    "drafts": [],
    "findingsInfo": {"bundleFindingsCount": 1, "artifactFindingsCountMap": {}},
    "approvals": [],
    "bundleStages": [],
    "isUserApprover": False,
    "commentsInfo": {"bundleCommentsCount": 0},
}


# ---------------------------------------------------------------------------
# _parse_attachment
# ---------------------------------------------------------------------------

class TestParseAttachment:
    def test_parses_fields(self):
        result = gc._parse_attachment(_ATTACHMENT)
        assert result.id == "att-1"
        assert result.type == "ModelVersion"
        assert result.identifier == {"name": "churn-model", "version": 3}

    def test_missing_identifier_defaults_to_empty_dict(self):
        result = gc._parse_attachment({"id": "x", "type": "App"})
        assert result.identifier == {}

    def test_missing_fields_default_to_empty_string(self):
        result = gc._parse_attachment({})
        assert result.id == ""
        assert result.type == ""


# ---------------------------------------------------------------------------
# _parse_bundle
# ---------------------------------------------------------------------------

class TestParseBundle:
    def test_parses_all_fields(self):
        b = gc._parse_bundle(_BUNDLE)
        assert b.id == "bundle-abc"
        assert b.name == "Churn Bundle"
        assert b.project_id == "proj-123"
        assert b.policy_id == "policy-xyz"
        assert b.policy_name == "Credit Risk Policy"
        assert b.state == "Active"
        assert b.evidence_restricted is False
        assert b.stage == "Stage 1"
        assert b.classification_value == "High"
        assert b.created_at == "2026-01-01T00:00:00Z"
        assert len(b.attachments) == 1
        assert b.attachments[0].type == "ModelVersion"

    def test_null_optional_fields_become_none(self):
        raw = dict(_BUNDLE)
        raw["stage"] = None
        raw["classificationValue"] = None
        raw["createdAt"] = None
        b = gc._parse_bundle(raw)
        assert b.stage is None
        assert b.classification_value is None
        assert b.created_at is None

    def test_missing_attachments_defaults_to_empty(self):
        raw = {k: v for k, v in _BUNDLE.items() if k != "attachments"}
        b = gc._parse_bundle(raw)
        assert b.attachments == []


# ---------------------------------------------------------------------------
# _parse_finding
# ---------------------------------------------------------------------------

class TestParseFinding:
    def test_parses_all_fields(self):
        f = gc._parse_finding(_FINDING)
        assert f.id == "finding-1"
        assert f.bundle_id == "bundle-abc"
        assert f.name == "Missing data source documentation"
        assert f.severity == "S2"
        assert f.status == "To do"
        assert f.description == "The data source is not documented."
        assert f.assignee == "Alice"
        assert f.approver == "Bob"
        assert f.due_date == "2026-06-30T00:00:00Z"

    def test_null_assignee_approver(self):
        raw = dict(_FINDING, assignee=None, approver=None)
        f = gc._parse_finding(raw)
        assert f.assignee is None
        assert f.approver is None

    def test_missing_description_is_none(self):
        raw = {k: v for k, v in _FINDING.items() if k != "description"}
        f = gc._parse_finding(raw)
        assert f.description is None


# ---------------------------------------------------------------------------
# _parse_result
# ---------------------------------------------------------------------------

class TestParseResult:
    def test_parses_all_fields(self):
        r = gc._parse_result(_RESULT)
        assert r.id == "result-1"
        assert r.evidence_id == "ev-1"
        assert r.bundle_id == "bundle-abc"
        assert r.artifact_id == "art-1"
        assert r.artifact_content == {"value": "Yes"}
        assert r.is_latest is True

    def test_is_latest_defaults_false(self):
        raw = {k: v for k, v in _RESULT.items() if k != "isLatest"}
        r = gc._parse_result(raw)
        assert r.is_latest is False


# ---------------------------------------------------------------------------
# list_bundles
# ---------------------------------------------------------------------------

class TestListBundles:
    def test_returns_bundles_from_data_key(self):
        with patch.object(gc, "_domino_request", return_value={"data": [_BUNDLE]}) as m:
            result = list_bundles("proj-123")
        m.assert_called_once_with("GET", "/api/governance/v1/bundles", params={"projectId[]": "proj-123"})
        assert len(result) == 1
        assert result[0].id == "bundle-abc"

    def test_returns_bundles_from_list_response(self):
        with patch.object(gc, "_domino_request", return_value=[_BUNDLE]):
            result = list_bundles("proj-123")
        assert len(result) == 1

    def test_returns_empty_on_api_error(self):
        with patch.object(gc, "_domino_request", side_effect=RuntimeError("boom")):
            result = list_bundles("proj-123")
        assert result == []

    def test_returns_empty_on_empty_data(self):
        with patch.object(gc, "_domino_request", return_value={"data": []}):
            result = list_bundles("proj-123")
        assert result == []

    def test_skips_non_dict_items(self):
        with patch.object(gc, "_domino_request", return_value={"data": [_BUNDLE, "bad", None]}):
            result = list_bundles("proj-123")
        assert len(result) == 1


# ---------------------------------------------------------------------------
# get_bundle
# ---------------------------------------------------------------------------

class TestGetBundle:
    def test_returns_bundle(self):
        with patch.object(gc, "_domino_request", return_value=_BUNDLE) as m:
            result = get_bundle("bundle-abc")
        m.assert_called_once_with("GET", "/api/governance/v1/bundles/bundle-abc")
        assert result is not None
        assert result.id == "bundle-abc"

    def test_returns_none_on_error(self):
        with patch.object(gc, "_domino_request", side_effect=RuntimeError("not found")):
            result = get_bundle("bundle-abc")
        assert result is None

    def test_returns_none_on_non_dict_response(self):
        with patch.object(gc, "_domino_request", return_value=[]):
            result = get_bundle("bundle-abc")
        assert result is None


# ---------------------------------------------------------------------------
# compute_policy
# ---------------------------------------------------------------------------

class TestComputePolicy:
    def test_returns_computed_policy(self):
        with patch.object(gc, "_domino_request", return_value=_COMPUTED_POLICY) as m:
            result = compute_policy("bundle-abc", "policy-xyz")
        m.assert_called_once_with(
            "POST",
            "/api/governance/v1/rpc/compute-policy",
            json={"bundleId": "bundle-abc", "policyId": "policy-xyz"},
        )
        assert result is not None
        assert result.policy_id == "policy-xyz"
        assert result.policy_name == "Credit Risk Policy"
        assert result.bundle.id == "bundle-abc"

    def test_parses_results(self):
        with patch.object(gc, "_domino_request", return_value=_COMPUTED_POLICY):
            result = compute_policy("bundle-abc", "policy-xyz")
        assert len(result.results) == 1
        assert result.results[0].artifact_content == {"value": "Yes"}

    def test_parses_policy_stages(self):
        with patch.object(gc, "_domino_request", return_value=_COMPUTED_POLICY):
            result = compute_policy("bundle-abc", "policy-xyz")
        assert len(result.policy_stages) == 1
        assert result.policy_stages[0]["name"] == "Stage 1"

    def test_returns_none_on_error(self):
        with patch.object(gc, "_domino_request", side_effect=RuntimeError("boom")):
            result = compute_policy("bundle-abc", "policy-xyz")
        assert result is None

    def test_returns_none_on_non_dict_response(self):
        with patch.object(gc, "_domino_request", return_value="unexpected"):
            result = compute_policy("bundle-abc", "policy-xyz")
        assert result is None

    def test_empty_results_allowed(self):
        raw = dict(_COMPUTED_POLICY, results=[])
        with patch.object(gc, "_domino_request", return_value=raw):
            result = compute_policy("bundle-abc", "policy-xyz")
        assert result is not None
        assert result.results == []


# ---------------------------------------------------------------------------
# get_findings
# ---------------------------------------------------------------------------

class TestGetFindings:
    def test_returns_findings_from_list(self):
        with patch.object(gc, "_domino_request", return_value=[_FINDING]) as m:
            result = get_findings("bundle-abc")
        m.assert_called_once_with("GET", "/api/governance/v1/bundles/bundle-abc/findings")
        assert len(result) == 1
        assert result[0].name == "Missing data source documentation"

    def test_returns_findings_from_data_key(self):
        with patch.object(gc, "_domino_request", return_value={"data": [_FINDING]}):
            result = get_findings("bundle-abc")
        assert len(result) == 1

    def test_returns_empty_on_error(self):
        with patch.object(gc, "_domino_request", side_effect=RuntimeError("boom")):
            result = get_findings("bundle-abc")
        assert result == []

    def test_returns_empty_on_empty_list(self):
        with patch.object(gc, "_domino_request", return_value=[]):
            result = get_findings("bundle-abc")
        assert result == []

    def test_skips_non_dict_items(self):
        with patch.object(gc, "_domino_request", return_value=[_FINDING, "junk", 42]):
            result = get_findings("bundle-abc")
        assert len(result) == 1
