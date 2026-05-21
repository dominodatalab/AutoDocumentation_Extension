#!/usr/bin/env python3
"""FastHTML UI for Auto Model Documentation — Wizard redesign.

Two-step wizard:
  Step 1 — Choose a template (gallery + section preview + advanced config)
  Step 2 — Results (live job status, download links, history)
"""

from __future__ import annotations

import os
import pathlib
from typing import Optional

from fasthtml.common import *
from starlette.requests import Request
from starlette.staticfiles import StaticFiles

from domino_auth import configure_auth, user_auth

configure_auth(user_auth)

_LOGO_SVG = (pathlib.Path(__file__).parent.parent / "domino-logo.svg").read_text()


from studio.state import (
    _STARTUP_WARNINGS,
    domino_client,
    log_buffer,
    logger,
)
from studio.styles import STUDIO_CSS
from studio.scripts import MAIN_DOM_JS
from studio.ui_components import (
    _render_warnings_banner,
    _validate_environment,
)
from studio.routes_api import register_api_routes
from studio.routes_spec import register_spec_routes
from studio.routes_job import register_job_routes

from temporary_versioning import get_deploy_version_label


# ---------------------------------------------------------------------------
# Create FastHTML app
# ---------------------------------------------------------------------------

app, rt = fast_app(
    pico=False,
    hdrs=(
        Style(STUDIO_CSS),
        Script(MAIN_DOM_JS),
        Script(src="static/vendor/mammoth.browser.min.js"),
    )
)

_static_dir = pathlib.Path(__file__).parent / "static"
_static_dir.mkdir(exist_ok=True)
app.mount("/static", StaticFiles(directory=str(_static_dir)), name="static")


# ---------------------------------------------------------------------------
# Helper: build the advanced-options panel (collapsed <details>)
# ---------------------------------------------------------------------------

