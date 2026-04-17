"""Tests for domino_client.py — current REST-based API (no SDK dependency).

Covers: list_hardware_tiers, list_self_environments, list_environment_revisions,
get_project_default_tier,
get_job_status, stop_job, set_ui_host, build_job_url, build_autodoc_dataset_data_page_url,
resolve_project, submit_job with current signatures.
"""

from __future__ import annotations

import os
import sys
from unittest.mock import MagicMock, patch

import pytest

_repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_pkg_dir = os.path.join(_repo_root, "auto_model_docs")
for p in (_repo_root, _pkg_dir):
    if p not in sys.path:
        sys.path.insert(0, p)

import domino_auth
import domino_client as dc


@pytest.fixture(autouse=True)
def _setup_env(monkeypatch):
    monkeypatch.delenv("DOMINO_API_PROXY", raising=False)
    monkeypatch.setenv("DOMINO_USER_HOST", "https://domino.example.com")
    monkeypatch.setenv("DOMINO_USER_API_KEY", "test-api-key")
    monkeypatch.setenv("DOMINO_PROJECT_ID", "proj-123")
    monkeypatch.setenv("DOMINO_PROJECT_OWNER", "test_owner")
    monkeypatch.setenv("DOMINO_PROJECT_NAME", "test_project")
    # Clear caches
    dc._project_cache.clear()
    domino_auth.reset_ui_host()
    yield


# ---------------------------------------------------------------------------
# Host resolution — _resolve_api_host is re-exported from domino_auth
# ---------------------------------------------------------------------------

class TestHostResolution:
    def test_api_host(self):
        assert dc._resolve_api_host() == "https://domino.example.com"

    def test_api_host_strips_trailing_slash(self, monkeypatch):
        monkeypatch.setenv("DOMINO_USER_HOST", "https://domino.example.com/")
        assert dc._resolve_api_host() == "https://domino.example.com"


# ---------------------------------------------------------------------------
# list_hardware_tiers
# ---------------------------------------------------------------------------

class TestListHardwareTiers:
    @patch.object(dc, "_domino_request")
    def test_parses_tiers(self, mock_req):
        mock_req.return_value = [
            {"hardwareTier": {"id": "small", "name": "Small", "hwtFlags": {"isDefault": True}}},
            {"hardwareTier": {"id": "large", "name": "Large GPU", "hwtFlags": {"isDefault": False}}},
        ]
        tiers = dc.list_hardware_tiers(project_id="proj-123")
        assert len(tiers) == 2
        assert tiers[0]["id"] == "small"
        assert tiers[0]["name"] == "Small"
        assert tiers[0]["isDefault"] is True
        assert tiers[0]["option_label"] == "Small"
        assert tiers[1]["id"] == "large"
        assert tiers[1]["isDefault"] is False

    @patch.object(dc, "_domino_request")
    def test_nested_data_format(self, mock_req):
        mock_req.return_value = {"hardwareTiers": [
            {"id": "medium", "name": "Medium"},
        ]}
        tiers = dc.list_hardware_tiers(project_id="proj-123")
        assert len(tiers) == 1
        assert tiers[0]["id"] == "medium"
        assert tiers[0]["option_label"] == "Medium"

    @patch.object(dc, "_domino_request")
    def test_option_label_includes_specs_capacity_price(self, mock_req):
        mock_req.return_value = [
            {
                "hardwareTier": {
                    "id": "small-k8s",
                    "name": "Small",
                    "hwtFlags": {"isDefault": True},
                    "hwtResources": {
                        "cores": 1,
                        "memory": {"value": 4, "unit": "GiB"},
                    },
                    "gpuConfiguration": {"numberOfGpus": 0, "gpuKey": "nvidia.com/gpu"},
                    "centsPerMinute": 0.01,
                },
                "capacity": {"capacityLevel": "CAN_EXECUTE_WITH_CURRENT_INSTANCES"},
            },
        ]
        tiers = dc.list_hardware_tiers(project_id="proj-123")
        assert len(tiers) == 1
        ol = tiers[0]["option_label"]
        assert tiers[0]["capacity_label"] == "< 1 MIN"
        assert "Small" in ol
        assert "1 core" in ol
        assert "$0.0001/min" in ol
        assert "< 1 MIN" in ol

    @patch.object(dc, "_domino_request")
    def test_option_label_appends_spot_when_enabled(self, mock_req):
        mock_req.return_value = [
            {
                "hardwareTier": {
                    "id": "spot-tier",
                    "name": "Spot tier",
                    "hwtFlags": {"isDefault": False},
                    "hwtResources": {"cores": 1, "memory": {"value": 1, "unit": "GiB"}},
                    "capacityTypeRestrictions": {"enableSpotInstances": True},
                },
                "capacity": {},
            },
        ]
        tiers = dc.list_hardware_tiers(project_id="proj-123")
        assert "Spot" in tiers[0]["option_label"]

    @patch.object(dc, "_domino_request")
    def test_api_error_returns_empty(self, mock_req):
        mock_req.side_effect = RuntimeError("API down")
        assert dc.list_hardware_tiers(project_id="proj-123") == []


