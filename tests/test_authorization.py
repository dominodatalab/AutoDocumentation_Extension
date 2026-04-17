"""Unit tests for authorized_actions + authorization helpers."""

from __future__ import annotations

import importlib
import os
import sys
from typing import Any, Optional
from unittest.mock import MagicMock

import pytest

_repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_pkg_dir = os.path.join(_repo_root, "auto_model_docs")
for p in (_repo_root, _pkg_dir):
    if p not in sys.path:
        sys.path.insert(0, p)


class _FakeResp:
    def __init__(self, payload: Any, status_code: int = 200):
        self._payload = payload
        self.status_code = status_code
        self.post_calls: list[dict[str, Any]] = []

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            import httpx
            raise httpx.HTTPStatusError(
                f"status {self.status_code}",
                request=MagicMock(),
                response=MagicMock(status_code=self.status_code),
            )

    def json(self) -> Any:
        return self._payload


class _FakeClient:
    def __init__(self, resp: _FakeResp):
        self._resp = resp
        self.post_calls: list[dict[str, Any]] = []

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def post(self, url: str, *, json: Any, headers: dict) -> _FakeResp:
        self.post_calls.append({"url": url, "json": json, "headers": headers})
        return self._resp


@pytest.fixture(autouse=True)
def _reload_modules():
    """Reload authz modules so each test gets a clean import."""
    for m in ("authorization", "authorized_actions"):
        sys.modules.pop(m, None)
    yield
    for m in ("authorization", "authorized_actions"):
        sys.modules.pop(m, None)


def _install_fake_httpx(monkeypatch, resp: _FakeResp) -> _FakeClient:
    import httpx
    fake = _FakeClient(resp)
    monkeypatch.setattr(httpx, "Client", lambda *a, **kw: fake)
    return fake


# ---------------------------------------------------------------------------
# authorized_actions.py
# ---------------------------------------------------------------------------

class TestAuthorizedActions:
    def test_allowed_returns_true_for_allow_result(self, monkeypatch):
        resp = _FakeResp({
            "actions": [{
                "id": "job.project.start_job-p1",
                "code": "job.project.start_job",
                "result": True,
            }],
        })
        fake = _install_fake_httpx(monkeypatch, resp)

        import authorized_actions as aa
        action = aa.AuthorizedActionRequestItem(
            id="job.project.start_job-p1",
            code="job.project.start_job",
            context={"projectId": "p1"},
        )
        assert aa.authorized_action_allowed(action) is True
        assert len(fake.post_calls) == 1
        call = fake.post_calls[0]
        assert call["url"].endswith("/account/authz/permissions/authorizedactions")
        assert call["json"] == {
            "actions": [{
                "id": "job.project.start_job-p1",
                "code": "job.project.start_job",
                "context": {"projectId": "p1"},
            }],
        }
        assert "Authorization" in call["headers"] or "X-Domino-Api-Key" in call["headers"]

    def test_allowed_returns_false_for_deny_result(self, monkeypatch):
        resp = _FakeResp({
            "actions": [{"id": "x", "code": "y", "result": False}],
        })
        _install_fake_httpx(monkeypatch, resp)

        import authorized_actions as aa
        action = aa.AuthorizedActionRequestItem(id="x", code="y", context={"projectId": "p"})
        assert aa.authorized_action_allowed(action) is False

    def test_allowed_parses_bare_list_envelope(self, monkeypatch):
        resp = _FakeResp([{"id": "x", "code": "y", "result": True}])
        _install_fake_httpx(monkeypatch, resp)

        import authorized_actions as aa
        action = aa.AuthorizedActionRequestItem(id="x", code="y", context={"projectId": "p"})
        assert aa.authorized_action_allowed(action) is True

    def test_allowed_treats_null_result_as_deny(self, monkeypatch):
        resp = _FakeResp({"actions": [{"id": "x", "code": "y", "result": None}]})
        _install_fake_httpx(monkeypatch, resp)

        import authorized_actions as aa
        action = aa.AuthorizedActionRequestItem(id="x", code="y", context={"projectId": "p"})
        assert aa.authorized_action_allowed(action) is False

    def test_allowed_raises_on_500(self, monkeypatch):
        resp = _FakeResp({}, status_code=500)
        _install_fake_httpx(monkeypatch, resp)

        import authorized_actions as aa
        action = aa.AuthorizedActionRequestItem(id="x", code="y", context={"projectId": "p"})
        with pytest.raises(Exception):
            aa.authorized_action_allowed(action)


