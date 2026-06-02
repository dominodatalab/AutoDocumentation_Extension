from autodoc.core.models import (
    ArtifactResult,
    BundleSummary,
    ComputedPolicy,
    GovernanceFinding,
)
from autodoc.llm.prompts import (
    GOVERNANCE_SYSTEM_SUFFIX,
    build_narrative_prompt,
    format_artifact_answer,
    format_governance_context,
    system_prompt_with_governance,
    SYSTEM_NARRATIVE_WRITER,
)


def _bundle_summary() -> BundleSummary:
    return BundleSummary(
        id="bundle-1",
        name="Churn Model Bundle",
        project_id="proj-1",
        policy_id="policy-1",
        policy_name="Credit Risk Policy",
        state="Active",
        evidence_restricted=False,
        stage="Stage 1",
        classification_value="High",
    )


def _computed_policy() -> ComputedPolicy:
    return ComputedPolicy(
        bundle=_bundle_summary(),
        policy_id="policy-1",
        policy_name="Credit Risk Policy",
        policy_stages=[
            {
                "name": "Stage 1",
                "evidenceSet": [
                    {
                        "id": "ev-1",
                        "name": "Validation",
                        "artifacts": [
                            {
                                "id": "art-1",
                                "artifactType": "input",
                                "details": {"text": "Was the model validated?"},
                            },
                            {
                                "id": "art-2",
                                "artifactType": "file",
                                "details": {"text": "ignored"},
                            },
                        ],
                    }
                ],
            }
        ],
        results=[
            ArtifactResult(
                id="r-1",
                evidence_id="ev-1",
                bundle_id="bundle-1",
                artifact_id="art-1",
                artifact_content={"value": "Yes"},
                is_latest=True,
            )
        ],
        findings=[
            GovernanceFinding(
                id="f-1",
                bundle_id="bundle-1",
                name="Missing docs",
                severity="S2",
                status="To do",
                description="Needs write-up",
            )
        ],
    )


class TestFormatArtifactAnswer:
    def test_value_key(self):
        assert format_artifact_answer({"value": "Yes"}) == "Yes"

    def test_plain_string(self):
        assert format_artifact_answer("raw") == "raw"


class TestFormatGovernanceContext:
    def test_empty(self):
        assert format_governance_context([]) == ""

    def test_includes_qa_and_findings(self):
        text = format_governance_context([_computed_policy()])
        assert "Governance & Compliance Context" in text
        assert "Churn Model Bundle" in text
        assert "Was the model validated?" in text
        assert "**A**: Yes" in text
        assert "[S2] Missing docs" in text
        assert "ignored" not in text

    def test_narrative_prompt_includes_governance(self):
        gov = format_governance_context([_computed_policy()])
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
        assert "Governance & Compliance Context" in prompt
        assert "## Instructions" in prompt
        assert prompt.index("Governance") < prompt.index("## Instructions")


class TestSystemPromptWithGovernance:
    def test_unchanged_without_governance(self):
        assert system_prompt_with_governance(SYSTEM_NARRATIVE_WRITER, []) == (
            SYSTEM_NARRATIVE_WRITER
        )

    def test_appends_suffix_with_governance(self):
        system = system_prompt_with_governance(
            SYSTEM_NARRATIVE_WRITER, [_computed_policy()]
        )
        assert system.startswith(SYSTEM_NARRATIVE_WRITER)
        assert GOVERNANCE_SYSTEM_SUFFIX in system