def _build_advanced_options(tier_options):
    _default_openai_base_url = os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1")
    _default_anthropic_base_url = os.environ.get("ANTHROPIC_BASE_URL", "https://api.anthropic.com")

    return Div(
            # ── Hardware tier ───────────────────────────────────────────
            Div(
                Div(
                    Label("Hardware tier", for_="field-hardware_tier"),
                    Span("\u24d8", cls="info-tooltip", data_tooltip="Compute tier for the Domino job."),
                    cls="label-row",
                ),
                Select(*tier_options, name="hardware_tier", id="field-hardware_tier", cls="hw-tier-select"),
                cls="field",
            ),

            # ── Provider ────────────────────────────────────────────────
            Div(
                Label("Provider", for_="field-provider"),
                Select(
                    Option("Anthropic", value="anthropic"),
                    Option("OpenAI (Compatible)", value="openai", selected=True),
                    name="provider",
                    id="field-provider",
                    onchange="toggleOpenAIFields(this.value)",
                ),
                cls="field",
            ),

            # ── Provider API base URL ────────────────────────────────────
            Div(
                Div(
                    Label("Provider API base URL", for_="field-provider_base_url"),
                    Span(
                        "\u24d8",
                        cls="info-tooltip",
                        data_tooltip="HTTP base URL for the selected provider. Use for proxies or compatible gateways.",
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

            # ── Model ────────────────────────────────────────────────────
            Div(
                Div(
                    Label("Model", for_="field-model"),
                    Span("\u24d8", cls="info-tooltip", data_tooltip="Model name. Leave blank for the provider default."),
                    cls="label-row",
                ),
                Input(name="model", id="field-model", type="text", value="", placeholder=""),
                cls="field",
                id="model-name-field",
            ),

            cls="advanced-content",
        )


# ---------------------------------------------------------------------------
# index()
# ---------------------------------------------------------------------------

@rt("/")
async def index(req: Request):
    host = req.headers.get("x-forwarded-host") or req.headers.get("host") or ""
    scheme = req.headers.get("x-forwarded-proto", "https")
    domino_client.set_ui_host(host, scheme)

    project_id = req.query_params.get("projectId") or None
    if not project_id:
        return (
            Title("ModelDoc — Domino"),
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
                        } catch(e) {}
                    }
                    if (!pid && document.referrer) {
                        try { pid = new URL(document.referrer).searchParams.get('projectId'); } catch(e) {}
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
            Div(Div(NotStr(_LOGO_SVG), cls="domino-header-inner"), cls="domino-header"),
            Div(
                Div(Div(Span("Resolving project...", cls="bootstrap-status-text"), cls="bootstrap-status-wrap")),
                Div(
                    Div(
                        H2("Project ID required"),
                        P("This app must be launched with a ", Code("projectId"),
                          " query parameter so it knows which project to run jobs in."),
                        P("If you're running this as a Domino App, make sure the app is "
                          "configured to pass the project ID to the iframe URL.",
                          cls="bootstrap-error-detail"),
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
        pass
    if not tier_options:
        tier_options = [Option("(default)", value="")]

    advanced_opts = _build_advanced_options(tier_options)

    # ── Build the page ────────────────────────────────────────────────

    _is_mock = bool(os.environ.get("AUTODOC_MOCK_MODE"))

    return (
        Title("ModelDoc — Domino"),
        # Header
        Div(
            Div(NotStr(_LOGO_SVG), cls="domino-header-inner"),
            Span("local · mock data", cls="header-mock-badge") if _is_mock else None,
            cls="domino-header",
        ),
        # Page (full-height column below the Domino header)
        Div(
            *_render_warnings_banner(_STARTUP_WARNINGS),
            # (wizard-step1 fills remaining height; no page padding needed)

            # ── Main form (wraps both wizard steps) ─────────────────────
            Form(
                # Always-present hidden fields
                Input(type="hidden", name="detected_language", id="field-detected-language", value="python"),
                Input(name="spec_path", id="field-spec_path", type="hidden", value=""),

                # ── STEP 1: Template selection ──────────────────────────
                Div(
                    Div(
                        # LEFT: gallery
                        Div(
                            # Page title row (moved inside gallery column)
                            Div(
                                Span("ModelDoc", cls="page-title-text"),
                                Span(
                                    project_display_name,
                                    cls="page-title-project",
                                ) if project_display_name else None,
                                cls="page-title-row",
                            ),

                            # Gallery header row: title + Browse/Upload actions
                            Div(
                                Div(
                                    H2("Choose a template", cls="wizard-col-title"),
                                    Span(
                                        Span("folder", cls="material-symbols-outlined", style="font-size:13px"),
                                        project_display_name or project_id,
                                        cls="project-context-chip",
                                    ) if (project_display_name or project_id) else None,
                                ),
                                Div(
                                    Button(
                                        Span("folder_open", cls="material-symbols-outlined", style="font-size:15px"),
                                        "Browse",
                                        type="button",
                                        cls="gallery-action-btn",
                                        onclick="openBrowseModal()",
                                    ),
                                    Button(
                                        Span("upload_file", cls="material-symbols-outlined", style="font-size:15px"),
                                        "Upload",
                                        type="button",
                                        cls="gallery-action-btn",
                                        onclick="document.getElementById('spec-yaml-upload').click()",
                                    ),
                                    Input(
                                        type="file",
                                        accept=".yaml,.yml",
                                        id="spec-yaml-upload",
                                        cls="hidden-upload",
                                        onchange="handleYamlUpload(this)",
                                    ),
                                    cls="gallery-action-btns",
                                ),
                                cls="gallery-header-row",
                            ),

                            # Uploaded spec confirmation (hidden until a file is chosen)
                            Div(id="spec-confirm-bar", cls="spec-confirm-bar", style="display:none"),

                            # Template cards — JS will render these via the API
                            Div(
                                Div(
                                    Span("description", cls="material-symbols-outlined gallery-loading-icon"),
                                    Span("Loading templates...", cls="gallery-loading-text"),
                                    cls="gallery-loading",
                                ),
                                id="template-gallery",
                                cls="template-gallery",
                            ),

                            # Context Sources accordion
                            Details(
                                Summary(
                                    Span("database", cls="material-symbols-outlined", style="font-size:16px"),
                                    "Context sources",
                                    cls="adv-opts-accordion-summary",
                                ),
                                Div(
                                    P("Select which data sources the report generator will use.", cls="ctx-sources-subheading"),
                                    Div(
                                        # Code — always selected, required
                                        Div(
                                            Div(
                                                Span("Code", cls="ctx-source-name"),
                                                Span("Required", cls="ctx-source-required-tag"),
                                                Span("check_circle", cls="material-symbols-outlined ctx-source-check"),
                                                cls="ctx-source-header",
                                            ),
                                            P("Repository files and ML pipeline logic", cls="ctx-source-desc"),
                                            data_value="code",
                                            tabindex="0",
                                            role="button",
                                            aria_pressed="true",
                                            cls="ctx-source-card selected ctx-source-required",
                                        ),
                                        *[
                                            Div(
                                                Div(
                                                    Span(title, cls="ctx-source-name"),
                                                    Span("check_circle", cls="material-symbols-outlined ctx-source-check"),
                                                    cls="ctx-source-header",
                                                ),
                                                P(desc, cls="ctx-source-desc"),
                                                data_value=val,
                                                tabindex="0",
                                                role="button",
                                                aria_pressed="false",
                                                cls="ctx-source-card",
                                            )
                                            for val, title, desc in [
                                                ("experiments",   "Experiments",        "Domino experiment runs and logged metrics"),
                                                ("data",          "Data",               "Data sources and feature definitions"),
                                                ("model_metrics", "Model metrics",       "Performance and evaluation results"),
                                                ("governance",    "Governance evidence", "Artifacts, approvals, and audit trail"),
                                            ]
                                        ],
                                        id="ctx-sources-grid",
                                        cls="ctx-sources-grid",
                                    ),
                                    cls="adv-opts-accordion-body ctx-sources-body",
                                ),
                                cls="adv-opts-accordion",
                            ),

                            # Filters accordion (below context sources)
                            Details(
                                Summary(
                                    Span("filter_list", cls="material-symbols-outlined", style="font-size:16px"),
                                    "Filters",
                                    cls="adv-opts-accordion-summary",
                                ),
                                Div(
                                    # Model names
                                    Div(
                                        Label(
                                            "Model names",
                                            Span("info", cls="material-symbols-outlined filter-info-icon",
                                                 title="Comma-separated model names. Use * as a wildcard, e.g. churn-*"),
                                            cls="filter-label",
                                        ),
                                        Input(
                                            type="text",
                                            name="filter_model_names",
                                            id="filter-model-names",
                                            placeholder="model1, churn*, fraud-*",
                                            cls="filter-input",
                                        ),
                                        cls="filter-field",
                                    ),
                                    # Experiment names
                                    Div(
                                        Label(
                                            "Experiment names",
                                            Span("info", cls="material-symbols-outlined filter-info-icon",
                                                 title="Comma-separated MLflow experiment names. Use * as a wildcard."),
                                            cls="filter-label",
                                        ),
                                        Input(
                                            type="text",
                                            name="filter_experiment_names",
                                            id="filter-experiment-names",
                                            placeholder="exp1, exp2, my-experiment*",
                                            cls="filter-input",
                                        ),
                                        cls="filter-field",
                                    ),
                                    # Latest version only
                                    Label(
                                        Input(
                                            type="checkbox",
                                            name="filter_latest_only",
                                            id="filter-latest-only",
                                            checked=True,
                                            cls="filter-checkbox",
                                        ),
                                        "Latest version only",
                                        cls="filter-checkbox-label",
                                    ),
                                    cls="adv-opts-accordion-body filters-body",
                                ),
                                cls="adv-opts-accordion",
                            ),

                            cls="wizard-col-gallery",
                        ),

                        # RIGHT: single card column
                        Div(
                            Div(
                                # ── Header ───────────────────────────────────
                                Div(
                                    Span(
                                        Span("Document outline", cls="preview-panel-label"),
                                        Span("Preview", cls="preview-panel-tag"),
                                        style="display:flex;align-items:center;gap:0.5rem;",
                                    ),
                                    cls="preview-panel-header",
                                ),
                                # ── Sections list ────────────────────────────
                                Div(
                                    Div(
                                        Span("description", cls="material-symbols-outlined preview-empty-icon"),
                                        Span("Select a template to preview its document outline", cls="preview-empty-text"),
                                        cls="preview-empty-state",
                                    ),
                                    id="template-preview-panel",
                                    cls="template-preview-panel",
                                ),
                                # ── Edit template ────────────────────────────
                                Div(
                                    Div(
                                        Span("Edit template", cls="edit-tpl-label"),
                                        cls="edit-tpl-header",
                                    ),
                                    Textarea(
                                        id="edit-template-yaml",
                                        name="spec_yaml_content",
                                        cls="edit-tpl-textarea",
                                        placeholder="Select a template to edit its YAML…",
                                        spellcheck="false",
                                    ),
                                    cls="edit-tpl-section",
                                ),
                                # ── Output format ────────────────────────────
                                Div(
                                    Span("Output format", cls="output-fmt-label"),
                                    Div(
                                        *[
                                            Label(
                                                Input(type="radio", name="output_format", value=val,
                                                      checked=default, cls="output-fmt-radio"),
                                                Span(icon, cls="material-symbols-outlined output-fmt-icon"),
                                                Span(label, cls="output-fmt-text"),
                                                cls="output-fmt-option",
                                            )
                                            for val, label, icon, default in [
                                                ("docx", "Word (.docx)",     "description",     True),
                                                ("md",   "Markdown (.md)",   "markdown",        False),
                                                ("tex",  "LaTeX (.tex)",     "integration_instructions", False),
                                            ]
                                        ],
                                        cls="output-fmt-group",
                                    ),
                                    cls="output-fmt-section",
                                ),
                                cls="preview-card",
                            ),
                            cls="wizard-col-config",
                        ),

                        cls="wizard-layout",
                    ),

                    # ── Footer: Advanced options (left) + Generate (right) ──
                    Div(
                        Button(
                            Span("tune", cls="material-symbols-outlined", style="font-size:14px"),
                            "Advanced options",
                            type="button",
                            id="adv-opts-open-btn",
                            cls="adv-opts-link",
                        ),
                        Div(
                            Div(id="wizard-error", cls="wizard-error", style="display:none"),
                            Button(
                                "Generate Documentation",
                                type="submit",
                                id="generate-btn",
                                cls="primary wizard-generate-btn",
                                disabled=True,
                            ),
                            cls="wizard-footer-right",
                        ),
                        cls="wizard-footer",
                    ),

                    id="wizard-step1",
                ),

                # ── Advanced options modal ────────────────────────────────
                Div(
                    Div(
                        Div(
                            Span(
                                "Advanced options",
                                cls="modal-title",
                            ),
                            Button(
                                Span("close", cls="material-symbols-outlined"),
                                type="button",
                                id="adv-opts-close-btn",
                                cls="modal-close-btn",
                                aria_label="Close",
                            ),
                            cls="modal-header",
                        ),
                        Div(
                            advanced_opts,
                            cls="modal-body",
                        ),
                        Div(
                            Button(
                                "Done",
                                type="button",
                                id="adv-opts-done-btn",
                                cls="primary",
                            ),
                            cls="modal-footer",
                        ),
                        cls="adv-opts-modal",
                    ),
                    id="adv-opts-overlay",
                    cls="modal-overlay",
                ),

                # ── Browse-spec modal ────────────────────────────────────
                Div(
                    Div(
                        Div(
                            Span("Browse spec files", cls="modal-title"),
                            Button(
                                Span("close", cls="material-symbols-outlined"),
                                type="button",
                                cls="modal-close-btn",
                                aria_label="Close",
                                onclick="closeBrowseModal()",
                            ),
                            cls="modal-header",
                        ),
                        Div(
                            # Breadcrumb
                            Div(
                                A("root", href="#", cls="browse-crumb-link",
                                  onclick="event.preventDefault()"),
                                cls="browse-breadcrumb-bar",
                            ),
                            # File tree list — populated by JS via /api/dataset-files
                            Div(
                                Span("folder_open", cls="material-symbols-outlined spec-file-empty-icon"),
                                Span("Select a dataset to browse its files", cls="spec-file-list-empty"),
                                cls="spec-file-empty",
                                id="browse-file-list",
                            ),
                            cls="modal-body browse-modal-body",
                        ),
                        Div(
                            Span("", id="browse-selected-label", cls="browse-selected-label"),
                            Button(
                                "Select",
                                type="button",
                                id="browse-confirm-btn",
                                cls="primary",
                                onclick="confirmBrowseSelection()",
                                disabled=True,
                            ),
                            cls="browse-footer",
                        ),
                        cls="adv-opts-modal browse-modal",
                    ),
                    id="browse-modal-overlay",
                    cls="modal-overlay",
                    onclick="if(event.target===this)closeBrowseModal()",
                ),

                # ── STEP 2: Results ─────────────────────────────────────
                Div(
                    Div(
                        Button(
                            "\u2190 Back",
                            type="button",
                            id="btn-back-to-templates",
                            cls="back-link-btn",
                        ),
                        Span(
                            Span("folder", cls="material-symbols-outlined", style="font-size:13px"),
                            project_display_name or project_id,
                            cls="project-context-chip",
                        ) if (project_display_name or project_id) else None,
                        # Layout switcher + history button — populated by JS
                        Div(id="layout-switcher-slot", cls="layout-switcher-slot"),
                        Div(id="history-btn-slot", cls="history-btn-slot"),
                        cls="results-nav-row",
                    ),

                    # Results panel (populated by JS after submission)
                    Div(
                        Div(
                            Span("rocket_launch", cls="material-symbols-outlined results-submitting-icon"),
                            Span("Submitting job...", cls="results-submitting-text"),
                            cls="results-submitting",
                        ),
                        id="results-panel",
                        cls="results-panel",
                    ),

                    # Layout A: History accordion (hidden in Layout B by JS)
                    Details(
                        Summary("History", cls="advanced-section-summary"),
                        Div(
                            Div(
                                Span("description", cls="material-symbols-outlined spec-file-empty-icon"),
                                Span("No history yet.", cls="spec-file-list-empty"),
                                cls="spec-file-empty",
                            ),
                            id="job-history-content",
                        ),
                        cls="advanced-section history-section",
                        id="history-details",
                        open=False,
                    ),

                    id="wizard-step2",
                    cls="wizard-step",
                    style="display:none",
                ),

                # Layout B: History drawer (always in DOM, shown/hidden by JS)
                Div(id="history-drawer-overlay", cls="history-drawer-overlay"),
                Div(
                    Div(
                        Span("History", cls="drawer-title"),
                        Button(
                            Span("close", cls="material-symbols-outlined"),
                            type="button",
                            id="history-drawer-close",
                            cls="drawer-close-btn",
                            aria_label="Close",
                        ),
                        cls="drawer-header",
                    ),
                    Div(
                        Div(
                            Span("description", cls="material-symbols-outlined spec-file-empty-icon"),
                            Span("No history yet.", cls="spec-file-list-empty"),
                            cls="spec-file-empty",
                        ),
                        id="job-history-drawer-content",
                        cls="drawer-body",
                    ),
                    id="history-drawer",
                    cls="history-drawer",
                ),

                id="main-form",
                data_execution_mode="domino",
                data_app_rel="run",
                enctype="multipart/form-data",
            ),

            cls="page page--wizard",
        ),
    )


# ---------------------------------------------------------------------------
# Register route modules
# ---------------------------------------------------------------------------

if os.environ.get("AUTODOC_MOCK_MODE"):
    from mock_routes import register_mock_routes
    register_mock_routes(rt)

register_api_routes(rt)
register_spec_routes(rt)
register_job_routes(rt)


@rt("/logs")
def logs():
    from starlette.responses import PlainTextResponse
    lines = log_buffer.snapshot()
    body = "\n".join(lines) if lines else "(no log records buffered yet)"
    return PlainTextResponse(body)


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
    import threading as _threading
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

serve(host=HOST, port=PORT)
