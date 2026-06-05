"""Tests for governance citation display and notebook re-export recovery."""

from __future__ import annotations

from autodoc.generation.citations import (
    CitationRegistry,
    build_evidence_citation_id,
    build_finding_citation_id,
    build_governance_citation_id,
    citation_details_meta_comment,
    format_governance_display_label,
    format_governance_reference_text,
    parse_citation_details_meta_comment,
    replace_markers_with_ids,
)
from autodoc.generation.notebook_exporter import NotebookExporter


BUNDLE_ID = "7f746bd1-3c88-4d89-97d0-9eba1bfb38b0"
BUNDLE_NAME = "mlflow3-logged-and-registered1-governance-bundle"
POLICY_NAME = "autodoc-ml-governance-policy"


def _gov_base() -> dict:
    return {
        "bundle_id": BUNDLE_ID,
        "bundle_name": BUNDLE_NAME,
        "policy_name": POLICY_NAME,
    }


class TestGovernanceCitationFormatting:
    def test_reference_text_for_governance_field(self):
        cid = build_governance_citation_id("risk_tier")
        details = {
            **_gov_base(),
            "type": "governance",
            "source_key": "risk_tier",
            "evidence_text": "Medium",
        }
        text = format_governance_reference_text(cid, details)
        assert BUNDLE_NAME in text
        assert BUNDLE_ID in text
        assert POLICY_NAME in text
        assert "Risk tier: Medium" in text

    def test_display_label_for_governance_field(self):
        cid = build_governance_citation_id("stage")
        details = {
            **_gov_base(),
            "type": "governance",
            "source_key": "stage",
            "evidence_text": "Stage 1",
        }
        label = format_governance_display_label(cid, details)
        assert label == f"{BUNDLE_NAME} · Stage"

    def test_reference_text_for_evidence(self):
        cid = build_evidence_citation_id("Was the model validated on a hold-out dataset?")
        details = {
            **_gov_base(),
            "type": "evidence",
            "source_key": cid.split(".", 1)[-1],
            "evidence_text": 'Was the model validated on a hold-out dataset? — "Yes"',
            "evidence_stage": "Stage 1",
            "evidence_set_name": "Model validation",
        }
        text = format_governance_reference_text(cid, details)
        assert BUNDLE_NAME in text
        assert "Stage 1 / Model validation" in text
        assert "hold-out dataset" in text

    def test_reference_text_for_finding(self):
        cid = build_finding_citation_id("find-1")
        details = {
            **_gov_base(),
            "type": "finding",
            "source_key": "find-1",
            "finding_title": "Validation methodology not documented",
            "finding_description": "Hold-out characteristics missing.",
            "finding_severity": "S2",
            "finding_status": "To do",
        }
        text = format_governance_reference_text(cid, details)
        assert BUNDLE_NAME in text
        assert "[S2]" in text
        assert "Validation methodology not documented" in text

    def test_registry_entry_uses_bundle_context(self):
        reg = CitationRegistry()
        cid = build_governance_citation_id("risk_tier")
        reg.register(
            cid,
            {
                **_gov_base(),
                "type": "governance",
                "source_key": "risk_tier",
                "evidence_text": "Medium",
            },
        )
        entry = reg.get_entry(cid)
        assert entry is not None
        assert BUNDLE_NAME in entry.text
        assert entry.display_label == f"{BUNDLE_NAME} · Risk tier"

    def test_inline_markers_use_display_label(self):
        reg = CitationRegistry()
        cid = build_governance_citation_id("risk_tier")
        details = {
            **_gov_base(),
            "type": "governance",
            "source_key": "risk_tier",
            "evidence_text": "Medium",
        }
        rendered, _ = replace_markers_with_ids(
            f"Risk level [@{cid}]",
            reg,
            details_map={cid: details},
            markdown=True,
        )
        assert f"[{BUNDLE_NAME} · Risk tier](#ref-{cid})" in rendered
        assert f"<!-- @cite:{cid} -->" in rendered


class TestNotebookReferencesRecovery:
    def test_parse_references_cell_recovers_governance_meta(self):
        cid = build_governance_citation_id("risk_tier")
        meta = citation_details_meta_comment(
            {
                "type": "governance",
                "source_key": "risk_tier",
                "bundle_id": BUNDLE_ID,
                "bundle_name": BUNDLE_NAME,
                "policy_name": POLICY_NAME,
                "evidence_text": "Medium",
            }
        )
        cell = "\n".join(
            [
                "## References",
                "",
                (
                    f'**[1]** {cid} | {BUNDLE_NAME} ({BUNDLE_ID}) | Risk tier: Medium '
                    f"<!-- @cite:{cid}{meta} -->"
                ),
            ]
        )
        exporter = NotebookExporter()
        recovered = exporter._parse_references_cell(cell)
        assert cid in recovered
        assert recovered[cid]["bundle_id"] == BUNDLE_ID
        assert recovered[cid]["bundle_name"] == BUNDLE_NAME
        assert recovered[cid]["evidence_text"] == "Medium"

    def test_parse_meta_comment_round_trip(self):
        payload = {
            "type": "evidence",
            "bundle_id": BUNDLE_ID,
            "bundle_name": BUNDLE_NAME,
            "evidence_text": "Q — A",
        }
        meta = citation_details_meta_comment(payload)
        line = f"<!-- @cite:evidence.foo{meta} -->"
        parsed = parse_citation_details_meta_comment(line)
        assert parsed["bundle_id"] == BUNDLE_ID
        assert parsed["type"] == "evidence"
