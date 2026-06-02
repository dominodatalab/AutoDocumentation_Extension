"""Read-only client for the Domino rai-guardrails-service governance API.

All paths are relative to /api/governance/v1/ on the same Domino host as the
rest of the API. Authentication is handled by domino_client._domino_request.
"""

from __future__ import annotations

import logging
from typing import Any, List, Optional

from domino_client import _domino_request
from autodoc.core.models import (
    ArtifactResult,
    BundleAttachment,
    BundleSummary,
    ComputedPolicy,
    GovernanceFinding,
)

logger = logging.getLogger(__name__)

_BASE = "/api/governance/v1"


def _parse_attachment(raw: dict[str, Any]) -> BundleAttachment:
    return BundleAttachment(
        id=str(raw.get("id", "")),
        type=str(raw.get("type", "")),
        identifier=raw.get("identifier") or {},
    )


def _parse_bundle(raw: dict[str, Any]) -> BundleSummary:
    attachments = [
        _parse_attachment(a)
        for a in (raw.get("attachments") or [])
        if isinstance(a, dict)
    ]
    return BundleSummary(
        id=str(raw.get("id", "")),
        name=str(raw.get("name", "")),
        project_id=str(raw.get("projectId", "")),
        policy_id=str(raw.get("policyId", "")),
        policy_name=str(raw.get("policyName", "")),
        state=str(raw.get("state", "")),
        evidence_restricted=bool(raw.get("evidenceRestricted", False)),
        stage=raw.get("stage") or None,
        classification_value=raw.get("classificationValue") or None,
        attachments=attachments,
        created_at=raw.get("createdAt") or None,
    )


def _parse_finding(raw: dict[str, Any]) -> GovernanceFinding:
    assignee_obj = raw.get("assignee") or {}
    approver_obj = raw.get("approver") or {}
    return GovernanceFinding(
        id=str(raw.get("id", "")),
        bundle_id=str(raw.get("bundleId", "")),
        name=str(raw.get("name", "")),
        severity=str(raw.get("severity", "")),
        status=str(raw.get("status", "")),
        description=raw.get("description") or None,
        assignee=assignee_obj.get("name") if isinstance(assignee_obj, dict) else None,
        approver=approver_obj.get("name") if isinstance(approver_obj, dict) else None,
        due_date=raw.get("dueDate") or None,
    )


def _parse_result(raw: dict[str, Any]) -> ArtifactResult:
    return ArtifactResult(
        id=str(raw.get("id", "")),
        evidence_id=str(raw.get("evidenceId", "")),
        bundle_id=str(raw.get("bundleId", "")),
        artifact_id=str(raw.get("artifactId", "")),
        artifact_content=raw.get("artifactContent"),
        is_latest=bool(raw.get("isLatest", False)),
    )


def list_bundles(project_id: str) -> List[BundleSummary]:
    """Return all bundles for a project."""
    try:
        data = _domino_request(
            "GET",
            f"{_BASE}/bundles",
            params={"projectId[]": project_id},
        )
        items = data.get("data") if isinstance(data, dict) else data
        if not isinstance(items, list):
            return []
        return [_parse_bundle(b) for b in items if isinstance(b, dict)]
    except Exception:
        logger.exception("list_bundles failed for project %s", project_id)
        return []


def get_bundle(bundle_id: str) -> Optional[BundleSummary]:
    """Return bundle metadata for the given bundle ID."""
    try:
        raw = _domino_request("GET", f"{_BASE}/bundles/{bundle_id}")
        if not isinstance(raw, dict):
            return None
        return _parse_bundle(raw)
    except Exception:
        logger.exception("get_bundle failed for bundle %s", bundle_id)
        return None


def compute_policy(bundle_id: str, policy_id: str) -> Optional[ComputedPolicy]:
    """Call POST /rpc/compute-policy and return the result.

    Returns both the policy definition (stages/evidences/artifacts = question text)
    and the submitted answers (results). Single call, no separate evidence-template
    lookups needed. Confirmed by SME 2026-05-29.
    """
    try:
        raw = _domino_request(
            "POST",
            f"{_BASE}/rpc/compute-policy",
            json={"bundleId": bundle_id, "policyId": policy_id},
        )
        if not isinstance(raw, dict):
            return None

        bundle_raw = raw.get("bundle") or {}
        policy_raw = raw.get("policy") or {}

        bundle = _parse_bundle(bundle_raw)

        stages: list[dict[str, Any]] = []
        for stage in (policy_raw.get("stages") or []):
            if isinstance(stage, dict):
                stages.append(stage)

        results = [
            _parse_result(r)
            for r in (raw.get("results") or [])
            if isinstance(r, dict)
        ]
        # Only use submitted/latest results for evidence Q&A.
        results = [r for r in results if r.is_latest]

        return ComputedPolicy(
            bundle=bundle,
            policy_id=str(policy_raw.get("id", "")),
            policy_name=str(policy_raw.get("name", "")),
            policy_stages=stages,
            results=results,
        )
    except Exception:
        logger.exception("compute_policy failed for bundle %s policy %s", bundle_id, policy_id)
        return None


def get_findings(bundle_id: str) -> List[GovernanceFinding]:
    """Return all findings for a bundle."""
    try:
        data = _domino_request("GET", f"{_BASE}/bundles/{bundle_id}/findings")
        items = data if isinstance(data, list) else (data.get("data") if isinstance(data, dict) else [])
        if not isinstance(items, list):
            return []
        return [_parse_finding(f) for f in items if isinstance(f, dict)]
    except Exception:
        logger.exception("get_findings failed for bundle %s", bundle_id)
        return []