# ---------------------------------------------------------------------------
# list_self_environments
# ---------------------------------------------------------------------------

class TestListSelfEnvironments:
    @patch.object(dc, "_domino_request")
    def test_parses_array(self, mock_req):
        mock_req.return_value = [
            {"id": "e1", "name": "Env A"},
        ]
        envs = dc.list_self_environments()
        assert len(envs) == 1
        assert envs[0]["id"] == "e1"
        assert envs[0]["name"] == "Env A"
        mock_req.assert_called_once_with("GET", "/v4/environments/self")

    @patch.object(dc, "_domino_request")
    def test_parses_wrapped(self, mock_req):
        mock_req.return_value = {"environments": [{"id": "e2", "name": "B"}]}
        envs = dc.list_self_environments()
        assert envs[0]["id"] == "e2"

    @patch.object(dc, "_domino_request")
    def test_error_returns_empty(self, mock_req):
        mock_req.side_effect = OSError("net")
        assert dc.list_self_environments() == []


class TestGetDefaultEnvironment:
    @patch.object(dc, "_domino_request")
    def test_returns_environment(self, mock_req):
        mock_req.return_value = {"id": "env-default", "name": "Default Env"}
        result = dc.get_default_environment()
        assert result is not None
        assert result["id"] == "env-default"
        mock_req.assert_called_once_with("GET", "/v4/environments/defaultEnvironment")

    @patch.object(dc, "_domino_request")
    def test_error_returns_none(self, mock_req):
        mock_req.side_effect = RuntimeError("timeout")
        assert dc.get_default_environment() is None


class TestResolveJobEnvironmentDefaults:
    @patch.dict(os.environ, {"DOMINO_ENVIRONMENT_ID": "e1", "DOMINO_ENVIRONMENT_REVISION_ID": "r2"}, clear=False)
    @patch.object(dc, "list_environment_revisions")
    def test_uses_configured_env_and_revision_when_valid(self, mock_revs):
        mock_revs.return_value = [{"id": "r1"}, {"id": "r2"}]
        envs = [{"id": "e1", "name": "Configured"}]
        result = dc.resolve_job_environment_defaults(env_list=envs)
        assert result == {"environment_id": "e1", "environment_revision_id": "r2"}

    @patch.dict(os.environ, {"DOMINO_ENVIRONMENT_ID": "e1", "DOMINO_ENVIRONMENT_REVISION_ID": "bad"}, clear=False)
    @patch.object(dc, "list_environment_revisions")
    def test_uses_latest_revision_when_configured_revision_invalid(self, mock_revs):
        mock_revs.return_value = [{"id": "r9"}, {"id": "r8"}]
        envs = [{"id": "e1", "name": "Configured"}]
        result = dc.resolve_job_environment_defaults(env_list=envs)
        assert result == {"environment_id": "e1", "environment_revision_id": "r9"}

    @patch.dict(os.environ, {}, clear=True)
    @patch.object(dc, "get_default_environment")
    @patch.object(dc, "list_environment_revisions")
    def test_falls_back_to_user_default_environment(self, mock_revs, mock_default):
        mock_default.return_value = {"id": "e-default", "name": "Default"}
        mock_revs.return_value = [{"id": "r1"}]
        envs = [{"id": "e-default", "name": "Default"}, {"id": "e-other", "name": "Other"}]
        result = dc.resolve_job_environment_defaults(env_list=envs)
        assert result == {"environment_id": "e-default", "environment_revision_id": "r1"}

    @patch.dict(os.environ, {}, clear=True)
    @patch.object(dc, "get_default_environment", return_value=None)
    @patch.object(dc, "list_environment_revisions")
    def test_falls_back_to_first_self_environment(self, mock_revs, _mock_default):
        mock_revs.return_value = [{"id": "r-first"}]
        envs = [{"id": "e-first", "name": "First"}, {"id": "e-second", "name": "Second"}]
        result = dc.resolve_job_environment_defaults(env_list=envs)
        assert result == {"environment_id": "e-first", "environment_revision_id": "r-first"}


