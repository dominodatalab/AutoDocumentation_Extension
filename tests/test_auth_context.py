"""Tests for auth_context.py — ContextVar-based auth forwarding."""

from __future__ import annotations

import sys
import os

import pytest

# Ensure auto_model_docs is importable
_repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_pkg_dir = os.path.join(_repo_root, "auto_model_docs")
for p in (_repo_root, _pkg_dir):
    if p not in sys.path:
        sys.path.insert(0, p)

from unittest.mock import MagicMock, patch

from auth_context import (
    User,
    get_request_auth_header,
    get_user_auth_headers,
    get_viewing_user,
    set_request_auth_header,
    set_viewing_user,
)


class TestSetGetAuthHeader:
    def test_default_is_none(self):
        set_request_auth_header(None)
        assert get_request_auth_header() is None

    def test_set_and_get(self):
        set_request_auth_header("Bearer test-jwt-token")
        assert get_request_auth_header() == "Bearer test-jwt-token"
        set_request_auth_header(None)  # cleanup

    def test_overwrite(self):
        set_request_auth_header("Bearer first")
        set_request_auth_header("Bearer second")
        assert get_request_auth_header() == "Bearer second"
        set_request_auth_header(None)

    def test_clear(self):
        set_request_auth_header("Bearer token")
        set_request_auth_header(None)
        assert get_request_auth_header() is None


class TestGetUserAuthHeaders:
    def test_returns_auth_dict(self):
        set_request_auth_header("Bearer my-jwt")
        headers = get_user_auth_headers()
        assert headers == {"Authorization": "Bearer my-jwt"}
        set_request_auth_header(None)

    def test_raises_when_no_token(self):
        set_request_auth_header(None)
        with pytest.raises(RuntimeError, match="No forwarded user token"):
            get_user_auth_headers()

    def test_preserves_exact_value(self):
        """The header value should be forwarded exactly as received."""
        set_request_auth_header("Token custom-scheme-value")
        headers = get_user_auth_headers()
        assert headers["Authorization"] == "Token custom-scheme-value"
        set_request_auth_header(None)


class TestGetViewingUser:
    def setup_method(self):
        set_viewing_user(None)
        set_request_auth_header(None)

    def teardown_method(self):
        set_viewing_user(None)
        set_request_auth_header(None)

    def test_returns_cached_value_without_http_call(self):
        set_viewing_user(User(id="uid-1", user_name="alice"))
        with patch("httpx.Client") as mock_client_cls:
            u = get_viewing_user()
        assert u.id == "uid-1"
        assert u.user_name == "alice"
        mock_client_cls.assert_not_called()

    def test_fetches_from_self_endpoint(self, monkeypatch):
        monkeypatch.setenv("DOMINO_API_HOST", "https://domino.example.com")
        set_request_auth_header("Bearer jwt")

        mock_resp = MagicMock()
        mock_resp.raise_for_status = MagicMock()
        mock_resp.json.return_value = {"id": "uid-42", "userName": "bob"}
        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.get.return_value = mock_resp

        from domino_auth import configure_auth, user_auth
        configure_auth(user_auth)

        with patch("httpx.Client", return_value=mock_client):
            u = get_viewing_user()

        assert u.id == "uid-42"
        assert u.user_name == "bob"
        call_url = mock_client.get.call_args.args[0]
        assert call_url.endswith("/v4/users/self")

    def test_caches_across_calls(self, monkeypatch):
        monkeypatch.setenv("DOMINO_API_HOST", "https://domino.example.com")
        set_request_auth_header("Bearer jwt")

        mock_resp = MagicMock()
        mock_resp.raise_for_status = MagicMock()
        mock_resp.json.return_value = {"id": "uid-1", "userName": "alice"}
        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.get.return_value = mock_resp

        from domino_auth import configure_auth, user_auth
        configure_auth(user_auth)

        with patch("httpx.Client", return_value=mock_client):
            get_viewing_user()
            get_viewing_user()
            get_viewing_user()

        assert mock_client.get.call_count == 1

    def test_raises_without_jwt(self, monkeypatch):
        monkeypatch.setenv("DOMINO_API_HOST", "https://domino.example.com")
        set_request_auth_header(None)
        from domino_auth import MissingAuthError, configure_auth, user_auth
        configure_auth(user_auth)
        with pytest.raises(MissingAuthError):
            get_viewing_user()

    def test_raises_when_host_missing(self, monkeypatch):
        monkeypatch.delenv("DOMINO_API_HOST", raising=False)
        monkeypatch.delenv("DOMINO_API_PROXY", raising=False)
        with pytest.raises(RuntimeError, match="DOMINO_API_HOST"):
            get_viewing_user()

    def test_raises_when_response_has_no_id(self, monkeypatch):
        monkeypatch.setenv("DOMINO_API_HOST", "https://domino.example.com")
        set_request_auth_header("Bearer jwt")

        mock_resp = MagicMock()
        mock_resp.raise_for_status = MagicMock()
        mock_resp.json.return_value = {"userName": "alice"}
        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.get.return_value = mock_resp

        from domino_auth import configure_auth, user_auth
        configure_auth(user_auth)

        with patch("httpx.Client", return_value=mock_client):
            with pytest.raises(RuntimeError, match="no id"):
                get_viewing_user()
