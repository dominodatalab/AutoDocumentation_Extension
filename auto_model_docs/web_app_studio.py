#!/usr/bin/env python3
"""FastHTML UI for Auto Model Documentation — Blueprint Enterprise redesign.

This is the slim orchestrator that imports from the studio package and
assembles the application.
"""

from __future__ import annotations

import json
import os
import pathlib
from typing import Optional

from fasthtml.common import *
from starlette.requests import Request

from domino_auth import configure_auth, user_auth

configure_auth(user_auth)

# Inline SVG logo — white paths, designed for dark backgrounds
_LOGO_SVG = (pathlib.Path(__file__).parent.parent / "domino-logo.svg").read_text()

from default_consts import DEFAULT_OPENAI_MODEL

from studio.state import (
    _STARTUP_WARNINGS,
    _resolve_request_project_id,
    domino_client,
)
from studio.styles import STUDIO_CSS
from studio.scripts import MAIN_DOM_JS
from studio.ui_components import (
    _render_warnings_banner,
    _validate_environment,
    validate_studio_domino_compute_environment,
)
from studio.font_assets import (
    STUDIO_FONT_BASE_PATCH_JS,
    fontawesome_faces_css,
    register_font_assets,
)
from studio.routes_api import register_api_routes
from studio.routes_job import register_job_routes

from domino_job_store import ensure_database


# ---------------------------------------------------------------------------
# Create FastHTML app with styles and scripts
# ---------------------------------------------------------------------------

app, rt = fast_app(
    pico=False,
    hdrs=(
        Style(STUDIO_CSS),
        # NOTE: output defaults script is injected per-request in index()
        # so it picks up the resolved target project name.
        Script(MAIN_DOM_JS),
    )
)

ensure_database()


# ---------------------------------------------------------------------------
# index() — Blueprint Enterprise 3-Column Layout
# ---------------------------------------------------------------------------

