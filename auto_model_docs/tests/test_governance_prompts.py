from autodoc.core.models import EvidenceItem, Finding, GovernanceContext
from autodoc.generation.citations import build_evidence_citation_id
from autodoc.generation.generator import ContentGenerator
from autodoc.llm.prompts import (
    GOVERNANCE_ANTI_FABRICATION,
    GOVERNANCE_SYSTEM_NOTE,
    SYSTEM_NARRATIVE_WRITER,
    build_chart_prompt,
    build_list_prompt,
    build_narrative_prompt,
    build_section_planning_prompt,
    build_table_prompt,
    narrative_system_prompt,
)
from unittest.mock import MagicMock


def _governance_block() -> str:
    ctx = GovernanceContext(
        bundle_id="bundle-1",
        bundle_name="Churn Bundle",
        policy_name="Credit Risk Policy",
        risk_tier="High",
        evidence=[
            EvidenceItem(
                artifact_id="a1",
                question="Was the model validated?",
                answer="Yes",
                citation_id=build_evidence_citation_id("Was the model validated?"),
            )
        ],
        findings=[
            Finding(
                finding_id="f1",
                title="Missing docs",
                severity="S2",
                status="To do",
            )
        ],
    )
    return ContentGenerator(MagicMock())._format_governance_evidence(ctx)


class TestGovernancePrompts:
    def test_narrative_without_governance_unchanged_instructions(self):
        prompt = build_narrative_prompt(
            section_name="Overview",
            purpose="Summarize",
            data_needed=None,
            model_classes="XGB",
            ml_task_type="classification",
            target_variable="y",
            features="a,b",
            data_sources="csv",
            model_name=None,
            model_info="",
            insights="",
        )
        assert GOVERNANCE_ANTI_FABRICATION not in prompt
        assert narrative_system_prompt("") == SYSTEM_NARRATIVE_WRITER

    def test_narrative_with_governance_includes_clause(self):
        gov = _governance_block()
        prompt = build_narrative_prompt(
            section_name="Overview",
            purpose="Summarize",
            data_needed=None,
            model_classes="XGB",
            ml_task_type="classification",
            target_variable="y",
            features="a,b",
            data_sources="csv",
            model_name=None,
            model_info="",
            insights="",
            governance_evidence=gov,
        )
        assert GOVERNANCE_ANTI_FABRICATION in prompt
        assert "Governance Evidence" in prompt
        assert GOVERNANCE_SYSTEM_NOTE in narrative_system_prompt(gov)

    def test_table_chart_list_include_clause_when_block_set(self):
        gov = _governance_block()
        table = build_table_prompt(
            purpose="metrics",
            data_needed=None,
            features="a",
            model_classes="XGB",
            transformations="",
            hyperparameters="",
            governance_evidence=gov,
        )
        chart = build_chart_prompt(
            purpose="metrics",
            data_needed=None,
            chart_type="bar",
            model_classes="XGB",
            ml_task_type="classification",
            governance_evidence=gov,
        )
        lst = build_list_prompt(
            purpose="limits",
            data_needed=None,
            model_classes="XGB",
            ml_task_type="classification",
            features="a",
            governance_evidence=gov,
        )
        for prompt in (table, chart, lst):
            assert GOVERNANCE_ANTI_FABRICATION in prompt

    def test_planning_prompt_includes_governance_block(self):
        gov = _governance_block()
        prompt = build_section_planning_prompt(
            section_name="Validation",
            hint=None,
            model_name=None,
            model_classes="XGB",
            ml_task_type="classification",
            features_preview="a,b",
            target_variable="y",
            registered_models="m1",
            data_sources="csv",
            governance_evidence=gov,
        )
        assert "Governance Evidence" in prompt

    def test_anti_fabrication_distinguishes_model_of_record_from_candidates(self):
        assert "[@governance.model_of_record]" in GOVERNANCE_ANTI_FABRICATION
        assert "development candidates" in GOVERNANCE_ANTI_FABRICATION
        assert "development history" in GOVERNANCE_SYSTEM_NOTE.lower()
