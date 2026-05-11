from __future__ import annotations

import os
import sys

import pytest
from starlette.requests import Request
from starlette.testclient import TestClient

_repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_pkg_dir = os.path.join(_repo_root, "auto_model_docs")
for p in (_repo_root, _pkg_dir):
    if p not in sys.path:
        sys.path.insert(0, p)


@pytest.fixture
def fh_app():
    from fasthtml.common import fast_app

    from studio.font_assets import register_font_assets

    app, rt = fast_app(pico=False)
    register_font_assets(rt)
    return app


def test_studio_asset_url_apps_prefix():
    from studio.font_assets import studio_asset_url

    scope = {
        "type": "http",
        "asgi": {"version": "3.0"},
        "method": "GET",
        "path": "/apps/myapp/",
        "raw_path": b"/apps/myapp/",
        "query_string": b"",
        "headers": [],
        "scheme": "https",
        "server": ("test", 443),
        "client": ("127.0.0.1", 12345),
    }
    req = Request(scope)
    assert studio_asset_url(req, "studio-static/fontawesome/fa-x") == "/apps/myapp/studio-static/fontawesome/fa-x"


def test_studio_asset_url_root():
    from studio.font_assets import studio_asset_url

    scope = {
        "type": "http",
        "asgi": {"version": "3.0"},
        "method": "GET",
        "path": "/",
        "raw_path": b"/",
        "query_string": b"",
        "headers": [],
        "scheme": "https",
        "server": ("test", 443),
        "client": ("127.0.0.1", 12345),
    }
    req = Request(scope)
    assert studio_asset_url(req, "studio-static/fontawesome/fa-x") == "/studio-static/fontawesome/fa-x"


def test_font_face_css_contains_urls(fh_app):
    from studio.font_assets import fontawesome_faces_css

    scope = {
        "type": "http",
        "asgi": {"version": "3.0"},
        "method": "GET",
        "path": "/apps/z/",
        "raw_path": b"/apps/z/",
        "query_string": b"",
        "headers": [],
        "scheme": "https",
        "server": ("test", 443),
        "client": ("127.0.0.1", 12345),
    }
    css = fontawesome_faces_css(Request(scope))
    assert "/apps/z/studio-static/fontawesome/fa-pro-light-300" in css
    assert ".otf" not in css


def test_serve_font_otf(fh_app):
    c = TestClient(fh_app)
    r = c.get("/studio-static/fontawesome/fa-pro-light-300")
    assert r.status_code == 200
    assert r.content[:4] == b"OTTO"
    assert c.get("/studio-static/fontawesome/unknown").status_code == 404