# ---------------------------------------------------------------------------
# list_environment_revisions
# ---------------------------------------------------------------------------

class TestListEnvironmentRevisions:
    @patch.object(dc, "_domino_request")
    def test_parses_revisions(self, mock_req):
        mock_req.return_value = {
            "revisions": [
                {"id": "rid1", "number": 1, "created": 1713600000000},
                {"id": "rid2", "number": 2, "created": 1713700000000},
            ],
        }
        revs = dc.list_environment_revisions("env123")
        mock_req.assert_called_once_with(
            "GET",
            "/v4/environments/env123/page/0/pageSize/1000/revisions",
        )
        assert len(revs) == 2
        assert revs[0]["id"] == "rid2"
        assert revs[0]["number"] == 2
        assert "option_label" in revs[0]

    @patch.object(dc, "_domino_request")
    def test_empty_id_returns_empty(self, mock_req):
        assert dc.list_environment_revisions("") == []
        mock_req.assert_not_called()

    def test_no_project_id_returns_empty(self):
        assert dc.list_hardware_tiers(project_id=None) == []

    @patch.object(dc, "_domino_request")
    def test_cross_project(self, mock_req):
        mock_req.return_value = []
        dc.list_hardware_tiers(project_id="other-proj")
        # Verify it called with the project ID in the path
        call_path = mock_req.call_args.args[1]
        assert "other-proj" in call_path


# ---------------------------------------------------------------------------
# get_project_default_tier
# ---------------------------------------------------------------------------

class TestGetProjectDefaultTier:
    def test_env_override(self, monkeypatch):
        monkeypatch.setenv("AUTODOC_DEFAULT_HARDWARE_TIER", "gpu-xl")
        assert dc.get_project_default_tier() == "gpu-xl"

    def test_domino_env(self, monkeypatch):
        monkeypatch.delenv("AUTODOC_DEFAULT_HARDWARE_TIER", raising=False)
        monkeypatch.setenv("DOMINO_HARDWARE_TIER_ID", "small-k8s")
        assert dc.get_project_default_tier() == "small-k8s"

    def test_none_when_unset(self, monkeypatch):
        monkeypatch.delenv("AUTODOC_DEFAULT_HARDWARE_TIER", raising=False)
        monkeypatch.delenv("DOMINO_HARDWARE_TIER_ID", raising=False)
        assert dc.get_project_default_tier() is None


# ---------------------------------------------------------------------------
# get_job_status
# ---------------------------------------------------------------------------

