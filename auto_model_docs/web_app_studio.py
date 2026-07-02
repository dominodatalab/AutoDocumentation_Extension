#!/usr/bin/env python3
"""FastHTML UI for Auto Model Documentation — Wizard redesign.

Two-step wizard:
  Step 1 — Choose a template (gallery + section preview + advanced config)
  Step 2 — Results (live job status, download links, history)
"""

from __future__ import annotations

import json
import os
import pathlib
from typing import Optional

from fasthtml.common import *
from starlette.requests import Request
from starlette.staticfiles import StaticFiles

from domino_auth import configure_auth, user_auth

configure_auth(user_auth)

_LOGO_SVG = (pathlib.Path(__file__).parent.parent / "domino-logo.svg").read_text()

from default_consts import DEFAULT_OPENAI_MODEL

from studio.state import (
    _STARTUP_WARNINGS,
    _resolve_request_project_id,
    domino_client,
    domino_datasets,
    EnvironmentWarning,
)
from studio.styles import STUDIO_CSS
from studio.scripts import MAIN_DOM_JS
from studio.ui_components import (
    _render_warnings_banner,
    _validate_environment,
    format_project_context_label,
    render_studio_bootstrap_error_page,
    studio_job_store_config_error,
    validate_studio_domino_compute_environment,
)
from studio.routes_api import register_api_routes
from studio.routes_job import register_job_routes

from domino_job_store import ensure_database


# ---------------------------------------------------------------------------
# Create FastHTML app
# ---------------------------------------------------------------------------

