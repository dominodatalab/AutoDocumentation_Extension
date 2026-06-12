"""Tests for studio/ui_components.py — sanitizers, environment validation, UI helpers."""

from __future__ import annotations

import importlib
import importlib.util
import os
import sys
from pathlib import Path
from types import ModuleType
from unittest.mock import MagicMock, patch

import pytest

# Ensure auto_model_docs is importable
_repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_pkg_dir = os.path.join(_repo_root, "auto_model_docs")
for p in (_repo_root, _pkg_dir):
    if p not in sys.path:
        sys.path.insert(0, p)


# ---------------------------------------------------------------------------
# Import helpers
# ---------------------------------------------------------------------------

def _load_module_from_file(name: str, path: str) -> ModuleType:
    """Load a Python module from an absolute file path."""
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def _mock_dependencies(monkeypatch):
    """Mock studio.state and fasthtml so ui_components can import."""
    from dataclasses import dataclass
    from typing import Optional

    # Build a real-ish state mock
    mock_state = ModuleType("studio.state")
    mock_state._get_default_code_root = lambda: Path("/mnt/code")
    mock_state._max_jobs = lambda: 1
    mock_state.domino_job_store = MagicMock()

    @dataclass
    class DominoJobRecord:
        id: str
        owner_id: str
        domino_run_id: Optional[str] = None
        hardware_tier: Optional[str] = None
        status: str = "queued"
        domino_status: Optional[str] = None
        job_url: Optional[str] = None
        dataset_id: Optional[str] = None
        spec_path: Optional[str] = None
        submitted_at: Optional[str] = None
        completed_at: Optional[str] = None
        error: Optional[str] = None
        project_id: Optional[str] = None

    @dataclass
    class EnvironmentWarning:
        level: str
        message: str
        action: str

    mock_state.DominoJobRecord = DominoJobRecord
    mock_state.EnvironmentWarning = EnvironmentWarning

    # Create a studio package module
    studio_pkg = ModuleType("studio")
    studio_pkg.__path__ = [os.path.join(_pkg_dir, "studio")]
    studio_pkg.__package__ = "studio"

    saved = {}
    for key in ("studio", "studio.state", "studio.ui_components"):
        saved[key] = sys.modules.get(key)

    sys.modules["studio"] = studio_pkg
    sys.modules["studio.state"] = mock_state

    # Ensure fasthtml.common provides the needed names
    fh_names = ("Div", "P", "A", "Span", "H3", "Select", "Option", "Input",
                "Label", "Table", "Thead", "Tbody", "Tr", "Th", "Td",
                "Pre", "Button", "Details", "Summary", "Ul", "Li")
    mock_fh_common = ModuleType("fasthtml.common")
    for name in fh_names:
        setattr(mock_fh_common, name, lambda *a, _name=name, **kw: MagicMock(__ft_name__=_name))
    # FT type stub
    mock_fh_common.FT = type("FT", (), {})

    mock_fh = ModuleType("fasthtml")
    mock_fh.common = mock_fh_common

    sys.modules["fasthtml"] = mock_fh
    sys.modules["fasthtml.common"] = mock_fh_common

    yield {"state": mock_state}

    # Restore
    for key, val in saved.items():
        if val is None:
            sys.modules.pop(key, None)
        else:
            sys.modules[key] = val
    sys.modules.pop("fasthtml", None)
    sys.modules.pop("fasthtml.common", None)


def _import_ui():
    """Force-(re)load ui_components from its source file."""
    sys.modules.pop("studio.ui_components", None)
    ui_path = os.path.join(_pkg_dir, "studio", "ui_components.py")
    return _load_module_from_file("studio.ui_components", ui_path)


# ---------------------------------------------------------------------------
# _sanitize_optional_int
# ---------------------------------------------------------------------------

class TestSanitizeOptionalInt:
    def test_none_returns_none(self):
        ui = _import_ui()
        assert ui._sanitize_optional_int(None) is None

    def test_empty_string_returns_none(self):
        ui = _import_ui()
        assert ui._sanitize_optional_int("") is None

    def test_valid_int_string(self):
        ui = _import_ui()
        assert ui._sanitize_optional_int("42") == 42

    def test_zero(self):
        ui = _import_ui()
        assert ui._sanitize_optional_int("0") == 0

    def test_invalid_returns_none(self):
        ui = _import_ui()
        assert ui._sanitize_optional_int("not-a-number") is None


# ---------------------------------------------------------------------------
# _sanitize_optional_float
# ---------------------------------------------------------------------------