class TestGetJobStatus:
    @patch.object(dc, "_domino_request")
    def test_succeeded(self, mock_req):
        mock_req.return_value = {"statuses": {"executionStatus": "Succeeded"}}
        result = dc.get_job_status("run-1")
        assert result["local_status"] == "succeeded"
        assert result["domino_status"] == "Succeeded"

    @patch.object(dc, "_domino_request")
    def test_failed(self, mock_req):
        mock_req.return_value = {"statuses": {"executionStatus": "Failed"}}
        result = dc.get_job_status("run-1")
        assert result["local_status"] == "failed"

    @patch.object(dc, "_domino_request")
    def test_running(self, mock_req):
        mock_req.return_value = {"statuses": {"executionStatus": "Executing"}}
        result = dc.get_job_status("run-1")
        assert result["local_status"] == "running"

    @patch.object(dc, "_domino_request")
    def test_cancelled(self, mock_req):
        mock_req.return_value = {"statuses": {"executionStatus": "Stopped"}}
        result = dc.get_job_status("run-1")
        assert result["local_status"] == "cancelled"

    @patch.object(dc, "_domino_request")
    def test_pending(self, mock_req):
        mock_req.return_value = {"statuses": {"executionStatus": "Queued"}}
        result = dc.get_job_status("run-1")
        # "queued" maps to _PENDING_STATUSES → "pending"
        assert result["local_status"] == "pending"

    @patch.object(dc, "_domino_request")
    def test_api_error_returns_unknown(self, mock_req):
        mock_req.side_effect = RuntimeError("timeout")
        result = dc.get_job_status("run-1")
        assert result["local_status"] == "unknown"
        assert result["domino_status"] == "unknown"

    @patch.object(dc, "_domino_request")
    def test_fallback_status_field(self, mock_req):
        mock_req.return_value = {"status": "Completed"}
        result = dc.get_job_status("run-1")
        assert result["local_status"] == "succeeded"


# ---------------------------------------------------------------------------
# stop_job
# ---------------------------------------------------------------------------

class TestStopJob:
    @patch.object(dc, "_domino_request")
    def test_calls_api(self, mock_req):
        dc.stop_job("run-1", project_id="proj-123")
        mock_req.assert_called_once_with(
            "POST", "/v4/jobs/stop",
            json={"jobId": "run-1", "commitResults": True, "projectId": "proj-123"},
        )

    def test_raises_without_project_id(self):
        with pytest.raises(ValueError, match="project_id is required"):
            dc.stop_job("run-1")

    @patch.object(dc, "_domino_request")
    def test_api_error_is_swallowed(self, mock_req):
        mock_req.side_effect = RuntimeError("already stopped")
        dc.stop_job("run-1", project_id="proj-123")  # should not raise


# ---------------------------------------------------------------------------
# set_ui_host / build_job_url
# ---------------------------------------------------------------------------

class TestSetUiHost:
    def test_basic(self):
        domino_auth.set_ui_host("example.domino.tech")
        assert domino_auth.resolve_ui_host() == "https://example.domino.tech"

    def test_strips_apps_prefix(self):
        domino_auth.set_ui_host("apps.domino.example.com")
        assert domino_auth.resolve_ui_host() == "https://domino.example.com"

    def test_with_scheme(self):
        domino_auth.set_ui_host("https://custom.host:8443")
        assert domino_auth.resolve_ui_host() == "https://custom.host:8443"

    def test_caches_first_value(self):
        domino_auth.set_ui_host("first.example.com")
        domino_auth.set_ui_host("second.example.com")
        assert "first" in domino_auth.resolve_ui_host()

    def test_empty_is_noop(self):
        domino_auth.set_ui_host("")
        assert domino_auth.resolve_ui_host() == "https://domino.example.com"


class TestBuildJobUrl:
    def test_builds_url(self):
        domino_auth.set_ui_host("domino.example.com")
        # build_job_url uses get_project_context which needs resolve_project
        with patch.object(dc, "get_project_context", return_value=("proj-123", "test_project", "test_owner")):
            url = dc.build_job_url("run-123", project_id="proj-123")
        assert url == "https://domino.example.com/jobs/test_owner/test_project/run-123/logs?status=all"

    def test_none_without_ui_host(self, monkeypatch):
        monkeypatch.delenv("DOMINO_USER_HOST", raising=False)
        assert dc.build_job_url("run-123", project_id="proj-123") is None

    @patch.object(dc, "resolve_project")
    def test_with_cross_project(self, mock_resolve):
        domino_auth.set_ui_host("domino.example.com")
        mock_resolve.return_value = dc.ProjectInfo(
            id="other-proj", name="other-model", owner_username="bob",
        )
        url = dc.build_job_url("run-456", project_id="other-proj")
        assert "/bob/other-model/" in url


