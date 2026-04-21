"""Tests for domino_auth: host resolution, auth providers, project ID."""

from __future__ import annotations

import os
import sys

import pytest
from unittest.mock import patch

_repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_pkg_dir = os.path.join(_repo_root, "auto_model_docs")
for p in (_repo_root, _pkg_dir):
    if p not in sys.path:
        sys.path.insert(0, p)

import domino_auth
from domino_auth import (
    AuthCredentials,
    MissingAuthError,
    cli_auth,
    configure_auth,
    current_auth,
    get_cli_token,
    get_user_token,
    reset_auth,
    resolve_api_host,
    resolve_project_id,
    user_auth,
)


@pytest.fixture(autouse=True)
def _reset_provider():
    reset_auth()
    yield
    reset_auth()


class TestResolveApiHost:
    def test_returns_host_from_env(self, monkeypatch):
        monkeypatch.delenv("DOMINO_API_PROXY", raising=False)
        monkeypatch.setenv("DOMINO_API_HOST", "https://domino.example.com")
        assert resolve_api_host() == "https://domino.example.com"

    def test_strips_trailing_slash(self, monkeypatch):
        monkeypatch.delenv("DOMINO_API_PROXY", raising=False)
        monkeypatch.setenv("DOMINO_API_HOST", "https://domino.example.com/")
        assert resolve_api_host() == "https://domino.example.com"

    def test_strips_multiple_trailing_slashes(self, monkeypatch):
        monkeypatch.delenv("DOMINO_API_PROXY", raising=False)
        monkeypatch.setenv("DOMINO_API_HOST", "https://domino.example.com///")
        assert resolve_api_host() == "https://domino.example.com"

    def test_returns_empty_when_unset(self, monkeypatch):
        monkeypatch.delenv("DOMINO_API_HOST", raising=False)
        monkeypatch.delenv("DOMINO_API_PROXY", raising=False)
        assert resolve_api_host() == ""

    def test_returns_empty_when_blank(self, monkeypatch):
        monkeypatch.delenv("DOMINO_API_PROXY", raising=False)
        monkeypatch.setenv("DOMINO_API_HOST", "")
        assert resolve_api_host() == ""

    def test_prefers_proxy_over_host(self, monkeypatch):
        monkeypatch.setenv("DOMINO_API_PROXY", "http://localhost:8899")
        monkeypatch.setenv("DOMINO_API_HOST", "https://nucleus:80")
        assert resolve_api_host() == "http://localhost:8899"

    def test_falls_back_to_host_when_proxy_unset(self, monkeypatch):
        monkeypatch.delenv("DOMINO_API_PROXY", raising=False)
        monkeypatch.setenv("DOMINO_API_HOST", "https://nucleus:80")
        assert resolve_api_host() == "https://nucleus:80"


class TestGetUserToken:
    def test_returns_forwarded_jwt(self):
        with patch("domino_auth.get_request_auth_header", return_value="Bearer user-jwt"):
            assert get_user_token() == "Bearer user-jwt"

    def test_raises_when_missing(self):
        with patch("domino_auth.get_request_auth_header", return_value=None):
            with pytest.raises(MissingAuthError):
                get_user_token()

    def test_raises_on_empty_string(self):
        with patch("domino_auth.get_request_auth_header", return_value=""):
            with pytest.raises(MissingAuthError):
                get_user_token()

    def test_ignores_env_api_keys(self, monkeypatch):
        monkeypatch.setenv("DOMINO_USER_API_KEY", "should-not-be-used")
        monkeypatch.setenv("DOMINO_API_KEY", "also-not-used")
        with patch("domino_auth.get_request_auth_header", return_value=None):
            with pytest.raises(MissingAuthError):
                get_user_token()