class TestSanitizeOptionalFloat:
    def test_none_returns_none(self):
        ui = _import_ui()
        assert ui._sanitize_optional_float(None) is None

    def test_empty_string_returns_none(self):
        ui = _import_ui()
        assert ui._sanitize_optional_float("") is None

    def test_valid_float_string(self):
        ui = _import_ui()
        assert ui._sanitize_optional_float("3.14") == pytest.approx(3.14)

    def test_integer_string(self):
        ui = _import_ui()
        assert ui._sanitize_optional_float("10") == 10.0

    def test_invalid_returns_none(self):
        ui = _import_ui()
        assert ui._sanitize_optional_float("abc") is None


# ---------------------------------------------------------------------------
# _db_record_to_dataclass
# ---------------------------------------------------------------------------

class TestDbRecordToDataclass:
    def test_converts_full_row(self):
        ui = _import_ui()
        row = {
            "id": "job-1",
            "owner_id": "alice",
            "domino_run_id": "run-1",
            "hardware_tier": "tier-1",
            "status": "running",
            "domino_status": "Executing",
            "job_url": "https://domino/jobs/1",
            "dataset_id": "ds-9",
            "spec_path": "/spec.yaml",
            "submitted_at": "2026-01-01T00:00:00",
            "completed_at": None,
            "project_id": "proj-123",
        }
        record = ui._db_record_to_dataclass(row)
        assert record.id == "job-1"
        assert record.owner_id == "alice"
        assert record.status == "running"
        assert record.domino_run_id == "run-1"
        assert record.dataset_id == "ds-9"

    def test_handles_missing_optional_fields(self):
        ui = _import_ui()
        row = {"id": "job-2", "owner_id": "bob"}
        record = ui._db_record_to_dataclass(row)
        assert record.id == "job-2"
        assert record.status == "queued"  # default
        assert record.domino_run_id is None
        assert record.dataset_id is None


# ---------------------------------------------------------------------------
# _validate_environment
# ---------------------------------------------------------------------------

class TestValidateEnvironment:
    def test_no_warnings_in_normal_env(self, _mock_dependencies, monkeypatch):
        monkeypatch.setenv("MLFLOW_TRACKING_URI", "http://mlflow")
        monkeypatch.delenv("DOMINO_PROJECT_ID", raising=False)
        ui = _import_ui()
        with patch.object(Path, "exists", return_value=True):
            with patch.object(Path, "mkdir"):
                warnings = ui._validate_environment()
        assert isinstance(warnings, list)

    def test_warns_when_code_root_missing(self, _mock_dependencies, monkeypatch):
        monkeypatch.delenv("MLFLOW_TRACKING_URI", raising=False)
        monkeypatch.delenv("DOMINO_PROJECT_ID", raising=False)
        _mock_dependencies["state"]._get_default_code_root = lambda: Path(".")
        ui = _import_ui()
        with patch.object(Path, "exists", return_value=False):
            with patch.object(Path, "mkdir"):
                warnings = ui._validate_environment()
        levels = [w.level for w in warnings]
        assert "warning" in levels

    def test_warns_when_mlflow_missing(self, _mock_dependencies, monkeypatch):
        monkeypatch.delenv("MLFLOW_TRACKING_URI", raising=False)
        monkeypatch.delenv("DOMINO_PROJECT_ID", raising=False)
        ui = _import_ui()
        with patch.object(Path, "exists", return_value=True):
            with patch.object(Path, "mkdir"):
                warnings = ui._validate_environment()
        messages = [w.message for w in warnings]
        assert any("MLflow" in m for m in messages)

    def test_warns_when_domino_api_host_missing(self, _mock_dependencies, monkeypatch):
        monkeypatch.setenv("DOMINO_PROJECT_ID", "proj-1")
        monkeypatch.delenv("DOMINO_API_HOST", raising=False)
        monkeypatch.delenv("MLFLOW_TRACKING_URI", raising=False)
        ui = _import_ui()
        with patch.object(Path, "exists", return_value=True):
            with patch.object(Path, "mkdir"):
                warnings = ui._validate_environment()
        messages = [w.message for w in warnings]
        assert any("API host" in m for m in messages)


# ---------------------------------------------------------------------------
# _field_id
# ---------------------------------------------------------------------------

class TestFieldId:
    def test_prefix(self):
        ui = _import_ui()
        assert ui._field_id("model") == "field-model"
        assert ui._field_id("hardware_tier") == "field-hardware_tier"


# ---------------------------------------------------------------------------
# _render_warnings_banner
# ---------------------------------------------------------------------------