class TestBuildAutodocDatasetDataPageUrl:
    def test_builds_url(self):
        domino_auth.set_ui_host("domino.example.com")
        with patch.object(dc, "get_project_context", return_value=("proj-123", "test_project", "test_owner")):
            url = dc.build_autodoc_dataset_data_page_url("proj-123", "ds-uuid-1")
        assert url == "https://domino.example.com/u/test_owner/test_project/data/rw/upload/autodoc/ds-uuid-1/docs"

    def test_none_without_ui_host(self, monkeypatch):
        monkeypatch.delenv("DOMINO_USER_HOST", raising=False)
        assert dc.build_autodoc_dataset_data_page_url("proj-123", "ds-1") is None

    def test_none_empty_dataset_id(self):
        domino_auth.set_ui_host("domino.example.com")
        assert dc.build_autodoc_dataset_data_page_url("proj-123", "  ") is None


# ---------------------------------------------------------------------------
# resolve_project
# ---------------------------------------------------------------------------

class TestResolveProject:
    @patch.object(dc, "_domino_request")
    def test_caches_result(self, mock_req):
        mock_req.return_value = {"name": "my-model", "ownerUsername": "alice"}
        info1 = dc.resolve_project("proj-abc")
        info2 = dc.resolve_project("proj-abc")
        assert info1 is info2
        assert mock_req.call_count == 1  # cached

    @patch.object(dc, "_domino_request")
    def test_returns_project_info(self, mock_req):
        mock_req.return_value = {"name": "my-model", "ownerUsername": "alice"}
        info = dc.resolve_project("proj-abc")
        assert info.name == "my-model"
        assert info.owner_username == "alice"

    @patch.object(dc, "_domino_request")
    def test_returns_none_on_missing_fields(self, mock_req):
        mock_req.return_value = {"name": "my-model"}  # no owner
        info = dc.resolve_project("proj-missing")
        assert info is None

    @patch.object(dc, "_domino_request")
    def test_returns_none_on_api_error(self, mock_req):
        mock_req.side_effect = Exception("network error")
        info = dc.resolve_project("proj-err")
        assert info is None


# ---------------------------------------------------------------------------
# submit_job
# ---------------------------------------------------------------------------

class TestSubmitJob:
    @patch.object(dc, "get_project_context", return_value=("proj-123", "test_project", "test_owner"))
    @patch.object(dc, "_domino_request")
    def test_returns_run_id(self, mock_req, _mock_ctx):
        mock_req.return_value = {"id": "run-abc"}
        run_id = dc.submit_job(
            "python main.py", "main", "", "proj-123", "", "",
        )
        assert run_id == "run-abc"

    @patch.object(dc, "get_project_context", return_value=("proj-123", "test_project", "test_owner"))
    @patch.object(dc, "_domino_request")
    def test_includes_branch(self, mock_req, _mock_ctx):
        mock_req.return_value = {"id": "run-1"}
        dc.submit_job("python main.py", "feature/x", "", "proj-123", "", "")
        payload = mock_req.call_args.kwargs["json"]
        assert payload["mainRepoGitRef"] == {"type": "branches", "value": "feature/x"}

    @patch.object(dc, "get_project_context", return_value=("proj-123", "test_project", "test_owner"))
    @patch.object(dc, "_domino_request")
    def test_no_branch(self, mock_req, _mock_ctx):
        mock_req.return_value = {"id": "run-1"}
        dc.submit_job("python main.py", None, "", "proj-123", "", "")
        payload = mock_req.call_args.kwargs["json"]
        assert "mainRepoGitRef" not in payload

    @patch.object(dc, "get_project_context", return_value=("proj-123", "test_project", "test_owner"))
    @patch.object(dc, "_domino_request")
    def test_includes_tier(self, mock_req, _mock_ctx):
        mock_req.return_value = {"id": "run-1"}
        dc.submit_job("python main.py", None, "gpu-large", "proj-123", "", "")
        payload = mock_req.call_args.kwargs["json"]
        assert payload["overrideHardwareTierId"] == "gpu-large"

    @patch.object(dc, "get_project_context", return_value=("proj-123", "test_project", "test_owner"))
    @patch.object(dc, "_domino_request")
    def test_raises_on_missing_run_id(self, mock_req, _mock_ctx):
        mock_req.return_value = {"unexpected": "response"}
        with pytest.raises(ValueError, match="unexpected response"):
            dc.submit_job("python main.py", None, "", "proj-123", "", "")

    def test_raises_on_no_project(self):
        with pytest.raises(ValueError, match="project_id is required"):
            dc.submit_job("python main.py", None, "", "", "", "")

    @patch.object(dc, "get_project_context", return_value=("proj-123", "test_project", "test_owner"))
    @patch.object(dc, "_domino_request")
    def test_retry_without_git_ref(self, mock_req, _mock_ctx):
        """If branch-pinned start fails, retries without mainRepoGitRef.

        Note: the payload dict is mutated in-place (pop) before the retry,
        so both call_args entries share the same dict reference.  We verify
        the retry happened (2 calls) and the final payload lacks the key.
        """
        call_count = 0
        def side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise RuntimeError("bad ref")
            return {"id": "run-retry"}

        mock_req.side_effect = side_effect
        run_id = dc.submit_job("python main.py", "bad-branch", "", "proj-123", "", "")
        assert run_id == "run-retry"
        assert mock_req.call_count == 2
        # Final payload (shared reference) should not have mainRepoGitRef
        final_payload = mock_req.call_args.kwargs["json"]
        assert "mainRepoGitRef" not in final_payload


