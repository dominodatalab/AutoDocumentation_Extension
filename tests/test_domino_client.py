"""Tests for cross-project Domino integration in domino_client.

Functions under test: resolve_project, _domino_request, get_project_context,
submit_job.  Tests mock httpx at the transport layer so they run without a
live Domino API.
"""

from __future__ import annotations

import json
import os
import shlex
import sys
from dataclasses import dataclass
from typing import Any
from unittest.mock import MagicMock, patch

import httpx
import pytest

# Ensure auto_model_docs is importable (bare module names like domino_client)
_repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_pkg_dir = os.path.join(_repo_root, "auto_model_docs")
for p in (_repo_root, _pkg_dir):
    if p not in sys.path:
        sys.path.insert(0, p)

import domino_client as dc
from domino_client import (
    resolve_project,
    _domino_request,
    get_project_context,
    submit_job,
    browse_code,
    get_project_code_root,
    get_code_source_info,
    browse_gbp_code,
    browse_dfs_code,
    read_gbp_file_raw,
)

# No skip markers needed — all functions now exist in domino_client


@pytest.fixture(autouse=True)
def _setup_env(monkeypatch):
    monkeypatch.setenv("DOMINO_API_HOST", "https://domino.example.com")
    monkeypatch.setenv("DOMINO_USER_API_KEY", "test-api-key")
    monkeypatch.setenv("DOMINO_PROJECT_ID", "proj-123")
    monkeypatch.setenv("DOMINO_PROJECT_OWNER", "test_owner")
    monkeypatch.setenv("DOMINO_PROJECT_NAME", "test_project")
    dc._project_cache.clear()
    yield


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _json_response(data: dict, status: int = 200) -> httpx.Response:
    """Build a fake httpx.Response with JSON body."""
    return httpx.Response(
        status_code=status,
        json=data,
        request=httpx.Request("GET", "https://domino.example.com/test"),
    )


def _text_response(text: str, status: int = 200) -> httpx.Response:
    """Build a fake httpx.Response with plain-text body (for JSON-decode failures)."""
    return httpx.Response(
        status_code=status,
        text=text,
        request=httpx.Request("GET", "https://domino.example.com/test"),
    )


_SAMPLE_PROJECT_RESP = {
    "id": "507f1f77bcf86cd799439011",
    "name": "my-model",
    "owner": {"userName": "alice"},
}


# ===================================================================
# resolve_project() tests
# ===================================================================

class TestResolveProject:
    """Tests for resolve_project(project_id) → ProjectInfo | None.

    The current resolve_project is synchronous and returns None on failure
    (no typed exceptions). It uses _domino_request internally.
    """

    def test_cache_hit_returns_cached(self):
        """Second call for same ID returns cached ProjectInfo without API call."""
        with patch.object(dc, "_domino_request") as mock_req:
            mock_req.return_value = _SAMPLE_PROJECT_RESP
            with patch.dict(dc._project_cache, {}, clear=True):
                first = resolve_project("507f1f77bcf86cd799439011")
                second = resolve_project("507f1f77bcf86cd799439011")

        assert first.name == second.name == "my-model"
        assert first is second  # cached
        assert mock_req.call_count == 1

    def test_cache_miss_calls_api(self):
        """First call for an ID hits the API and caches the result."""
        with patch.object(dc, "_domino_request") as mock_req:
            mock_req.return_value = _SAMPLE_PROJECT_RESP
            with patch.dict(dc._project_cache, {}, clear=True):
                info = resolve_project("507f1f77bcf86cd799439011")

        assert info.id == "507f1f77bcf86cd799439011"
        assert info.name == "my-model"
        assert info.owner_username == "alice"

    def test_api_error_returns_none(self):
        """Network/API errors return None (no typed exceptions)."""
        with patch.object(dc, "_domino_request") as mock_req:
            mock_req.side_effect = Exception("network error")
            with patch.dict(dc._project_cache, {}, clear=True):
                info = resolve_project("000000000000000000000000")

        assert info is None

    def test_missing_name_returns_none(self):
        """Response with missing 'name' field should return None."""
        bad_resp = {"id": "507f1f77bcf86cd799439011", "owner": {"userName": "alice"}}
        with patch.object(dc, "_domino_request") as mock_req:
            mock_req.return_value = bad_resp
            with patch.dict(dc._project_cache, {}, clear=True):
                info = resolve_project("507f1f77bcf86cd799439011")

        assert info is None

    def test_missing_owner_returns_none(self):
        """Response with missing 'owner' field should return None."""
        bad_resp = {"id": "507f1f77bcf86cd799439011", "name": "my-model"}
        with patch.object(dc, "_domino_request") as mock_req:
            mock_req.return_value = bad_resp
            with patch.dict(dc._project_cache, {}, clear=True):
                info = resolve_project("507f1f77bcf86cd799439011")

        assert info is None