class TestRenderWarningsBanner:
    def test_empty_warnings_returns_empty(self):
        ui = _import_ui()
        assert ui._render_warnings_banner([]) == []

    def test_renders_banners_for_each_warning(self, _mock_dependencies):
        ui = _import_ui()
        EnvironmentWarning = _mock_dependencies["state"].EnvironmentWarning
        warnings = [
            EnvironmentWarning(level="info", message="Info msg", action="Do this"),
            EnvironmentWarning(level="warning", message="Warn msg", action="Fix this"),
            EnvironmentWarning(level="error", message="Error msg", action="Urgent"),
        ]
        banners = ui._render_warnings_banner(warnings)
        assert len(banners) == 3


# ---------------------------------------------------------------------------
# _render_domino_status
# ---------------------------------------------------------------------------

class TestRenderDominoStatus:
    def test_renders_idle_when_no_record(self, _mock_dependencies):
        ui = _import_ui()
        result = ui._render_domino_status(None)
        assert result is not None

    def test_renders_running_job(self, _mock_dependencies):
        ui = _import_ui()
        DominoJobRecord = _mock_dependencies["state"].DominoJobRecord
        record = DominoJobRecord(
            id="job-1", owner_id="alice", status="running",
            domino_run_id="run-1", job_url="https://domino/jobs/1",
            submitted_at="2026-01-01T00:00:00",
            domino_status="Executing",
        )
        result = ui._render_domino_status(record)
        assert result is not None

    def test_renders_queued_with_banner(self, _mock_dependencies):
        ui = _import_ui()
        DominoJobRecord = _mock_dependencies["state"].DominoJobRecord
        record = DominoJobRecord(id="job-2", owner_id="alice", status="queued")
        result = ui._render_domino_status(record)
        assert result is not None

    def test_renders_succeeded_job(self, _mock_dependencies):
        ui = _import_ui()
        DominoJobRecord = _mock_dependencies["state"].DominoJobRecord
        record = DominoJobRecord(
            id="job-3", owner_id="alice", status="succeeded",
            submitted_at="2026-01-01T00:00:00",
            completed_at="2026-01-01T01:00:00",
            domino_status="Succeeded",
        )
        result = ui._render_domino_status(record)
        assert result is not None


class TestValidateStudioComputeEnvironment:
    def test_missing_both_env_vars(self, monkeypatch, _mock_dependencies):
        monkeypatch.delenv("DOMINO_ENVIRONMENT_ID", raising=False)
        monkeypatch.delenv("DOMINO_ENVIRONMENT_REVISION_ID", raising=False)
        ui = _import_ui()
        out = ui.validate_studio_domino_compute_environment(MagicMock())
        assert len(out) == 2
        assert "administrator" in " ".join(out).lower()

    def test_revision_not_accessible(self, monkeypatch, _mock_dependencies):
        monkeypatch.setenv("DOMINO_ENVIRONMENT_ID", "e1")
        monkeypatch.setenv("DOMINO_ENVIRONMENT_REVISION_ID", "need-this")
        mock_c = MagicMock()
        mock_c.list_environment_revisions.return_value = [{"id": "other-rev"}]
        ui = _import_ui()
        out = ui.validate_studio_domino_compute_environment(mock_c)
        mock_c.list_environment_revisions.assert_called_once_with("e1")
        assert len(out) == 2

    def test_api_raises_returns_friendly(self, monkeypatch, _mock_dependencies):
        monkeypatch.setenv("DOMINO_ENVIRONMENT_ID", "e1")
        monkeypatch.setenv("DOMINO_ENVIRONMENT_REVISION_ID", "r1")
        mock_c = MagicMock()
        mock_c.list_environment_revisions.side_effect = RuntimeError("network")
        ui = _import_ui()
        out = ui.validate_studio_domino_compute_environment(mock_c)
        assert len(out) == 2
        assert "try again" in " ".join(out).lower()

    def test_ok_empty_list(self, monkeypatch, _mock_dependencies):
        monkeypatch.setenv("DOMINO_ENVIRONMENT_ID", "e1")
        monkeypatch.setenv("DOMINO_ENVIRONMENT_REVISION_ID", "r1")
        mock_c = MagicMock()
        mock_c.list_environment_revisions.return_value = [{"id": "r1", "number": 1}]
        ui = _import_ui()
        assert ui.validate_studio_domino_compute_environment(mock_c) == []