# ---------------------------------------------------------------------------
# download_artifact_at_head
# ---------------------------------------------------------------------------

class TestDownloadArtifactAtHead:
    @patch.object(dc, "_get_auth_headers", return_value={})
    @patch.object(dc, "get_project_context", return_value=("proj-123", "test_project", "test_owner"))
    @patch.object(dc, "_resolve_ui_host", return_value="https://nucleus.example.com")
    def test_logs_on_http_404(self, _mock_host, _mock_ctx, _mock_auth, caplog):
        import logging
        mock_resp = MagicMock()
        mock_resp.status_code = 404
        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.get.return_value = mock_resp

        with patch("httpx.Client", return_value=mock_client):
            with caplog.at_level(logging.WARNING):
                result = dc.download_artifact_at_head("proj-123", "docs/6a4e6b6d/model_docs.docx")

        assert result is None
        assert any("download_artifact_at_head not found" in r.message for r in caplog.records)
        assert any("http_status=404" in r.message for r in caplog.records)
        assert any("owner=test_owner" in r.message for r in caplog.records)
        assert any("project=test_project" in r.message for r in caplog.records)

    @patch.object(dc, "_resolve_ui_host", return_value=None)
    def test_logs_when_ui_host_missing(self, _mock_host, caplog):
        import logging
        with caplog.at_level(logging.WARNING):
            result = dc.download_artifact_at_head("proj-123", "docs/foo/model_docs.docx")
        assert result is None
        assert any("ui host not configured" in r.message for r in caplog.records)

    @patch.object(dc, "_get_auth_headers", return_value={})
    @patch.object(dc, "get_project_context", return_value=("proj-123", "test_project", "test_owner"))
    def test_uses_ui_host_not_api_proxy(self, _mock_ctx, _mock_auth, monkeypatch):
        domino_auth.set_ui_host("apps.nucleus.example.com")
        monkeypatch.setenv("DOMINO_API_PROXY", "http://localhost:8899")
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.content = b"docx"
        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.get.return_value = mock_resp

        with patch("httpx.Client", return_value=mock_client):
            result = dc.download_artifact_at_head("proj-123", "docs/abc/model_docs.docx")

        assert result == b"docx"
        called_url = mock_client.get.call_args[0][0]
        assert called_url.startswith("https://nucleus.example.com/u/test_owner/test_project/raw/latest/")
        assert "localhost" not in called_url
