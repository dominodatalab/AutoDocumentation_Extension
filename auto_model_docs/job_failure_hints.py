from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True)
class JobFailureHint:
    headline: str
    message: str
    detail: str

    def as_dict(self) -> dict[str, str]:
        return asdict(self)


def classify_job_failure_log(log_text: str) -> JobFailureHint | None:
    text = log_text or ""
    lower = text.lower()

    if ("anthropic_api_key" in lower or "openai_api_key" in lower) and "not set" in lower:
        return JobFailureHint(
            headline="LLM API key not configured",
            message=(
                "The documentation job could not run because no LLM API key was found "
                "for the selected provider."
            ),
            detail=(
                "Ask your Domino administrator to add ANTHROPIC_API_KEY or OPENAI_API_KEY "
                "to the extension compute environment."
            ),
        )

    if "domino_project_id is required" in lower:
        return JobFailureHint(
            headline="Project configuration missing",
            message="The documentation job could not determine which Domino project to use.",
            detail=(
                "Ask your Domino administrator to ensure DOMINO_PROJECT_ID is available "
                "in the job environment."
            ),
        )

    if "domino_user_host or domino_api_proxy is required to load governance" in lower:
        return JobFailureHint(
            headline="Governance access not configured",
            message="The job could not reach Domino Governance.",
            detail=(
                "Ask your Domino administrator to complete extension setup for "
                "Governance API access."
            ),
        )

    if "bundle " in lower and "not found in project" in lower:
        return JobFailureHint(
            headline="Governance bundle not available",
            message="The selected governance bundle could not be loaded in this project.",
            detail=(
                "Choose a different bundle, or ask your project owner to confirm you have "
                "access to Governance in this project."
            ),
        )

    if "compute-policy failed for bundle" in lower:
        return JobFailureHint(
            headline="Governance bundle could not be loaded",
            message="Domino could not evaluate the policy for the selected governance bundle.",
            detail=(
                "Try another bundle, or ask your Domino administrator if Governance is "
                "configured correctly."
            ),
        )

    return None


def failure_hint_dict(log_text: str) -> dict[str, Any] | None:
    hint = classify_job_failure_log(log_text)
    return hint.as_dict() if hint else None