class TestGetCliToken:
    def test_prefers_user_api_key(self, monkeypatch):
        monkeypatch.setenv("DOMINO_USER_API_KEY", "user-key")
        monkeypatch.setenv("DOMINO_API_KEY", "generic-key")
        assert get_cli_token() == "user-key"

    def test_falls_back_to_domino_api_key(self, monkeypatch):
        monkeypatch.delenv("DOMINO_USER_API_KEY", raising=False)
        monkeypatch.setenv("DOMINO_API_KEY", "generic-key")
        assert get_cli_token() == "generic-key"

    def test_raises_when_missing(self, monkeypatch):
        monkeypatch.delenv("DOMINO_USER_API_KEY", raising=False)
        monkeypatch.delenv("DOMINO_API_KEY", raising=False)
        with pytest.raises(MissingAuthError):
            get_cli_token()

    def test_raises_when_empty(self, monkeypatch):
        monkeypatch.setenv("DOMINO_USER_API_KEY", "")
        monkeypatch.setenv("DOMINO_API_KEY", "")
        with pytest.raises(MissingAuthError):
            get_cli_token()

    def test_ignores_forwarded_jwt(self, monkeypatch):
        monkeypatch.setenv("DOMINO_USER_API_KEY", "api-key")
        with patch("domino_auth.get_request_auth_header", return_value="Bearer should-not-be-used"):
            assert get_cli_token() == "api-key"


class TestAuthCredentials:
    def test_jwt_headers_with_bearer_prefix(self):
        c = AuthCredentials(kind="jwt", token="Bearer abc123")
        assert c.to_headers() == {"Authorization": "Bearer abc123"}

    def test_jwt_headers_without_bearer_prefix(self):
        c = AuthCredentials(kind="jwt", token="abc123")
        assert c.to_headers() == {"Authorization": "Bearer abc123"}

    def test_api_key_headers(self):
        c = AuthCredentials(kind="api_key", token="secret")
        assert c.to_headers() == {"X-Domino-Api-Key": "secret"}


class TestUserAuth:
    def test_builds_jwt_credentials(self):
        with patch("domino_auth.get_request_auth_header", return_value="Bearer jwt"):
            creds = user_auth()
        assert creds == AuthCredentials(kind="jwt", token="Bearer jwt")

    def test_raises_without_token(self):
        with patch("domino_auth.get_request_auth_header", return_value=None):
            with pytest.raises(MissingAuthError):
                user_auth()


class TestCliAuth:
    def test_builds_api_key_credentials(self, monkeypatch):
        monkeypatch.setenv("DOMINO_USER_API_KEY", "k1")
        assert cli_auth() == AuthCredentials(kind="api_key", token="k1")

    def test_raises_without_key(self, monkeypatch):
        monkeypatch.delenv("DOMINO_USER_API_KEY", raising=False)
        monkeypatch.delenv("DOMINO_API_KEY", raising=False)
        with pytest.raises(MissingAuthError):
            cli_auth()


class TestConfiguredProvider:
    def test_current_auth_raises_when_not_configured(self):
        with pytest.raises(MissingAuthError, match="not configured"):
            current_auth()

    def test_configure_with_user_auth(self):
        configure_auth(user_auth)
        with patch("domino_auth.get_request_auth_header", return_value="Bearer abc"):
            assert current_auth() == AuthCredentials(kind="jwt", token="Bearer abc")

    def test_configure_with_cli_auth(self, monkeypatch):
        monkeypatch.setenv("DOMINO_USER_API_KEY", "key")
        configure_auth(cli_auth)
        assert current_auth() == AuthCredentials(kind="api_key", token="key")

    def test_reset_auth_clears_provider(self, monkeypatch):
        monkeypatch.setenv("DOMINO_USER_API_KEY", "key")
        configure_auth(cli_auth)
        reset_auth()
        with pytest.raises(MissingAuthError):
            current_auth()

    def test_current_auth_propagates_provider_errors(self):
        configure_auth(user_auth)
        with patch("domino_auth.get_request_auth_header", return_value=None):
            with pytest.raises(MissingAuthError):
                current_auth()


class TestResolveProjectId:
    def test_returns_given_id(self):
        assert resolve_project_id("abc123") == "abc123"

    def test_raises_when_none(self):
        with pytest.raises(RuntimeError, match="No project ID available"):
            resolve_project_id(None)

    def test_raises_when_empty_string(self):
        with pytest.raises(RuntimeError, match="No project ID available"):
            resolve_project_id("")
