"""Tests for governance HTTP in domino_client."""

from __future__ import annotations

import os
import sys
from unittest.mock import patch

import pytest

_repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_pkg_dir = os.path.join(_repo_root, "auto_model_docs")
for p in (_repo_root, _pkg_dir):
    if p not in sys.path:
        sys.path.insert(0, p)

import domino_client as dc
from domino_client import compute_policy, get_findings, list_bundles


@pytest.fixture(autouse=True)
def _env(monkeypatch):
    monkeypatch.setenv("DOMINO_USER_HOST", "http://nucleus-frontend.domino-platform:80")
    monkeypatch.setenv("DOMINO_API_HOST", "https://domino.example.com")
    monkeypatch.setenv("DOMINO_USER_API_KEY", "test-key")


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


class TestParseGovernanceAttachment:
    def test_parses_fields(self):
        result = dc._parse_governance_attachment(_ATTACHMENT)
        assert result.id == "att-1"
        assert result.type == "ModelVersion"
        assert result.identifier == {"name": "churn-model", "version": 3}

    def test_missing_identifier_defaults_to_empty_dict(self):
        result = dc._parse_governance_attachment({"id": "x", "type": "App"})
        assert result.identifier == {}


class TestParseGovernanceBundle:
    def test_parses_all_fields(self):
        b = dc._parse_governance_bundle(_BUNDLE)
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
        b = dc._parse_governance_bundle(raw)
        assert b.stage is None
        assert b.classification_value is None
        assert b.created_at is None


class TestParseGovernanceFinding:
    def test_parses_all_fields(self):
        f = dc._parse_governance_finding(_FINDING)
        assert f.id == "finding-1"
        assert f.bundle_id == "bundle-abc"
        assert f.name == "Missing data source documentation"
        assert f.severity == "S2"
        assert f.status == "To do"
        assert f.assignee == "Alice"
        assert f.approver == "Bob"


class TestParseGovernanceResult:
    def test_parses_all_fields(self):
        r = dc._parse_governance_result(_RESULT)
        assert r.id == "result-1"
        assert r.evidence_id == "ev-1"
        assert r.artifact_content == {"value": "Yes"}
        assert r.is_latest is True

    def test_filters_non_latest_in_compute_policy(self):
        stale = dict(_RESULT, id="result-2", isLatest=False)
        raw = dict(_COMPUTED_POLICY, results=[_RESULT, stale])
        with patch.object(dc, "_governance_request", return_value=raw):
            result = compute_policy("bundle-abc", "policy-xyz")
        assert result is not None
        assert len(result.results) == 1
        assert result.results[0].id == "result-1"


class TestListBundles:
    def test_returns_bundles_from_data_key(self):
        with patch.object(dc, "_governance_request", return_value={"data": [_BUNDLE]}) as m:
            result = list_bundles("proj-123")
        m.assert_called_once_with(
            "GET",
            "/api/governance/v1/bundles",
            params={"projectId[]": "proj-123", "offset": 0, "limit": 25},
        )
        assert len(result) == 1
        assert result[0].id == "bundle-abc"

    def test_returns_bundles_from_list_response(self):
        with patch.object(dc, "_governance_request", return_value=[_BUNDLE]):
            result = list_bundles("proj-123")
        assert len(result) == 1

    def test_returns_empty_on_api_error(self):
        with patch.object(dc, "_governance_request", side_effect=RuntimeError("boom")):
            result = list_bundles("proj-123")
        assert result == []

    def test_paginates_until_exhausted(self):
        page1 = {
            "data": [dict(_BUNDLE, id="bundle-1")],
            "meta": {"pagination": {"offset": 0, "limit": 1, "totalCount": 2}},
        }
        page2 = {
            "data": [dict(_BUNDLE, id="bundle-2")],
            "meta": {"pagination": {"offset": 1, "limit": 1, "totalCount": 2}},
        }
        with patch.object(dc, "_governance_request", side_effect=[page1, page2]) as m:
            result = list_bundles("proj-123")
        assert m.call_count == 2
        assert [b.id for b in result] == ["bundle-1", "bundle-2"]
        assert m.call_args_list[1].kwargs["params"]["offset"] == 1


class TestComputePolicy:
    def test_returns_computed_policy(self):
        with patch.object(dc, "_governance_request", return_value=_COMPUTED_POLICY) as m:
            result = compute_policy("bundle-abc", "policy-xyz")
        m.assert_called_once_with(
            "POST",
            "/api/governance/v1/rpc/compute-policy",
            json={"bundleId": "bundle-abc", "policyId": "policy-xyz"},
        )
        assert result is not None
        assert result.policy_id == "policy-xyz"
        assert result.bundle.id == "bundle-abc"

    def test_returns_none_on_error(self):
        with patch.object(dc, "_governance_request", side_effect=RuntimeError("boom")):
            result = compute_policy("bundle-abc", "policy-xyz")
        assert result is None


class TestGetFindings:
    def test_returns_findings_from_list(self):
        with patch.object(dc, "_governance_request", return_value=[_FINDING]) as m:
            result = get_findings("bundle-abc")
        m.assert_called_once_with("GET", "/api/governance/v1/bundles/bundle-abc/findings")
        assert len(result) == 1
        assert result[0].name == "Missing data source documentation"

    def test_returns_findings_from_data_key(self):
        with patch.object(dc, "_governance_request", return_value={"data": [_FINDING]}):
            result = get_findings("bundle-abc")
        assert len(result) == 1

    def test_returns_empty_on_error(self):
        with patch.object(dc, "_governance_request", side_effect=RuntimeError("boom")):
            result = get_findings("bundle-abc")
        assert result == []


class TestGovernanceHostResolution:
    def test_uses_user_host_not_proxy(self, monkeypatch):
        monkeypatch.setenv("DOMINO_API_PROXY", "http://localhost:8899")
        monkeypatch.setenv("DOMINO_USER_HOST", "http://nucleus-frontend.domino-platform:80")
        monkeypatch.setenv("DOMINO_USER_API_KEY", "test-key")
        with patch.object(dc, "_domino_request", return_value={"data": [_BUNDLE]}) as m:
            list_bundles("proj-123")
        assert m.call_args.kwargs["base_url"] == "http://nucleus-frontend.domino-platform:80"