# ===================================================================
# _domino_request() tests
# ===================================================================

class TestDominoRequest:
    """Tests for the low-level _domino_request() HTTP helper.

    The current implementation is synchronous and uses httpx.Client.
    """

    def test_successful_json_response(self):
        """Successful request returns parsed JSON."""
        import httpx as _httpx

        mock_client = MagicMock()
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"key": "value"}
        mock_resp.raise_for_status = MagicMock()
        mock_client.request.return_value = mock_resp
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)

        with patch("httpx.Client", return_value=mock_client):
            result = _domino_request("GET", "/v4/projects")

        assert result == {"key": "value"}

    def test_4xx_raises_immediately(self):
        """Client errors (4xx) should raise immediately without retrying."""
        import httpx as _httpx

        mock_client = MagicMock()
        mock_resp = MagicMock()
        mock_resp.status_code = 400
        mock_resp.raise_for_status.side_effect = _httpx.HTTPStatusError(
            "400", request=MagicMock(), response=mock_resp,
        )
        mock_client.request.return_value = mock_resp
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)

        with patch("httpx.Client", return_value=mock_client):
            with pytest.raises(_httpx.HTTPStatusError):
                _domino_request("GET", "/v4/projects")

        assert mock_client.request.call_count == 1


# ===================================================================
# get_project_context() tests
# ===================================================================

class TestGetProjectContext:
    """Tests for get_project_context(project_id=...) → tuple.

    Returns (project_id, project_name, owner_username).
    """

    def test_with_project_id_calls_resolve(self):
        """When project_id is provided, resolve_project should be called."""
        mock_info = dc.ProjectInfo(
            id="507f1f77bcf86cd799439011", name="my-model", owner_username="alice",
        )
        with patch.object(dc, "resolve_project", return_value=mock_info) as mock_resolve:
            pid, pname, powner = get_project_context(project_id="507f1f77bcf86cd799439011")

        mock_resolve.assert_called_once_with("507f1f77bcf86cd799439011")
        assert pname == "my-model"
        assert powner == "alice"

    def test_empty_project_id_raises(self):
        with pytest.raises(ValueError, match="project_id is required"):
            get_project_context("")