@rt("/")
async def index(req: Request):
    host = req.headers.get("x-forwarded-host") or req.headers.get("host") or ""
    scheme = req.headers.get("x-forwarded-proto", "https")
    domino_client.set_ui_host(host, scheme)

    # projectId query param is required. Domino's reverse proxy may strip query params
    # from the iframe URL, so if it's missing we serve a bootstrap page whose JS
    # extracts the ID from the parent frame, hash fragment, or postMessage and reloads.
    project_id = _resolve_request_project_id(req)
    if not project_id:
        return (
            Title("Auto Model Docs Studio — Domino"),
            Style(fontawesome_faces_css()),
            Script(STUDIO_FONT_BASE_PATCH_JS),
            Style(STUDIO_CSS),
            Script(r"""
                (function() {
                    var pid = null;

                    if (window.location.hash) {
                        var h = window.location.hash.substring(1);
                        if (h.charAt(0) === '?') h = h.substring(1);
                        pid = new URLSearchParams(h).get('projectId');
                    }

                    if (!pid && window.parent !== window) {
                        try {
                            var pLoc = window.parent.location;
                            pid = new URLSearchParams(pLoc.search).get('projectId');
                            if (!pid && pLoc.hash) {
                                var ph = pLoc.hash.substring(1);
                                if (ph.charAt(0) === '?') ph = ph.substring(1);
                                pid = new URLSearchParams(ph).get('projectId');
                            }
                        } catch(e) { /* cross-origin */ }
                    }

                    if (!pid && document.referrer) {
                        try {
                            pid = new URL(document.referrer).searchParams.get('projectId');
                        } catch(e) {}
                    }

                    if (pid) {
                        var url = new URL(window.location.href);
                        url.searchParams.set('projectId', pid);
                        window.location.replace(url.toString());
                        return;
                    }

                    var allowedOrigin = window.location.origin;
                    window.addEventListener('message', function(e) {
                        if (e.origin !== allowedOrigin) return;
                        if (e.data && typeof e.data === 'object' && e.data.projectId) {
                            var url = new URL(window.location.href);
                            url.searchParams.set('projectId', e.data.projectId);
                            window.location.replace(url.toString());
                        }
                    });

                    setTimeout(function() {
                        var el = document.getElementById('project-id-error');
                        if (el) el.style.display = '';
                    }, 2000);
                })();
            """),
            Div(
                Div(
                    NotStr(_LOGO_SVG),
                    cls="domino-header-inner",
                ),
                cls="domino-header",
            ),
            Div(
                Div(
                    Div(
                        Span("Resolving project...", cls="bootstrap-status-text"),
                    ),
                    cls="bootstrap-status-wrap",
                ),
                Div(
                    Div(
                        H2("Project ID required"),
                        P(
                            "This app must be launched with a ",
                            Code("projectId"),
                            " query parameter so it knows which project to run jobs in, "
                            "store spec files to, and write output to.",
                        ),
                        P(
                            "If you're running this as a Domino App, make sure the app is "
                            "configured to pass the project ID to the iframe URL.",
                            cls="bootstrap-error-detail",
                        ),
                        cls="bootstrap-error-card",
                    ),
                    id="project-id-error",
                    cls="bootstrap-error-wrap",
                    style="display: none;",
                ),
                cls="page",
            ),
        )

    project_display_name: Optional[str] = None
    if project_id:
        info = domino_client.resolve_project(project_id)
        if info:
            project_display_name = f"{info.owner_username}/{info.name}"

    try:
        from autodoc.core.config import Settings as _StudioSettings
        _ss = _StudioSettings()
        _default_openai_base_url = _ss.openai_base_url or "https://api.openai.com/v1"
        _default_anthropic_base_url = _ss.anthropic_base_url or "https://api.anthropic.com"
    except Exception:
        _default_openai_base_url = "https://api.openai.com/v1"
        _default_anthropic_base_url = "https://api.anthropic.com"
    import auth_context
    try:
        owner_id = auth_context.get_viewing_user().id
    except Exception:
        owner_id = ""
    tier_options = []
    try:
        tier_rows = domino_client.list_hardware_tiers(project_id=project_id) or []
        default_tier = domino_client.get_project_default_tier()
        for t in tier_rows:
            tid = t.get("id", "")
            label = t.get("option_label") or t.get("name") or tid
            is_default = t.get("isDefault", False) or tid == default_tier
            tier_options.append(Option(label, value=tid, selected=is_default))
    except Exception:
        tier_options = []
    if not tier_options:
        tier_options = [Option("(default)", value="")]

    compute_env_errors = validate_studio_domino_compute_environment(domino_client)
    studio_errors_panel = Div(id="studio-errors-panel", cls="studio-errors-panel")
    _insight_children = [
        Div(
            H3("How it works"),
            P(
                "Select a spec file to define your documentation structure, configure project settings, "
                "then click Generate documentation. Auto Model Docs scans your codebase and MLflow "
                "experiments to produce a structured Word document.",
            ),
            cls="insight-card",
        ),
        studio_errors_panel,
    ]
    if compute_env_errors:
        _insight_children.append(
            Script(
                json.dumps(compute_env_errors),
                id="studio-compute-env-json",
                type="application/json",
            )
        )

    # LEFT COLUMN: What to document
    left_col_children = [
        Div(
            H2("Documentation specification"),
            Span("Step 1", cls="step-badge"),
            cls="col-header",
        ),
    ]

    # Spec file card
    spec_card_children = []

    # Dataset browser + upload
    spec_card_children.append(
        Div(
            H3("Spec file selection"),
            P("To browse for spec files, select a dataset and a spec file in the navigator below.", cls="field-hint-text"),
            A(
                "Download reference template",
                href="api/download-template",
                data_app_rel="api/download-template",
                download="doc_spec_template.yaml",
                cls="app-link",
            ),
            Hr(cls="section-divider"),
            Div(
                Label("Dataset", Span(" *", cls="required-star")),
                Select(
                    Option("Loading datasets...", value="", disabled=True, selected=True),
                    id="spec-dataset-select",
                ),
                cls="field",
            ),
            Div(id="spec-breadcrumb", cls="spec-breadcrumb"),           
            Div(
                Div(
                    Span(cls="fa-icon fa-folder-open spec-file-empty-icon"),
                    Span("Select a dataset to browse spec files", cls="spec-file-list-empty"),
                    cls="spec-file-empty",
                ),
                id="spec-file-list",
                cls="spec-file-list",
            ),
            Div(
                Span("Selected:", cls="spec-selected-label"),
                Input(
                    name="spec_path",
                    id="field-spec_path",
                    type="text",
                    value="",
                    placeholder="Select a file, upload, or type a path",
                    autocomplete="off",
                    spellcheck="false",
                    cls="spec-path-input",
                ),
                id="spec-selected-indicator",
                cls="spec-selected-indicator",
            ),
            Div(
                Label(
                    "Upload spec",
                    Input(
                        type="file",
                        accept=".yaml,.yml",
                        id="spec-machine-upload",
                        cls="hidden-upload",
                    ),
                    cls="primary",
                ),
                cls="spec-upload-footer",
            ),
            Details(
                Summary("Filters", cls="advanced-section-summary"),
                Div(
                    Div(
                        Div(
                            Label("Model names", for_="field-filtered_model_names"),
                            Span("\u24d8", cls="info-tooltip", data_tooltip="Comma-separated. Supports wildcards: * and ?"),
                            cls="label-row",
                        ),
                        Input(
                            name="filtered_model_names",
                            id="field-filtered_model_names",
                            type="text",
                            placeholder="model1, churn*, fraud-*",
                        ),
                        cls="field",
                    ),
                    Div(
                        Div(
                            Label("Experiment names", for_="field-filtered_experiment_names"),
                            Span("\u24d8", cls="info-tooltip", data_tooltip="Comma-separated. Supports wildcards: * and ?"),
                            cls="label-row",
                        ),
                        Input(
                            name="filtered_experiment_names",
                            id="field-filtered_experiment_names",
                            type="text",
                            placeholder="exp1, exp2, my-experiment*",
                        ),
                        cls="field",
                    ),
                    Label(
                        Input(type="checkbox", name="latest_only", id="field-latest_only", checked=True),
                        Span("Latest version only"),
                        cls="checkbox-field",
                    ),
                    cls="advanced-content",
                ),
                cls="advanced-section",
                open=False,
            ),
            cls="field",
        )
    )

    left_col_children.append(Div(*spec_card_children, cls="bp-card"))

    # MIDDLE COLUMN: Configuration & Run
    mid_col_children = [
        Div(
            H2("Configure and run"),
            Span("Step 2", cls="step-badge"),
            cls="col-header",
        ),
    ]

    # Run settings card
    run_card_children = []

    run_card_children.append(
        Div(
            H3(
                Span("Target project: ", cls="target-project-label-prefix"),
                Span(
                    project_display_name or project_id or "",
                    cls="target-project-display",
                ),
                cls="target-project-row",
            ),
            cls="field target-project-callout",
        )
    )

    run_card_children.append(
        Div(
            Label("Source code root path", for_="code-root-prefix"),
            Div(
                Select(
                    Option("Loading...", value="", selected=True, disabled=True),
                    id="code-root-prefix",
                    cls="code-root-prefix code-root-loading",
                    aria_label="Code root base path",
                ),
                Input(
                    id="code-root-suffix",
                    type="text",
                    placeholder="subdirectory (optional)",
                    cls="code-root-suffix",
                ),
                Input(
                    name="code_root",
                    id="field-code_root",
                    type="hidden",
                    value="",
                ),
                cls="code-root-wrap",
            ),
            cls="field",
        )
    )
    # Hidden detected language field
    run_card_children.append(
        Input(type="hidden", name="detected_language", id="field-detected-language", value="python"),
    )

    # Language detection row (shown after code root is set)
    run_card_children.append(
        Div(
            Span("Detected: ", cls="lang-detection-label"),
            Span(id="lang-detected-name", cls="lang-detection-value"),
            Span(id="lang-detected-count", cls="lang-detection-count"),
            Button(
                "Override",
                id="lang-override-btn",
                type="button",
                cls="primary",
                aria_label="Override detected language",
                onclick="document.getElementById('lang-override-select').style.display = "
                        "document.getElementById('lang-override-select').style.display === 'none' ? 'inline-block' : 'none';",
            ),
            Select(
                Option("Auto-detect", value="auto", selected=True),
                Option("Python", value="python"),
                Option("R", value="r"),
                Option("SAS", value="sas"),
                Option("MATLAB", value="matlab"),
                id="lang-override-select",
                cls="lang-override-select",
                onchange="handleLanguageOverride(this.value)",
            ),
            id="lang-detection-row",
            cls="lang-detection-row",
        )
    )

    advanced_modal_fields = [
        Div(
            Div(
                Label("Hardware tier", for_="field-hardware_tier"),
                Span("\u24d8", cls="info-tooltip", data_tooltip="Compute tier for the Domino job."),
                cls="label-row",
            ),
            Select(
                *tier_options,
                name="hardware_tier",
                id="field-hardware_tier",
                cls="hw-tier-select",
            ),
            cls="field",
        ),
        Div(
            Label("Provider", for_="field-provider"),
            Select(
                Option("Anthropic", value="anthropic"),
                Option("OpenAI (Compatible)", value="openai", selected=True),
                name="provider",
                id="field-provider",
            ),
            cls="field",
        ),
        Div(
            Div(
                Label("Provider API base URL", for_="field-provider_base_url"),
                Span(
                    "\u24d8",
                    cls="info-tooltip",
                    data_tooltip="HTTP base URL for the selected provider (official defaults shown). Use for proxies or compatible gateways.",
                ),
                cls="label-row",
            ),
            Input(
                name="provider_base_url",
                id="field-provider_base_url",
                type="text",
                value=_default_openai_base_url,
                placeholder=_default_openai_base_url,
                data_default_openai=_default_openai_base_url,
                data_default_anthropic=_default_anthropic_base_url,
            ),
            cls="field",
            id="provider-base-url-field",
        ),
        Div(
            Div(
                Label("Model", for_="field-model"),
                Span(
                    "\u24d8",
                    cls="info-tooltip",
                    data_tooltip="Provider model name.",
                ),
                cls="label-row",
            ),
            Input(
                name="model",
                id="field-model",
                type="text",
                value=DEFAULT_OPENAI_MODEL,
                placeholder=DEFAULT_OPENAI_MODEL,
            ),
            cls="field",
            id="model-name-field",
        ),
    ]

    advanced_modal = Div(
        Div(
            Div(
                H3("Advanced settings", id="studio-advanced-modal-title", cls="studio-modal-title"),
                Button(
                    "Close",
                    type="button",
                    id="studio-advanced-close",
                    cls="primary",
                    aria_label="Close advanced settings",
                ),
                cls="studio-modal-header",
            ),
            Div(*advanced_modal_fields, cls="studio-modal-body advanced-content"),
            cls="studio-modal",
            role="dialog",
            aria_modal="true",
            aria_labelledby="studio-advanced-modal-title",
        ),
        id="studio-advanced-modal",
        cls="studio-modal-overlay",
        aria_hidden="true",
    )

    run_card_children.append(
        Div(
            Button(
                "Advanced settings",
                type="button",
                id="studio-advanced-open",
                cls="primary",
            ),
            cls="advanced-open-row",
        )
    )

    run_card_children.append(Div(cls="card-content-spacer"))

    run_card_children.append(
        Div(
            Button("Generate Documentation", type="submit", id="generate-btn", cls="primary"),
            P("", id="generate-run-message", cls="generate-run-message"),
            cls="card-footer generate-actions",
        )
    )

    mid_col_children.append(Div(*run_card_children, cls="bp-card"))

    # RIGHT COLUMN: History
    right_col_children = [
        Div(
            H2("History"),
            Span("Step 3", cls="step-badge"),
            cls="col-header",
        ),
    ]

    right_col_children.append(
        Div(
            Div(
                Div(
                    Span(cls="fa-icon fa-file-lines spec-file-empty-icon"),
                    Span("No autodocs generated yet.", cls="spec-file-list-empty"),
                    cls="spec-file-empty",
                ),
                id="job-history-content",
            ),
            cls="output-panel",
        )
    )

    return (
        Title("Auto Model Docs Studio — Domino"),
        Style(fontawesome_faces_css()),
        Script(STUDIO_FONT_BASE_PATCH_JS),
        # Header
        Div(
            Div(
                NotStr(_LOGO_SVG),
                cls="domino-header-inner",
            ),
            cls="domino-header",
        ),
        # Page content
        Div(
            H1("Auto Model Docs Studio", cls="page-title"),
            Div(
                *_insight_children,
                cls="studio-page-insight",
            ),
            *_render_warnings_banner(_STARTUP_WARNINGS),
            Form(
                Div(
                    # Left column
                    Div(*left_col_children, cls="studio-col-left"),
                    # Middle column
                    Div(*mid_col_children, cls="studio-col-mid"),
                    # Right column
                    Div(*right_col_children, cls="studio-col-right"),
                    cls="studio-grid",
                ),
                id="main-form",
                data_execution_mode="domino",
                data_app_rel="run",
                enctype="multipart/form-data",
            ),
            advanced_modal,
            cls="page",
        ),
    )


