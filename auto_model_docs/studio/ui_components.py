"""FastHTML UI component helpers for Model Docs Studio."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

from fasthtml.common import *

from domino_job_store import job_db_not_configured_msg

from .state import (
    DominoJobRecord,
    EnvironmentWarning,
    _get_default_code_root,
    _max_jobs,
)


# ---------------------------------------------------------------------------
# Sanitizers / parsers
# ---------------------------------------------------------------------------

def format_project_context_label(value: Optional[str]) -> str:
    if not value:
        return ""
    parts = [part.strip() for part in value.split("/") if part.strip()]
    if len(parts) <= 1:
        return value.strip()
    return " / ".join(parts)


def _sanitize_optional_int(value: Optional[str]) -> Optional[int]:
    if value is None or value == "":
        return None
    try:
        return int(value)
    except (ValueError, TypeError):
        return None


def _sanitize_optional_float(value: Optional[str]) -> Optional[float]:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (ValueError, TypeError):
        return None


def _db_record_to_dataclass(row: dict) -> DominoJobRecord:
    return DominoJobRecord(
        id=row["id"],
        owner_id=row["owner_id"],
        domino_run_id=row.get("domino_run_id"),
        hardware_tier=row.get("hardware_tier"),
        status=row.get("status", "queued"),
        domino_status=row.get("domino_status"),
        job_url=row.get("job_url"),
        dataset_id=row.get("dataset_id"),
        spec_path=row.get("spec_path"),
        submitted_at=row.get("submitted_at"),
        completed_at=row.get("completed_at"),
        project_id=row.get("project_id"),
    )


# ---------------------------------------------------------------------------
# Environment validation
# ---------------------------------------------------------------------------

def _validate_environment() -> list:
    """Validate environment and return warnings. Never raises."""
    warnings = []
    code_root = _get_default_code_root()

    # Check code directory
    if not code_root.exists() or code_root == Path("."):
        warnings.append(EnvironmentWarning(
            level="warning",
            message="Code directory not found.",
            action="Documents will be generated from MLflow artifacts only.",
        ))

    # Check MLflow
    if not os.environ.get("MLFLOW_TRACKING_URI"):
        warnings.append(EnvironmentWarning(
            level="info",
            message="MLflow not configured.",
            action="Document generation will use code analysis only.",
        ))

    if not os.environ.get("DOMINO_API_HOST"):
        warnings.append(EnvironmentWarning(
            level="warning",
            message="Domino API host not configured.",
            action="Job submission may fail.",
        ))

    # Output and cache are managed via DatasetStore — no local directories needed.

    return warnings


def validate_studio_domino_compute_environment(domino_client_mod: Any) -> list[str]:
    """Return non-empty list of user-facing lines if the app cannot use the configured compute environment."""
    eid = (os.environ.get("DOMINO_ENVIRONMENT_ID") or "").strip()
    rid = (os.environ.get("DOMINO_ENVIRONMENT_REVISION_ID") or "").strip()
    if not eid or not rid:
        return [
            "This app is missing required configuration.",
            "Please contact your administrator to finish setup.",
        ]
    try:
        revs = domino_client_mod.list_environment_revisions(eid) or []
    except Exception:
        return [
            "We could not verify your run environment right now.",
            "Please try again in a few minutes, or contact your administrator if this continues.",
        ]
    rev_ids: set[str] = set()
    for r in revs:
        if isinstance(r, dict) and r.get("id") is not None:
            rev_ids.add(str(r["id"]))
    if rid not in rev_ids:
        return [
            "Your account cannot use the run environment configured for this app.",
            "Please contact your administrator to fix access or update the configuration.",
        ]
    return []


def studio_job_store_config_error() -> tuple[str, str, str] | None:
    missing = job_db_not_configured_msg()
    if not missing:
        return None
    if "DOMINO_DATASETS_DIR" in missing:
        return (
            "Job history not configured",
            "This app requires DOMINO_DATASETS_DIR so job history can be stored on a Domino dataset mount.",
            "If you're running this as a Domino App, contact your administrator to configure the app environment.",
        )
    return (
        "Job history not configured",
        "This app requires DOMINO_PROJECT_NAME so job history can be stored for this deployment.",
        "If you're running this as a Domino App, contact your administrator to configure the app environment.",
    )


def render_studio_bootstrap_error_page(
    heading: str,
    message: str,
    detail: str,
) -> tuple:
    import pathlib

    from studio.styles import STUDIO_CSS

    logo_svg = (pathlib.Path(__file__).resolve().parent.parent.parent / "domino-logo.svg").read_text()
    return (
        Title("Model Docs — Domino"),
        Style(STUDIO_CSS),
        Div(Div(NotStr(logo_svg), cls="domino-header-inner"), cls="domino-header"),
        Div(
            Div(
                Div(
                    H2(heading),
                    P(message),
                    P(detail, cls="bootstrap-error-detail"),
                    cls="bootstrap-error-card",
                ),
                cls="bootstrap-error-wrap",
            ),
            cls="page",
        ),
    )


# ---------------------------------------------------------------------------
# Form field helpers
# ---------------------------------------------------------------------------

def _field_id(name: str) -> str:
    return f"field-{name}"


def _labeled_input(label_text: str, name: str, **kwargs: str) -> FT:
    return Div(
        Label(label_text, for_=_field_id(name)),
        Input(name=name, id=_field_id(name), **kwargs),
        cls="field",
    )


def _labeled_select(label_text: str, name: str, *options: FT) -> FT:
    return Div(
        Label(label_text, for_=_field_id(name)),
        Select(*options, name=name, id=_field_id(name)),
        cls="field",
    )


def _checkbox_field(label_text: str, name: str) -> FT:
    return Div(
        Label(
            Input(type="checkbox", name=name, id=_field_id(name)),
            Span(label_text),
            cls="checkbox",
        ),
        cls="field",
    )


# ---------------------------------------------------------------------------
# Warnings banner
# ---------------------------------------------------------------------------

def _render_warnings_banner(warnings: list) -> list:
    """Render environment warnings as dismissible HTML banners."""
    if not warnings:
        return []
    banners = []
    style_map = {
        "info": "warning-banner warning-banner-info",
        "warning": "warning-banner warning-banner-warning",
        "error": "warning-banner warning-banner-error",
    }
    for w in warnings:
        style = style_map.get(w.level, style_map["info"])
        banners.append(
            Div(
                Span(f"{w.message} {w.action}", cls="warning-banner-message"),
                Button(
                    Span("close", cls="material-symbols-outlined"),
                    type="button",
                    cls="warning-banner-close",
                    aria_label="Dismiss",
                    onclick="this.parentElement.remove();",
                ),
                cls=style,
            )
        )
    return banners


# ---------------------------------------------------------------------------
# Status panels
# ---------------------------------------------------------------------------

def _render_domino_status(record: Optional[DominoJobRecord]) -> FT:
    """Render the terminal panel for a documentation job."""
    if not record:
        return Div(
            Div(
                H3("Documentation job"),
                cls="terminal-header",
            ),
            Div(
                "Click Generate Documentation to start.",
                cls="terminal terminal-idle",
            ),
            cls="terminal-card",
            data_job_status="idle",
        )

    status = record.status
    badge_cls = f"terminal-status terminal-status-{status}"

    # Job link
    job_link = None
    if record.job_url:
        job_link = A(
            "View job in UI \u2192",
            href=record.job_url,
            target="_blank",
            cls="domino-job-link",
        )

    # Queue-full explanation for queued jobs
    queue_banner = None
    if status == "queued" and not record.domino_run_id:
        max_j = _max_jobs()
        queue_banner = Div(
            Span("\u26a0 "),
            Span(f"Job queued \u2014 you already have {max_j} active job{'s' if max_j != 1 else ''}. "
                 "It will start automatically when a slot opens. To free a slot: stop a running job above, "
                 "or switch to the History tab and use "),
            Span("Cancel queued", cls="spec-selected-value"),
            Span(" to remove pending jobs."),
            cls="inline-callout inline-callout-warning",
            role="alert",
        )

    # Status message
    status_lines = []
    if record.submitted_at:
        status_lines.append(f"Submitted: {record.submitted_at[:19].replace('T', ' ')} UTC")
    if record.domino_status:
        status_lines.append(f"Domino status: {record.domino_status}")
    if record.completed_at:
        status_lines.append(f"Completed: {record.completed_at[:19].replace('T', ' ')} UTC")
    if not status_lines:
        if status == "queued" and not record.domino_run_id:
            status_lines.append("Waiting for a slot to open...")
        else:
            status_lines.append("Waiting for status...")

    status_text = "\n".join(status_lines)

    return Div(
        Div(
            H3("Documentation job"),
            cls="terminal-header",
        ),
        Div(status.upper(), cls=badge_cls),
        queue_banner,
        Div(job_link, cls="domino-job-link-row") if job_link else None,
        Pre(status_text, cls="terminal"),
        id="domino-status-inner",
        cls="terminal-card",
        data_job_status=status,
    )