class TestBrowseCodeAndCodeRootOptions:
    def test_browse_code_get_params(self):
        with patch.object(dc, "_domino_request", return_value={"ok": True}) as mock_req:
            out = browse_code("alice", "myproj", path_string="")
        assert out == {"ok": True}
        mock_req.assert_called_once()
        assert mock_req.call_args[0][:2] == ("GET", "/v4/code/browseCode")
        params = mock_req.call_args.kwargs["params"]
        assert params["ownerUsername"] == "alice"
        assert params["projectName"] == "myproj"
        assert params["pathString"] == "/"

    def test_browse_code_non_empty_path(self):
        with patch.object(dc, "_domino_request", return_value={}) as mock_req:
            browse_code("alice", "myproj", path_string="src/")
        assert mock_req.call_args.kwargs["params"]["pathString"] == "src/"

    def test_code_root_git_based_project(self):
        with patch.object(dc, "browse_code") as mock_browse:
            mock_browse.return_value = {"projectSettings": {"isGitBasedProject": True}}
            result = get_project_code_root("alice", "myproj")
        assert result == "/mnt/code"

    def test_code_root_dfs_project(self):
        with patch.object(dc, "browse_code") as mock_browse:
            mock_browse.return_value = {"projectSettings": {"isGitBasedProject": False}}
            result = get_project_code_root("alice", "myproj")
        assert result == "/mnt"

    def test_code_root_calls_browse_with_empty_path(self):
        with patch.object(dc, "browse_code") as mock_browse:
            mock_browse.return_value = {"projectSettings": {}}
            get_project_code_root("alice", "myproj")
        mock_browse.assert_called_once_with("alice", "myproj", path_string="")


# ===================================================================
# submit_job() tests
# ===================================================================

class TestSubmitJob:
    """Tests for submit_job() — current REST-based implementation."""

    def test_successful_submission_returns_run_id(self):
        """submit_job should return the run ID from the Domino response."""
        with patch.object(dc, "_domino_request") as mock_req:
            mock_req.return_value = {"id": "run-abc-123"}
            run_id = submit_job(
                command=["python", "main.py"],
                branch="main",
                tier_id="small",
                project_id="proj-123",
                environment_id="",
                environment_revision_id="",
            )

        assert run_id == "run-abc-123"

    def test_submit_with_branch_passes_git_ref(self):
        """Branch should be passed as mainRepoGitRef in the payload."""
        with patch.object(dc, "_domino_request") as mock_req:
            mock_req.return_value = {"id": "run-xyz"}
            submit_job(
                command=["python", "main.py"],
                branch="feature/x",
                tier_id="",
                project_id="proj-123",
                environment_id="",
                environment_revision_id="",
            )

        payload = mock_req.call_args.kwargs["json"]
        assert payload["mainRepoGitRef"] == {"type": "branches", "value": "feature/x"}

    def test_no_project_id_raises_value_error(self):
        """When project_id is empty, submit_job should raise."""
        with pytest.raises(ValueError, match="project_id is required"):
            submit_job(
                command=["python", "main.py"],
                branch="main",
                tier_id="",
                project_id="",
                environment_id="",
                environment_revision_id="",
            )

    def test_submit_no_branch_no_tier(self):
        """submit_job with no branch or tier should still succeed."""
        with patch.object(dc, "_domino_request") as mock_req:
            mock_req.return_value = {"id": "run-simple"}
            run_id = submit_job(
                command=["echo", "hello"],
                branch=None,
                tier_id="",
                project_id="proj-123",
                environment_id="",
                environment_revision_id="",
            )

        assert run_id == "run-simple"
        payload = mock_req.call_args.kwargs["json"]
        assert "mainRepoGitRef" not in payload
        assert "overrideHardwareTierId" not in payload

    def test_submit_includes_environment_and_revision(self):
        with patch.object(dc, "_domino_request") as mock_req:
            mock_req.return_value = {"id": "run-env"}
            submit_job(
                command=["echo", "hi"],
                branch=None,
                tier_id="",
                project_id="proj-123",
                environment_id="envid00112233445566778899aa",
                environment_revision_id="revid00112233445566778899aa",
            )
        payload = mock_req.call_args.kwargs["json"]
        assert payload["environmentId"] == "envid00112233445566778899aa"
        assert payload["environmentRevisionSpec"] == {"revisionId": "revid00112233445566778899aa"}


# ===================================================================
# _build_job_command_str() tests
# ===================================================================

try:
    from studio.job_engine import _build_job_command_str as _bld_cmd
    from studio.state import JobRequest as _JR
    _HAS_WEBAPP = True
except Exception:
    _HAS_WEBAPP = False