# ---------------------------------------------------------------------------
# authorization.py: require_* helpers
# ---------------------------------------------------------------------------

def _install_allowed_response(monkeypatch, allowed: bool) -> _FakeClient:
    resp = _FakeResp({
        "actions": [{"id": "x", "code": "y", "result": allowed}],
    })
    return _install_fake_httpx(monkeypatch, resp)


class TestRequireHelpers:
    @pytest.mark.parametrize("fn_name,kwargs,expected_code,expected_ctx_key", [
        ("require_domino_job_start", {"project_id": "p1"}, "job.project.start_job", "projectId"),
        ("require_domino_job_stop",  {"job_id": "run-1"},  "job.project.stop_job",  "jobId"),
        ("require_domino_job_list",  {"project_id": "p1"}, "job.project.list_jobs", "projectId"),
        ("require_project_write",    {"project_id": "p1"}, "project.change_project_settings", "projectId"),
    ])
    def test_require_returns_none_on_allow(self, monkeypatch, fn_name, kwargs, expected_code, expected_ctx_key):
        fake = _install_allowed_response(monkeypatch, True)
        import authorization as auth
        fn = getattr(auth, fn_name)
        value = next(iter(kwargs.values()))

        assert fn(value) is None
        assert len(fake.post_calls) == 1
        sent = fake.post_calls[0]["json"]["actions"][0]
        assert sent["code"] == expected_code
        assert sent["context"] == {expected_ctx_key: value}

    @pytest.mark.parametrize("fn_name,arg", [
        ("require_domino_job_start", "p1"),
        ("require_domino_job_stop",  "run-1"),
        ("require_domino_job_list",  "p1"),
        ("require_project_write",    "p1"),
    ])
    def test_require_raises_403_on_deny(self, monkeypatch, fn_name, arg):
        _install_allowed_response(monkeypatch, False)
        from starlette.exceptions import HTTPException
        import authorization as auth
        fn = getattr(auth, fn_name)
        with pytest.raises(HTTPException) as excinfo:
            fn(arg)
        assert excinfo.value.status_code == 403

    @pytest.mark.parametrize("fn_name", [
        "require_domino_job_start",
        "require_domino_job_stop",
        "require_domino_job_list",
        "require_project_write",
    ])
    def test_require_raises_403_on_none_id(self, monkeypatch, fn_name):
        fake = _install_allowed_response(monkeypatch, True)
        from starlette.exceptions import HTTPException
        import authorization as auth
        fn = getattr(auth, fn_name)
        with pytest.raises(HTTPException) as excinfo:
            fn(None)
        assert excinfo.value.status_code == 403
        assert fake.post_calls == [], "None id should short-circuit before HTTP"

    @pytest.mark.parametrize("fn_name,arg", [
        ("require_domino_job_start", "p1"),
        ("require_domino_job_stop",  "run-1"),
        ("require_domino_job_list",  "p1"),
        ("require_project_write",    "p1"),
    ])
    def test_require_fails_closed_on_http_error(self, monkeypatch, fn_name, arg):
        resp = _FakeResp({}, status_code=500)
        _install_fake_httpx(monkeypatch, resp)
        from starlette.exceptions import HTTPException
        import authorization as auth
        fn = getattr(auth, fn_name)
        with pytest.raises(HTTPException) as excinfo:
            fn(arg)
        assert excinfo.value.status_code == 403

    def test_require_fails_closed_on_network_exception(self, monkeypatch):
        import httpx

        class _BoomClient:
            def __enter__(self): return self
            def __exit__(self, *a): return False
            def post(self, *a, **kw):
                raise httpx.ConnectError("boom")

        monkeypatch.setattr(httpx, "Client", lambda *a, **kw: _BoomClient())

        from starlette.exceptions import HTTPException
        import authorization as auth
        with pytest.raises(HTTPException) as excinfo:
            auth.require_domino_job_start("p1")
        assert excinfo.value.status_code == 403