# ---------------------------------------------------------------------------
# _render_job_history_table
# ---------------------------------------------------------------------------
class TestStudioPageInsightBanner:
    def test_insight_card_is_single_full_width_banner_before_grid(self):
        root = Path(__file__).resolve().parent.parent
        src = (root / "auto_model_docs" / "web_app_studio.py").read_text()
        scripts = (root / "auto_model_docs" / "studio" / "scripts.py").read_text()
        styles = (root / "auto_model_docs" / "studio" / "styles.py").read_text()
        assert 'id="wizard-step1"' in src
        assert 'id="template-preview-empty"' in src
        assert "access_log=False" in src
        assert "validate_studio_domino_compute_environment" in src
        assert "studio-compute-env-json" in src
        assert "loadBuiltinTemplates" in scripts
        assert "loadYamlTemplatePreview" in scripts
        assert ".preview-yaml-pre" in styles


class TestInfoTooltipLayer:
    def test_floating_tooltip_layer_escapes_overflow(self):
        root = Path(__file__).resolve().parent.parent
        styles = (root / "auto_model_docs" / "studio" / "styles.py").read_text()
        scripts = (root / "auto_model_docs" / "studio" / "scripts.py").read_text()
        assert "#studio-info-tooltip" in styles
        assert "position: fixed" in styles
        assert "#studio-info-tooltip.visible" in styles
        assert "studio-info-tooltip" in scripts
        assert "closest('.info-tooltip')" in scripts


class TestStudioTwoStepLayout:
    def test_configure_and_history_two_columns_two_steps(self):
        root = Path(__file__).resolve().parent.parent
        web = (root / "auto_model_docs" / "web_app_studio.py").read_text()
        styles = (root / "auto_model_docs" / "studio" / "styles.py").read_text()
        assert 'id="wizard-step1"' in web
        assert 'id="wizard-step2"' in web
        assert "Choose a template" in web
        assert 'id="generate-btn"' in web
        assert "adv-opts-overlay" in web
        assert "wizard-layout" in web or ".wizard-layout" in styles


class TestSpecFileBrowserUi:
    def test_spec_list_fixed_height_and_parent_nav_in_scripts(self):
        root = Path(__file__).resolve().parent.parent
        styles = (root / "auto_model_docs" / "studio" / "styles.py").read_text()
        scripts = (root / "auto_model_docs" / "studio" / "scripts.py").read_text()
        web = (root / "auto_model_docs" / "web_app_studio.py").read_text()
        assert "calc(5 * var(--spec-file-row))" in styles
        assert "specParentPath" in scripts
        assert "spec-file-parent" in scripts
        assert "spec-file-icon" in scripts
        assert "udcc1" in scripts
        assert "data-parent" in scripts
        assert ".spec-file-list > .spec-file-item:last-of-type" in styles
        assert "spec-file-list-pending" in scripts
        assert "spec-file-list-pending" in styles
        assert 'id="spec-file-list"' in web
        assert 'id="field-spec_path"' in web
        assert "absoluteSpecFromRelative" in scripts
        assert "<th>Documents</th>" in scripts
        assert "renderJobHistory" in scripts
        assert "field-environment_id" not in web
        assert "environment-revision-slot" not in web
        assert "adv-opts-overlay" in web
        assert "adv-opts-open-btn" in scripts
        assert "gear-settings-btn" not in web
        assert "gear-popover" not in web
        assert 'id="field-model"' in web
        assert "DEFAULT_OPENAI_MODEL" in web
        assert 'id="spec-yaml-upload"' in web
        assert web.index('id="field-spec_path"') < web.index('id="spec-yaml-upload"')
        assert web.index('id="spec-yaml-upload"') < web.index('id="spec-file-list"')
        assert 'id="generate-btn"' in web
        assert ".wizard-generate-btn" in styles

    def test_spec_dataset_select_excludes_autodoc_name(self):
        root = Path(__file__).resolve().parent.parent
        scripts_src = (root / "auto_model_docs" / "studio" / "scripts.py").read_text()
        from dataset_manager import AUTODOC_DATASET_NAME

        assert AUTODOC_DATASET_NAME == "autodoc"
        assert "datasets[i].name === 'autodoc'" in scripts_src

    def test_template_gallery_uses_template_uid(self):
        root = Path(__file__).resolve().parent.parent
        scripts_src = (root / "auto_model_docs" / "studio" / "scripts.py").read_text()
        assert "data-uid" in scripts_src


class TestResultsPanelNoRerenderInTerminalState:
    def test_results_panel_skips_rerender_for_same_terminal_job(self):
        root = Path(__file__).resolve().parent.parent
        scripts_src = (root / "auto_model_docs" / "studio" / "scripts.py").read_text()
        assert "_lastResultsPanelKey" in scripts_src
        assert "panelKey === _lastResultsPanelKey" in scripts_src
        assert "isTerminal" in scripts_src
        assert "_selectedTemplateUid" in scripts_src