skip_no_webapp = pytest.mark.skipif(not _HAS_WEBAPP, reason="studio package not importable (fasthtml missing)")


def _make_job_request(**overrides) -> Any:
    """Build a JobRequest with sensible defaults for testing.

    Avoids having to specify every required field in each test.
    """
    if not _HAS_WEBAPP:
        pytest.skip("studio package not importable")

    defaults = dict(
        spec_path="",
        provider="anthropic",
        model="",
        code_root="/mnt/code",
        max_files=50,
        workers=4,
        planning_workers=3,
        timeout=120.0,
        notebook=True,
        notebook_path="",
        filtered_experiment_names="",
        filtered_model_names="",
        latest_only=False,
        verbose=True,
        hardware_tier="small",
        environment_id="",
        environment_revision_id="",
        project_id="",
        provider_base_url="",
        max_retries=5,
        initial_backoff=10.0,
        max_backoff=120.0,
        backoff_jitter=0.2,
        notebook_from_cache=False,
    )
    defaults.update(overrides)
    return _JR(**defaults)


_ds = "/domino/datasets/local/autodoc"


@skip_no_webapp
class TestBuildJobCommandStr:
    """Tests for _build_job_command_str (in studio/job_engine.py)."""

    def test_includes_notebook_flag_when_enabled(self):
        req = _make_job_request(notebook=True)
        cmd = _bld_cmd(req, "/mnt/spec.yaml")
        assert "--notebook" in cmd

    def test_omits_notebook_when_disabled(self):
        req = _make_job_request(notebook=False)
        cmd = _bld_cmd(req, "/mnt/spec.yaml")
        assert "--notebook" not in cmd

    def test_includes_spec_path(self):
        """Spec path should appear in the command."""
        req = _make_job_request()
        cmd = _bld_cmd(req, "/mnt/data/specs/my_spec.yaml")
        assert "--spec" in cmd
        assert "/mnt/data/specs/my_spec.yaml" in cmd

    def test_no_artifacts_copy(self):
        """Command should not include any cp or artifacts step."""
        req = _make_job_request()
        cmd = _bld_cmd(req, "/spec.yaml")
        assert "cp" not in cmd

    def test_includes_provider_base_url_when_set(self):
        req = _make_job_request(
            provider="openai",
            provider_base_url="https://api.example/v1",
        )
        cmd = _bld_cmd(req, "/spec.yaml")
        assert "--provider-base-url" in cmd
        assert "https://api.example/v1" in cmd

    def test_includes_provider_base_url_for_anthropic(self):
        req = _make_job_request(
            provider="anthropic",
            provider_base_url="https://api.anthropic.example",
        )
        cmd = _bld_cmd(req, "/spec.yaml")
        assert "--provider-base-url" in cmd
        assert "https://api.anthropic.example" in cmd

    def test_includes_language_default_in_command(self):
        from default_consts import DEFAULT_LANGUAGE

        req = _make_job_request()
        cmd = _bld_cmd(req, "/spec.yaml")
        parts = shlex.split(cmd)
        assert parts[parts.index("--language") + 1] == DEFAULT_LANGUAGE


# ===================================================================
# get_code_source_info() tests
# ===================================================================

