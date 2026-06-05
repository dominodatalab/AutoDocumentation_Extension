"""Load governance bundle context for document generation."""

from __future__ import annotations

import logging
import os
from typing import Any, Optional

from autodoc.core.models import (
    ComputedPolicy,
    EvidenceItem,
    Finding,
    GovernanceContext,
    GovernanceFinding,
)
from domino_client import compute_policy, get_findings, list_bundles

logger = logging.getLogger(__name__)

OPEN_FINDING_STATUS = "To do"


class GovernanceLoadError(Exception):
    pass


def _normalize_answer(artifact_content: Any) -> str:
    if artifact_content is None:
        return ""
    if isinstance(artifact_content, dict) and "value" in artifact_content:
        return str(artifact_content["value"])
    return str(artifact_content)


def _extract_evidence_items(computed: ComputedPolicy) -> list[EvidenceItem]:
    from autodoc.generation.citations import build_evidence_citation_id

    results_by_key: dict[tuple[str, str], Any] = {}
    for result in computed.results:
        if result.is_latest:
            results_by_key[(str(result.evidence_id), str(result.artifact_id))] = result

    used_slugs: set[str] = set()
    items: list[EvidenceItem] = []
    for stage in computed.policy_stages or []:
        stage_name = stage.get("name") if isinstance(stage, dict) else None
        for evidence in (stage.get("evidenceSet") or []) if isinstance(stage, dict) else []:
            if not isinstance(evidence, dict):
                continue
            ev_id = str(evidence.get("id", ""))
            ev_name = evidence.get("name")
            for artifact in evidence.get("artifacts") or []:
                if not isinstance(artifact, dict):
                    continue
                if str(artifact.get("artifactType", "")).lower() != "input":
                    continue
                art_id = str(artifact.get("id", ""))
                question = (artifact.get("details") or {}).get("text", "")
                if not question:
                    continue
                result = results_by_key.get((ev_id, art_id))
                if result is None:
                    continue
                answer = _normalize_answer(result.artifact_content)
                if not answer:
                    continue
                citation_id = build_evidence_citation_id(str(question), used_slugs)
                items.append(
                    EvidenceItem(
                        artifact_id=art_id,
                        question=str(question),
                        answer=answer,
                        evidence_set_name=str(ev_name) if ev_name else None,
                        stage=str(stage_name) if stage_name else None,
                        answered_at=None,
                        citation_id=citation_id,
                    )
                )
    return items


def _finding_from_api(raw: GovernanceFinding, artifact_label: Optional[str] = None) -> Finding:
    return Finding(
        finding_id=str(raw.id),
        title=str(raw.name),
        description=str(raw.description or ""),
        severity=str(raw.severity) if raw.severity else None,
        status=str(raw.status),
        artifact_label=artifact_label,
    )


def _bundle_owner(bundle_row) -> Optional[str]:
    owner = getattr(bundle_row, "owner_username", None) or None
    if owner:
        return str(owner)
    project_owner = getattr(bundle_row, "project_owner", None) or None
    if project_owner:
        return str(project_owner)
    return None


def _filter_findings(
    findings: list[GovernanceFinding],
    findings_scope: str,
) -> list[Finding]:
    scope = (findings_scope or "open").strip().lower()
    result: list[Finding] = []
    for raw in findings:
        if scope == "open" and raw.status != OPEN_FINDING_STATUS:
            continue
        result.append(_finding_from_api(raw))
    return result


def load_governance_context(
    bundle_id: str,
    *,
    api_host: str,
    findings_scope: str = "open",
    project_id: Optional[str] = None,
) -> GovernanceContext:
    bundle_id = (bundle_id or "").strip()
    if not bundle_id:
        raise GovernanceLoadError("bundle_id is required")

    pid = (project_id or os.environ.get("DOMINO_PROJECT_ID") or "").strip()
    if not pid:
        raise GovernanceLoadError("DOMINO_PROJECT_ID is required to load governance context")

    host = (api_host or "").strip()
    if not host:
        raise GovernanceLoadError("governance api host is required")

    logger.info("Loading governance context for bundle %s", bundle_id)

    bundles = list_bundles(pid, api_host=host)
    bundle_row = next((b for b in bundles if str(b.id) == bundle_id), None)
    if bundle_row is None:
        raise GovernanceLoadError(f"Bundle {bundle_id} not found in project {pid}")

    computed = compute_policy(bundle_id, str(bundle_row.policy_id), api_host=host)
    if computed is None:
        raise GovernanceLoadError(
            f"compute-policy failed for bundle {bundle_id} policy {bundle_row.policy_id}"
        )

    raw_findings = get_findings(bundle_id, api_host=host)
    evidence = _extract_evidence_items(computed)
    findings = _filter_findings(raw_findings, findings_scope)

    bundle = computed.bundle
    return GovernanceContext(
        bundle_id=bundle_id,
        bundle_name=bundle.name or bundle_row.name,
        policy_name=computed.policy_name or bundle_row.policy_name,
        stage=bundle.stage or bundle_row.stage,
        state=bundle.state or bundle_row.state,
        risk_tier=bundle.classification_value or bundle_row.classification_value,
        owner=_bundle_owner(bundle_row),
        evidence=evidence,
        findings=findings,
    )
