"""Tests for governance evidence formatting (B1)."""

from __future__ import annotations

from autodoc.core.models import EvidenceItem, Finding, GovernanceContext
from autodoc.generation.citations import build_evidence_citation_id, build_finding_citation_id
from autodoc.generation.generator import ContentGenerator
from autodoc.llm import LLMClient
from unittest.mock import MagicMock


def _sample_context() -> GovernanceContext:
    return GovernanceContext(
        bundle_id="bundle-1",
        bundle_name="Churn Model Bundle",
        policy_name="Credit Risk Policy",
        stage="Stage 1",
        state="Active",
        risk_tier="High",
        evidence=[
            EvidenceItem(
                artifact_id="art-1",
                question="Was the model validated on a hold-out dataset?",
                answer="Yes",
                evidence_set_name="Model Training",
                stage="Stage 1",
                citation_id=build_evidence_citation_id(
                    "Was the model validated on a hold-out dataset?"
                ),
            ),
            EvidenceItem(
                artifact_id="art-2",
                question="Describe the validation methodology.",
                answer="Stratified 80/20 split.",
                evidence_set_name="Model Training",
                stage="Stage 1",
                citation_id=build_evidence_citation_id("Describe the validation methodology."),
            ),
        ],
        findings=[
            Finding(
                finding_id="find-1",
                title="Validation methodology not documented",
                description="Hold-out characteristics missing.",
                severity="S2",
                status="To do",
            )
        ],
        governed_model_names=["churn-model", "churn-model-v2"],
    )


class TestFormatGovernanceEvidence:
    def test_empty_when_no_context(self):
        gen = ContentGenerator(MagicMock(spec=LLMClient))
        assert gen._format_governance_evidence(None) == ""

    def test_expected_block_shape(self):
        gen = ContentGenerator(MagicMock(spec=LLMClient))
        block = gen._format_governance_evidence(_sample_context())
        assert "## Governance Evidence" in block
        assert "[@governance.bundle]: Churn Model Bundle" in block
        assert "[@governance.risk_tier]: High" in block
        assert "[@governance.model_of_record]: churn-model, churn-model-v2" in block
        assert "Evidence — Stage 1 / Model Training" in block
        assert "hold-out dataset" in block
        assert f"[@{build_finding_citation_id('find-1')}]" in block
        assert "Findings (To do):" in block

    def test_over_budget_omits_evidence_with_notice(self):
        gen = ContentGenerator(MagicMock(spec=LLMClient))
        items = []
        for i in range(30):
            items.append(
                EvidenceItem(
                    artifact_id=f"art-{i}",
                    question=f"Question number {i} about validation step?",
                    answer="x" * 500,
                    evidence_set_name="Set",
                    stage="Stage 1",
                    answered_at=f"2026-01-{i+1:02d}T00:00:00Z",
                    citation_id=build_evidence_citation_id(f"Question number {i}"),
                )
            )
        ctx = GovernanceContext(
            bundle_id="b",
            bundle_name="Bundle",
            policy_name="Policy",
            risk_tier="High",
            evidence=items,
            findings=[
                Finding(
                    finding_id="f-keep",
                    title="Must remain",
                    status="To do",
                )
            ],
        )
        block = gen._format_governance_evidence(ctx, token_budget=200)
        assert "evidence items omitted to fit token budget" in block
        assert "[@governance.risk_tier]: High" in block
        assert "[@finding.f-keep]" in block