class TestGetCodeSourceInfo:
    def _make_proj(self):
        from domino_client import ProjectInfo
        return ProjectInfo(id="proj-1", name="myproj", owner_username="alice")

    def test_git_project_returns_is_git_true(self):
        browse_resp = {"projectSettings": {"isGitBasedProject": True, "repositories": [{"id": "repo-1", "location": "/mnt/code"}]}}
        with patch.object(dc, "resolve_project", return_value=self._make_proj()), \
             patch.object(dc, "browse_code", return_value=browse_resp):
            info = get_code_source_info("proj-1")
        assert info["is_git"] is True
        assert info["repo_id"] == "repo-1"
        assert info["location"] == "/mnt/code"

    def test_dfs_project_returns_is_git_false(self):
        browse_resp = {"projectSettings": {"isGitBasedProject": False, "repositories": [{"id": "repo-2", "location": "/mnt"}]}}
        with patch.object(dc, "resolve_project", return_value=self._make_proj()), \
             patch.object(dc, "browse_code", return_value=browse_resp):
            info = get_code_source_info("proj-1")
        assert info["is_git"] is False
        assert info["repo_id"] == "repo-2"

    def test_no_repos_uses_default_location(self):
        browse_resp = {"projectSettings": {"isGitBasedProject": True, "repositories": []}}
        with patch.object(dc, "resolve_project", return_value=self._make_proj()), \
             patch.object(dc, "browse_code", return_value=browse_resp):
            info = get_code_source_info("proj-1")
        assert info["location"] == "/mnt/code"
        assert info["repo_id"] is None

    def test_skips_imported_repos_to_find_local(self):
        repos = [
            {"id": "imported-1", "location": "/mnt/imported/code/SomeRepo"},
            {"id": "local-1", "location": "/mnt/code"},
        ]
        browse_resp = {"projectSettings": {"isGitBasedProject": True, "repositories": repos}}
        with patch.object(dc, "resolve_project", return_value=self._make_proj()), \
             patch.object(dc, "browse_code", return_value=browse_resp):
            info = get_code_source_info("proj-1")
        assert info["repo_id"] == "local-1"
        assert info["location"] == "/mnt/code"

    def test_falls_back_to_non_imported_repo_when_no_exact_match(self):
        repos = [
            {"id": "imported-1", "location": "/mnt/imported/code/SomeRepo"},
            {"id": "other-1", "location": "/mnt/somewhere"},
        ]
        browse_resp = {"projectSettings": {"isGitBasedProject": True, "repositories": repos}}
        with patch.object(dc, "resolve_project", return_value=self._make_proj()), \
             patch.object(dc, "browse_code", return_value=browse_resp):
            info = get_code_source_info("proj-1")
        assert info["repo_id"] == "other-1"

    def test_uses_git_repos_api_fallback_when_local_repo_has_no_id(self):
        repos = [{"location": "/mnt/code"}]
        browse_resp = {"projectSettings": {"isGitBasedProject": True, "repositories": repos}}
        git_repos_resp = [{"id": "primary-repo-1"}]
        with patch.object(dc, "resolve_project", return_value=self._make_proj()), \
             patch.object(dc, "browse_code", return_value=browse_resp), \
             patch.object(dc, "_domino_request", return_value=git_repos_resp) as mock_req:
            info = get_code_source_info("proj-1")
        assert info["repo_id"] == "primary-repo-1"
        assert "/v4/projects/proj-1/gitRepositories" in mock_req.call_args[0][1]

    def test_unresolvable_project_raises(self):
        with patch.object(dc, "resolve_project", return_value=None):
            with pytest.raises(ValueError, match="Could not resolve"):
                get_code_source_info("proj-bad")


# ===================================================================
# browse_gbp_code() tests
# ===================================================================

