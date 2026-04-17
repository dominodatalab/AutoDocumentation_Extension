"""Tests for Domino HTTP client redirect behavior."""

from __future__ import annotations

import os
import sys
from unittest.mock import MagicMock, patch

_repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_pkg_dir = os.path.join(_repo_root, "auto_model_docs")
for p in (_repo_root, _pkg_dir):
    if p not in sys.path:
        sys.path.insert(0, p)

import domino_client as dc
from domino_auth import cli_auth, configure_auth, reset_auth


def setup_function():
    reset_auth()
    configure_auth(cli_auth)


def teardown_function():
    reset_auth()


@patch("httpx.Client")
def test_domino_request_uses_follow_redirects(mock_client_cls):
    mock_client = MagicMock()
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"id": "job-1"}
    mock_client.__enter__.return_value.request.return_value = mock_resp
    mock_client_cls.return_value = mock_client

    with patch.object(dc, "_resolve_api_host", return_value="https://cluster.example.com"), patch.dict(
        os.environ, {"DOMINO_USER_API_KEY": "test-key"}, clear=False
    ):
        result = dc._domino_request("GET", "/v4/jobs/job-1")

    assert result == {"id": "job-1"}
    mock_client_cls.assert_called_once_with(timeout=dc._DEFAULT_TIMEOUT, follow_redirects=True)