# ---------------------------------------------------------------------------
# Register route modules
# ---------------------------------------------------------------------------

register_font_assets(rt)
register_api_routes(rt)
register_job_routes(rt)


# ---------------------------------------------------------------------------
# Middleware
# ---------------------------------------------------------------------------

from starlette.middleware.cors import CORSMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware
from autodoc.core.config import Settings as _AppSettings

HOST = os.environ.get("APP_HOST", "0.0.0.0")
PORT = int(os.environ.get("APP_PORT", "8888"))

try:
    _app_settings = _AppSettings()
    _cors_origins = _app_settings.cors_origins
    _allowed_hosts = _app_settings.allowed_hosts
except Exception:
    _cors_origins = ["*"]
    _allowed_hosts = ["*"]

app.add_middleware(TrustedHostMiddleware, allowed_hosts=_allowed_hosts)
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type"],
)


@app.middleware("http")
async def capture_auth_context(request, call_next):
    from studio.state import auth_context as _auth_context

    forwarded = request.headers.get("authorization")
    _auth_context.set_request_auth_header(forwarded)
    try:
        response = await call_next(request)
    finally:
        _auth_context.set_request_auth_header(None)
    return response


# ---------------------------------------------------------------------------
# Startup / Shutdown
# ---------------------------------------------------------------------------

@app.on_event("startup")
async def _on_startup():
    import studio.state as _state
    from artifact_layout import init_layout

    init_layout()
    _state._STARTUP_WARNINGS = _validate_environment()


# ---------------------------------------------------------------------------
# Serve
# ---------------------------------------------------------------------------

serve(host=HOST, port=PORT, access_log=False)