class TestBrowseGbpCode:
    def test_returns_files_and_dirs_nested_response(self):
        items = [{"kind": "file", "name": "spec.yaml"}, {"kind": "dir", "name": "sub"}]
        with patch.object(dc, "_domino_request", return_value={"data": {"items": items}}):
            result = browse_gbp_code("proj-1", "repo-1", "")
        assert {"fileName": "spec.yaml", "isDirectory": False} in result
        assert {"fileName": "sub", "isDirectory": True} in result

    def test_returns_files_and_dirs_flat_response(self):
        items = [{"kind": "file", "name": "spec.yaml"}, {"kind": "dir", "name": "sub"}]
        with patch.object(dc, "_domino_request", return_value={"items": items}):
            result = browse_gbp_code("proj-1", "repo-1", "")
        assert {"fileName": "spec.yaml", "isDirectory": False} in result
        assert {"fileName": "sub", "isDirectory": True} in result

    def test_empty_directory_omits_param(self):
        with patch.object(dc, "_domino_request", return_value={"data": {"items": []}}) as mock_req:
            browse_gbp_code("proj-1", "repo-1", "")
        params = mock_req.call_args.kwargs.get("params") or mock_req.call_args[1].get("params", {})
        assert "directory" not in params

    def test_nonempty_directory_passes_param(self):
        with patch.object(dc, "_domino_request", return_value={"data": {"items": []}}) as mock_req:
            browse_gbp_code("proj-1", "repo-1", "src")
        params = mock_req.call_args.kwargs.get("params") or mock_req.call_args[1].get("params", {})
        assert params.get("directory") == "src"

    def test_url_contains_project_and_repo(self):
        with patch.object(dc, "_domino_request", return_value={"data": {"items": []}}) as mock_req:
            browse_gbp_code("proj-abc", "repo-xyz", "")
        url = mock_req.call_args[0][1]
        assert "proj-abc" in url
        assert "repo-xyz" in url


# ===================================================================
# browse_dfs_code() tests
# ===================================================================

class TestBrowseDfsCode:
    def test_merges_dirs_and_files(self):
        dirs = [{"name": "subdir"}]
        files = [{"name": "spec.yaml"}]

        def _req(method, url, **kwargs):
            if "browseDirectories" in url:
                return dirs
            return files

        with patch.object(dc, "_domino_request", side_effect=_req):
            result = browse_dfs_code("alice", "myproj", "/")
        names = [r["fileName"] for r in result]
        assert "subdir" in names
        assert "spec.yaml" in names
        dir_items = [r for r in result if r["isDirectory"]]
        file_items = [r for r in result if not r["isDirectory"]]
        assert dir_items[0]["fileName"] == "subdir"
        assert file_items[0]["fileName"] == "spec.yaml"

    def test_dir_failure_still_returns_files(self):
        files = [{"name": "a.yaml"}]

        def _req(method, url, **kwargs):
            if "browseDirectories" in url:
                raise RuntimeError("dir endpoint down")
            return files

        with patch.object(dc, "_domino_request", side_effect=_req):
            result = browse_dfs_code("alice", "myproj", "/")
        assert any(r["fileName"] == "a.yaml" for r in result)

    def test_default_path_is_root_slash(self):
        calls: list[Any] = []

        def _req(method, url, **kwargs):
            calls.append(kwargs.get("params", {}))
            return []

        with patch.object(dc, "_domino_request", side_effect=_req):
            browse_dfs_code("alice", "myproj")
        for params in calls:
            assert params.get("filePath") == "/"


# ===================================================================
# read_gbp_file_raw() tests
# ===================================================================

class TestReadGbpFileRaw:
    def test_returns_response_content(self, monkeypatch):
        monkeypatch.setenv("DOMINO_API_HOST", "https://domino.example.com")
        monkeypatch.setenv("DOMINO_USER_API_KEY", "key")
        dc._project_cache.clear()

        mock_resp = MagicMock()
        mock_resp.content = b"yaml: content"
        mock_resp.raise_for_status = MagicMock()

        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.get = MagicMock(return_value=mock_resp)

        with patch("httpx.Client", return_value=mock_client):
            result = read_gbp_file_raw("proj-1", "repo-1", "path/spec.yaml")

        assert result == b"yaml: content"
        call_kwargs = mock_client.get.call_args
        assert call_kwargs[1]["params"]["fileName"] == "path/spec.yaml"

    def test_raises_when_no_api_host(self, monkeypatch):
        monkeypatch.delenv("DOMINO_API_HOST", raising=False)
        dc._project_cache.clear()
        with patch.object(dc, "_resolve_api_host", return_value=None):
            with pytest.raises(RuntimeError, match="not configured"):
                read_gbp_file_raw("proj-1", "repo-1", "f.yaml")
