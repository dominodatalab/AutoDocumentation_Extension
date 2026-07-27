from __future__ import annotations

import os
import sys

_repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_pkg_dir = os.path.join(_repo_root, "auto_model_docs")
for p in (_repo_root, _pkg_dir):
    if p not in sys.path:
        sys.path.insert(0, p)

from job_failure_hints import classify_job_failure_log, failure_hint_dict


def test_classify_missing_anthropic_api_key():
    log = "Error: AUTODOC_ANTHROPIC_API_KEY or ANTHROPIC_API_KEY not set"
    hint = classify_job_failure_log(log)
    assert hint is not None
    assert hint.headline == "LLM API key not configured"
    assert "administrator" in hint.detail.lower()


def test_classify_missing_openai_api_key():
    log = "OPENAI_API_KEY not set"
    hint = classify_job_failure_log(log)
    assert hint is not None
    assert hint.headline == "LLM API key not configured"


def test_classify_missing_domino_project_id():
    hint = classify_job_failure_log("Error: DOMINO_PROJECT_ID is required. Set it to your Domino project ID.")
    assert hint is not None
    assert hint.headline == "Project configuration missing"
    assert "DOMINO_PROJECT_ID" in hint.detail


def test_classify_governance_host_missing():
    log = "Error: DOMINO_USER_HOST or DOMINO_API_PROXY is required to load governance context"
    hint = classify_job_failure_log(log)
    assert hint is not None
    assert hint.headline == "Governance access not configured"


def test_classify_governance_bundle_not_found():
    log = "Error: Bundle abc123 not found in project proj-1"
    hint = classify_job_failure_log(log)
    assert hint is not None
    assert hint.headline == "Governance bundle not available"


def test_classify_governance_compute_policy_failed():
    log = "Error: compute-policy failed for bundle abc123 policy pol-1"
    hint = classify_job_failure_log(log)
    assert hint is not None
    assert hint.headline == "Governance bundle could not be loaded"


def test_classify_unknown_error_returns_none():
    assert classify_job_failure_log("Error: Code scanning failed: boom") is None
    assert failure_hint_dict("") is None


def test_failure_hint_dict_shape():
    hint = failure_hint_dict("OPENAI_API_KEY not set")
    assert hint == {
        "headline": "LLM API key not configured",
        "message": (
            "The documentation job could not run because no LLM API key was found "
            "for the selected provider."
        ),
        "detail": (
            "Ask your Domino administrator to add ANTHROPIC_API_KEY or OPENAI_API_KEY "
            "to the extension compute environment."
        ),
    }
