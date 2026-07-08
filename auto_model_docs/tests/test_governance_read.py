"""Tests for autodoc/governance_read.py."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

_repo_root = Path(__file__).resolve().parents[2]
_pkg_dir = _repo_root / "auto_model_docs"
for p in (str(_repo_root), str(_pkg_dir)):
    if p not in sys.path:
        sys.path.insert(0, p)

from autodoc.core.models import (
    ArtifactResult,
    BundleAttachment,
    BundleSummary,
    ComputedPolicy,
    GovernanceFinding,
)
from autodoc.governance_read import (
    GovernanceLoadError,
    load_governance_context,
    merge_scan_model_names,
)

FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures" / "governance"
PROJECT_ID = "aaaaaaaa-bbbb-cccc-dddd-000000000001"
BUNDLE_ID = "7f746bd1-3c88-4d89-97d0-9eba1bfb38b0"
POLICY_ID = "a1111111-1111-1111-1111-111111111101"


def _load(name: str):
    with (FIXTURES_DIR / name).open(encoding="utf-8") as f:
        return json.load(f)


def _bundle_summary(*, attachments=None) -> BundleSummary:
    raw = _load("bundle-computed-policy.json")["bundle"]
    return BundleSummary(
        id=raw["id"],
        name=raw["name"],
        project_id=raw["projectId"],
        policy_id=raw["policyId"],
        policy_name=raw["policyName"],
        state=raw["state"],
        evidence_restricted=raw.get("evidenceRestricted", False),
        stage=raw.get("stage"),
        classification_value=raw.get("classificationValue"),
        attachments=attachments or [],
        created_at=raw.get("createdAt"),
        owner_username="demo-user",
        owner_display_name="Demo User",
        project_owner="demo-user",
    )


def _computed_policy() -> ComputedPolicy:
    payload = _load("bundle-computed-policy.json")
    bundle = _bundle_summary()
    results = [
        ArtifactResult(
            id=r["id"],
            evidence_id=r["evidenceId"],
            bundle_id=r["bundleId"],
            artifact_id=r["artifactId"],
            artifact_content=r.get("artifactContent"),
            is_latest=bool(r.get("isLatest")),
        )
        for r in payload.get("results") or []
        if r.get("isLatest")
    ]
    return ComputedPolicy(
        bundle=bundle,
        policy_id=payload["policy"]["id"],
        policy_name=payload["policy"]["name"],
        policy_stages=payload["policy"]["stages"],
        results=results,
    )


def _bundle_summary_from_list_fixture() -> BundleSummary:
    raw = _load("bundles-list.json")["data"][0]
    attachments = [
        BundleAttachment(
            id=a["id"],
            type=a["type"],
            identifier=a["identifier"],
        )
        for a in raw.get("attachments") or []
    ]
    created_by = raw.get("createdBy") or {}
    return BundleSummary(
        id=raw["id"],
        name=raw["name"],
        project_id=raw["projectId"],
        policy_id=raw["policyId"],
        policy_name=raw["policyName"],
        state=raw["state"],
        evidence_restricted=raw.get("evidenceRestricted", False),
        stage=raw.get("stage"),
        classification_value=raw.get("classificationValue"),
        attachments=attachments,
        created_at=raw.get("createdAt"),
        owner_username=created_by.get("userName"),
        owner_display_name=f"{created_by.get('firstName', '')} {created_by.get('lastName', '')}".strip(),
        project_owner=raw.get("projectOwner"),
    )


def _findings_raw():
    return [
        GovernanceFinding(
            id=f["id"],
            bundle_id=f["bundleId"],
            name=f["name"],
            severity=f["severity"],
            status=f["status"],
            description=f.get("description"),
        )
        for f in _load("findings-open.json").get("data") or []
    ]


@pytest.fixture(autouse=True)
def _env(monkeypatch):
    monkeypatch.setenv("DOMINO_USER_HOST", "https://domino.example.com")
    monkeypatch.setenv("DOMINO_USER_API_KEY", "test-key")
    monkeypatch.setenv("DOMINO_PROJECT_ID", PROJECT_ID)


class TestLoadGovernanceContext:
    def test_loads_from_fixtures_open_findings_only(self):
        with patch("autodoc.governance_read.list_bundles", return_value=[_bundle_summary()]), patch(
            "autodoc.governance_read.compute_policy", return_value=_computed_policy()
        ), patch("autodoc.governance_read.get_findings", return_value=_findings_raw()):
            ctx = load_governance_context(
                BUNDLE_ID, api_host="https://domino.example.com", findings_scope="open"
            )

        assert ctx.bundle_id == BUNDLE_ID
        assert ctx.owner == "Demo User"
        assert ctx.risk_tier == "Medium"
        assert len(ctx.evidence) == 2
        assert ctx.evidence[0].citation_id.startswith("evidence.")
        assert len(ctx.findings) == 1
        assert ctx.findings[0].status == "To do"

    def test_all_findings_scope(self):
        with patch("autodoc.governance_read.list_bundles", return_value=[_bundle_summary()]), patch(
            "autodoc.governance_read.compute_policy", return_value=_computed_policy()
        ), patch("autodoc.governance_read.get_findings", return_value=_findings_raw()):
            ctx = load_governance_context(
                BUNDLE_ID, api_host="https://domino.example.com", findings_scope="all"
            )
        assert len(ctx.findings) == 2

    def test_missing_bundle_raises(self):
        with patch("autodoc.governance_read.list_bundles", return_value=[]):
            with pytest.raises(GovernanceLoadError):
                load_governance_context(BUNDLE_ID, api_host="https://domino.example.com")

    def test_compute_policy_failure_raises(self):
        with patch("autodoc.governance_read.list_bundles", return_value=[_bundle_summary()]), patch(
            "autodoc.governance_read.compute_policy", return_value=None
        ):
            with pytest.raises(GovernanceLoadError):
                load_governance_context(BUNDLE_ID, api_host="https://domino.example.com")

    def test_governed_model_names_from_model_version_attachments(self):
        bundle = _bundle_summary_from_list_fixture()
        with patch("autodoc.governance_read.list_bundles", return_value=[bundle]), patch(
            "autodoc.governance_read.compute_policy", return_value=_computed_policy()
        ), patch("autodoc.governance_read.get_findings", return_value=_findings_raw()):
            ctx = load_governance_context(
                BUNDLE_ID, api_host="https://domino.example.com", findings_scope="open"
            )
        assert ctx.governed_model_names == ["fraud-detector-v1"]

    def test_use_user_host_skips_explicit_api_host(self, monkeypatch):
        monkeypatch.setenv("DOMINO_USER_HOST", "http://127.0.0.1:8763")
        with patch("autodoc.governance_read.list_bundles", return_value=[_bundle_summary()]) as mock_list, patch(
            "autodoc.governance_read.compute_policy", return_value=_computed_policy()
        ) as mock_compute, patch(
            "autodoc.governance_read.get_findings", return_value=_findings_raw()
        ) as mock_findings:
            ctx = load_governance_context(BUNDLE_ID, use_user_host=True, findings_scope="open")

        assert ctx.bundle_id == BUNDLE_ID
        mock_list.assert_called_once_with(PROJECT_ID, use_user_host=True)
        mock_compute.assert_called_once()
        assert mock_compute.call_args.kwargs == {"use_user_host": True}
        mock_findings.assert_called_once_with(BUNDLE_ID, use_user_host=True)


class TestMergeScanModelNames:
    def test_returns_filtered_when_no_governed(self):
        assert merge_scan_model_names(["a", "b"], []) == ["a", "b"]

    def test_returns_governed_when_no_filter(self):
        assert merge_scan_model_names(None, ["g1", "g2"]) == ["g1", "g2"]

    def test_unions_governed_not_in_filter(self):
        assert merge_scan_model_names(["filtered"], ["governed"]) == [
            "filtered",
            "governed",
        ]

    def test_deduplicates_overlap(self):
        assert merge_scan_model_names(["same", "other"], ["same"]) == ["same", "other"]