app, rt = fast_app(
    pico=False,
    hdrs=(
        Style(STUDIO_CSS),
        Script(MAIN_DOM_JS),
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
            Div(
                Div(
                    Label("Branch (optional)", for_="field-branch"),
                    Span("\u24d8", cls="info-tooltip", data_tooltip="Git branch for the Domino job. Leave blank to use the project default."),
                    cls="label-row",
                ),
                Input(
                    name="branch",
                    id="field-branch",
                    type="text",
                    autocomplete="off",
                ),
                cls="field",
                id="branch-field",
                style="display:none",
            ),

            Div(
                Div(
                    Label("Code path", for_="field-code_path"),
                    Span("\u24d8", cls="info-tooltip", data_tooltip="Path to the source code to be documented."),
                    cls="label-row",
                ),
                Div(
                    Input(
                        name="code_path",
                        id="field-code_path",
                        type="text",
                        placeholder="Loading\u2026",
                        autocomplete="off",
                    ),
                    Ul(id="code-path-dropdown", cls="combobox-dropdown hidden"),
                    cls="combobox",
                    id="code-path-combobox",
                ),
                cls="field",
                id="code-path-field",
            ),

            Div(
                Div(
                    Label("Hardware tier", for_="field-hardware_tier"),
                    Span("\u24d8", cls="info-tooltip", data_tooltip="Compute tier for the Domino job."),
                    cls="label-row",
                ),
                Select(*tier_options, name="hardware_tier", id="field-hardware_tier", cls="hw-tier-select"),
                cls="field",
            ),

            Div(
                Label("Provider", for_="field-provider"),
                Select(
                    Option("Anthropic", value="anthropic"),
                    Option("OpenAI (and compatible)", value="openai", selected=True),
                    name="provider",
                    id="field-provider",
                    onchange="toggleOpenAIFields(this.value)",
                ),
                cls="field",
            ),

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

            Div(
                Div(
                    Label("Model", for_="field-model"),
                    Span("\u24d8", cls="info-tooltip", data_tooltip="Model name. Leave blank for the provider default."),
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

    project_id = _resolve_request_project_id(req)
    if not project_id:
        return (
            Title("Model Docs — Domino"),
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
            Div(Div(NotStr(_LOGO_SVG), cls="domino-header-inner"), cls="domino-header"),
            Div(
                Div(Div(Span("Fetching project details...", cls="bootstrap-status-text"), cls="bootstrap-status-wrap")),
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

    config_err = studio_job_store_config_error()
    if config_err:
        heading, message, detail = config_err
        return render_studio_bootstrap_error_page(heading, message, detail)

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

    compute_env_errors = validate_studio_domino_compute_environment(domino_client)

    page_warnings = list(_STARTUP_WARNINGS)
    if project_id:
        try:
            ensured = domino_datasets.ensure_dataset(project_id)
            ds_id = (ensured.get("id") or "").strip()
            if ds_id:
                import spec_template_sync
                snap_id = (ensured.get("rwSnapshotId") or ensured.get("readWriteSnapshotId") or "").strip() or None
                if snap_id:
                    spec_template_sync.sync_builtins_to_autodoc_dataset(ds_id, dest_snapshot_id=snap_id)
                else:
                    spec_template_sync.sync_builtins_to_autodoc_dataset(ds_id)
        except Exception:
            page_warnings.append(
                EnvironmentWarning(
                    level="error",
                    message="Access to this project's Datasets is required.",
                    action="Ask the project owner for access, or contact your administrator.",
                )
            )

    return (
        Title("Model Docs — Domino"),
        # Header
        Div(
            Div(NotStr(_LOGO_SVG), cls="domino-header-inner"),
            cls="domino-header",
        ),
        # Page (full-height column below the Domino header)
        Div(
            *_render_warnings_banner(page_warnings),

            # Main form (wraps both wizard steps)
            Form(
                Input(name="spec_path", id="field-spec_path", type="hidden", value=""),

                Div(
                    Div(
                        Div(
                            Div(
                                Span("Model Docs", cls="page-title-text"),
                                Span(
                                    project_display_name,
                                    cls="page-title-project",
                                ) if project_display_name else None,
                                cls="page-title-row",
                            ),

                            Div(
                                Div(
                                    H2("Choose a template", cls="wizard-col-title"),
                                    Span(
                                        Span("folder", cls="material-symbols-outlined", style="font-size:13px"),
                                        format_project_context_label(project_display_name or project_id),
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

                            Div(id="spec-confirm-bar", cls="spec-confirm-bar", style="display:none"),

                            Div(
                                Div(
                                    Span("description", cls="material-symbols-outlined gallery-loading-icon"),
                                    Span("Loading templates...", cls="gallery-loading-text"),
                                    cls="gallery-loading",
                                ),
                                id="template-gallery",
                                cls="template-gallery",
                            ),

                            Div(
                                Div(
                                    Label(
                                        "Governance bundle",
                                        Span(
                                            "info",
                                            cls="material-symbols-outlined filter-info-icon",
                                            title="Bundle whose evidence and findings ground the document. Required when this project has governance bundles.",
                                        ),
                                        cls="filter-label",
                                    ),
                                    Select(
                                        Option("Loading bundles...", value="", disabled=True, selected=True),
                                        id="governance-bundle-select",
                                        cls="filter-input",
                                    ),
                                    Div(
                                        id="governance-bundle-auto",
                                        cls="governance-bundle-auto",
                                        style="display:none",
                                    ),
                                    Div(
                                        id="governance-bundle-hint",
                                        cls="governance-bundle-hint",
                                    ),
                                    cls="filter-field",
                                ),
                                cls="filters-body",
                                style="padding: 0.25rem 0 0.5rem 0; display:none",
                                id="governance-bundle-field",
                            ),

                            Details(
                                Summary(
                                    Span("filter_list", cls="material-symbols-outlined", style="font-size:16px"),
                                    "Filters",
                                    cls="adv-opts-accordion-summary",
                                ),
                                Div(
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
                                open=False,
                            ),

                            cls="wizard-col-gallery",
                        ),

                        Div(
                            Div(
                                Div(
                                    Div(
                                        Span(
                                            Span("Document outline", cls="preview-panel-label"),
                                            Span("Preview", cls="preview-panel-tag"),
                                            style="display:flex;align-items:center;gap:0.5rem;",
                                        ),
                                        Button(
                                            Span("history", cls="material-symbols-outlined"),
                                            "History",
                                            type="button",
                                            id="landing-history-btn",
                                            cls="history-drawer-btn",
                                        ),
                                        cls="preview-panel-header-row",
                                    ),
                                    Div(
                                        Span("Document context:", cls="doc-scope-prefix"),
                                        Span(
                                            "Code, Model Metrics and Artifacts. Governance Evidence & Findings",
                                            cls="doc-scope-items",
                                        ),
                                        id="doc-scope-label",
                                        cls="doc-scope-label",
                                    ),
                                    cls="preview-panel-header",
                                ),
                                Div(
                                    Div(
                                        Span("description", cls="material-symbols-outlined preview-empty-icon"),
                                        Span("Select a template to preview its document outline", cls="preview-empty-text"),
                                        cls="preview-empty-state",
                                        id="template-preview-empty",
                                    ),
                                    id="template-preview-panel",
                                    cls="template-preview-panel",
                                ),
                                Div(
                                    Div(
                                        Span("Edit template", cls="edit-tpl-label"),
                                        Button(
                                            Span("open_in_full", cls="material-symbols-outlined edit-tpl-maximize-icon"),
                                            type="button",
                                            id="edit-tpl-maximize-btn",
                                            cls="edit-tpl-maximize-btn",
                                            title="Maximize editor",
                                            aria_label="Maximize editor",
                                            aria_pressed="false",
                                        ),
                                        cls="edit-tpl-header",
                                    ),
                                    Textarea(
                                        id="edit-template-yaml",
                                        cls="edit-tpl-textarea",
                                        placeholder="Select a template to edit its YAML...",
                                        spellcheck="false",
                                    ),
                                    Div(
                                        Button(
                                            "Save",
                                            type="button",
                                            id="edit-tpl-save-btn",
                                            cls="edit-tpl-action-btn edit-tpl-save-btn",
                                            disabled=True,
                                        ),
                                        Button(
                                            "Revert",
                                            type="button",
                                            id="edit-tpl-revert-btn",
                                            cls="edit-tpl-action-btn edit-tpl-revert-btn",
                                            disabled=True,
                                        ),
                                        cls="edit-tpl-actions",
                                    ),
                                    Div(
                                        id="edit-tpl-status",
                                        cls="edit-tpl-status",
                                    ),
                                    cls="edit-tpl-section",
                                    id="edit-tpl-section",
                                ),
                                Div(
                                    Span("hourglass_empty", cls="material-symbols-outlined preview-empty-icon"),
                                    Span("Loading...", cls="preview-empty-text"),
                                    id="preview-card-loading",
                                    cls="preview-card-loading",
                                ),
                                cls="preview-card",
                            ),
                            cls="wizard-col-config",
                        ),

                        cls="wizard-layout",
                    ),

                    Div(
                        Button(
                            Span("tune", cls="material-symbols-outlined", style="font-size:14px"),
                            "Advanced options",
                            type="button",
                            id="adv-opts-open-btn",
                            cls="adv-opts-link",
                        ),
                        Div(
                            Span(
                                "Uses the LLM provider selected in Advanced options. Environment variables ANTHROPIC_API_KEY or OPENAI_API_KEY required.",
                                id="llm-provider-notice",
                                cls="wizard-llm-notice",
                            ),
                            Div(id="wizard-error", cls="wizard-error", style="display:none"),
                            Button(
                                "Generate Documentation",
                                type="button",
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

                # Advanced options modal
                Div(
                    Div(
                        Div(
                            Span("Advanced options", cls="modal-title"),
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

                # Browse-spec modal
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
                            Div(
                                Label("Source", Span(" *", cls="required-star")),
                                Select(
                                    Option("Loading sources...", value="", disabled=True, selected=True),
                                    id="browse-dataset-select",
                                ),
                                cls="field",
                            ),
                            Div(id="browse-breadcrumb", cls="spec-breadcrumb"),
                            Div(
                                Div(
                                    Span("folder_open", cls="material-symbols-outlined spec-file-empty-icon"),
                                    Span("Select a dataset to browse its files", cls="spec-file-list-empty"),
                                    cls="spec-file-empty",
                                ),
                                id="spec-file-list",
                                cls="spec-file-list",
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

                # Step 2: Results
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
                            format_project_context_label(project_display_name or project_id),
                            cls="project-context-chip",
                        ) if (project_display_name or project_id) else None,
                        Div(id="layout-switcher-slot", cls="layout-switcher-slot"),
                        cls="results-nav-row",
                    ),
                    Div(
                        Div(
                            Span("rocket_launch", cls="material-symbols-outlined results-submitting-icon"),
                            Span("Submitting job...", cls="results-submitting-text"),
                            cls="results-submitting",
                        ),
                        id="results-panel",
                        cls="results-panel",
                    ),
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

                # History drawer
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

            Script(
                json.dumps(compute_env_errors),
                id="studio-compute-env-json",
                type="application/json",
            ) if compute_env_errors else None,

            cls="page page--wizard",
        ),
    )


# ---------------------------------------------------------------------------
# Register route modules
# ---------------------------------------------------------------------------

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

    ensure_database()
    init_layout()
    _state._STARTUP_WARNINGS = _validate_environment()


# ---------------------------------------------------------------------------
# Serve
# ---------------------------------------------------------------------------

serve(host=HOST, port=PORT, access_log=False, reload=False)