class TestLandingDocPreviewRestoresEditYaml:
    def test_close_landing_preview_restores_edit_template_yaml(self):
        root = Path(__file__).resolve().parent.parent
        scripts_src = (root / "auto_model_docs" / "studio" / "scripts.py").read_text()
        assert "_landingPreviewOriginalEditYaml" in scripts_src
        assert "edit-template-yaml" in scripts_src
        assert "_landingPreviewOriginalEditYaml = null" in scripts_src
        assert "editArea.value = _landingPreviewOriginalEditYaml" in scripts_src


class TestGovernanceBundlePickerOptgroups:
    def test_bundle_select_groups_by_model_with_optgroup(self):
        root = Path(__file__).resolve().parent.parent
        scripts_src = (root / "auto_model_docs" / "studio" / "scripts.py").read_text()
        assert "_groupBundlesByModel" in scripts_src
        assert "_renderGovernanceBundleSelectOptions" in scripts_src
        assert "_bundleLeafLabel" in scripts_src
        assert "<optgroup label=" in scripts_src
        assert "_renderGovernanceBundleSelectOptions(bundles, _selectedBundleId)" in scripts_src
        assert "_bundleAutoLabel" in scripts_src
        assert "_firstVisibleBundle" in scripts_src
        assert "no governance context" in scripts_src
        assert "_GOVERNANCE_BUNDLE_INFO_MSG" in scripts_src
        assert "_updateBundleInfoNotice" in scripts_src
        assert "_bundlesForContext" not in scripts_src
        assert "_bundleMatchesModelNameFilters" not in scripts_src
        assert "filter-model-names" in scripts_src
        assert "applyGovernanceBundleSelection" in scripts_src

    def test_model_name_filter_not_live_wired_to_bundle_picker(self):
        root = Path(__file__).resolve().parent.parent
        scripts_src = (root / "auto_model_docs" / "studio" / "scripts.py").read_text()
        assert "filter-model-names" in scripts_src
        assert "addEventListener('input', applyGovernanceBundleSelection)" not in scripts_src
        assert "addEventListener('change', applyGovernanceBundleSelection)" not in scripts_src

    def test_model_name_filter_prefilled_from_model_id_url(self):
        root = Path(__file__).resolve().parent.parent
        scripts_src = (root / "auto_model_docs" / "studio" / "scripts.py").read_text()
        assert "_prefillModelNameFilterFromUrl" in scripts_src
        assert "resolvedModelId()" in scripts_src
        assert "_prefillModelNameFilterFromUrl();" in scripts_src

    def test_governance_bundle_select_always_shown(self):
        root = Path(__file__).resolve().parent.parent
        scripts_src = (root / "auto_model_docs" / "studio" / "scripts.py").read_text()
        assert "_defaultBundleId" in scripts_src
        assert "visible.length === 1" not in scripts_src
        assert "select.style.display = 'none'" not in scripts_src

    def test_model_id_preselects_first_matching_bundle(self):
        root = Path(__file__).resolve().parent.parent
        scripts_src = (root / "auto_model_docs" / "studio" / "scripts.py").read_text()
        assert "_bundleContainsModel" in scripts_src
        assert "_defaultBundleId" in scripts_src
        assert "resolvedModelId()" in scripts_src

    def test_generate_not_blocked_when_bundle_none_selected(self):
        root = Path(__file__).resolve().parent.parent
        scripts_src = (root / "auto_model_docs" / "studio" / "scripts.py").read_text()
        assert "visible.length > 0 && !_selectedBundleId" not in scripts_src

    def test_governance_bundle_hint_info_style(self):
        root = Path(__file__).resolve().parent.parent
        styles = (root / "auto_model_docs" / "studio" / "styles.py").read_text()
        assert "governance-bundle-hint-info" in styles

    def test_filters_accordion_open_by_default(self):
        root = Path(__file__).resolve().parent.parent
        web = (root / "auto_model_docs" / "web_app_studio.py").read_text()
        # "open=" is on the Details wrapper, not necessarily near "filters-body"
        assert "cls=\"adv-opts-accordion\"" in web
        assert "open=False" in web

    def test_doc_scope_separator_exists(self):
        root = Path(__file__).resolve().parent.parent
        web = (root / "auto_model_docs" / "web_app_studio.py").read_text()
        assert 'Hr(cls="doc-scope-separator")' in web
