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


def test_font_face_css_uses_placeholder_until_browser_patch(fh_app):
    from studio.font_assets import STUDIO_FONT_BASE_MARKER, fontawesome_faces_css

    css = fontawesome_faces_css()
    assert STUDIO_FONT_BASE_MARKER in css
    assert STUDIO_FONT_BASE_MARKER + "/fa-pro-light-300" in css
    assert ".otf" not in css
    assert "Font Awesome 6 Pro" in css
    assert css.count("@font-face") == 1
    assert "Font Awesome 6 Sharp" not in css


def test_font_base_patch_script_targets_placeholder():
    from studio.font_assets import STUDIO_FONT_BASE_MARKER, STUDIO_FONT_BASE_PATCH_JS

    assert STUDIO_FONT_BASE_MARKER in STUDIO_FONT_BASE_PATCH_JS
    assert "location.pathname" in STUDIO_FONT_BASE_PATCH_JS


def test_serve_font_otf(fh_app):
    c = TestClient(fh_app)
    r = c.get("/studio-static/fontawesome/fa-pro-light-300")
    assert r.status_code == 200
    assert r.content[:4] == b"OTTO"
    assert c.get("/studio-static/fontawesome/unknown").status_code == 404
    assert c.get("/studio-static/fontawesome/fa-pro-solid-900").status_code == 404


def test_studio_css_typography_matches_domino_web_ui():
    from pathlib import Path

    root = Path(__file__).resolve().parent.parent
    studio = root / "auto_model_docs" / "studio"
    styles = (studio / "styles.py").read_text()
    assert "fonts.googleapis.com/css2?family=Inter" in styles
    assert "Material+Symbols+Outlined" in styles
    assert "--font-body:" in styles and "Inter" in styles
    assert "ui-monospace" in styles
    assert ".material-symbols-outlined" in styles

    font_assets = (studio / "font_assets.py").read_text()
    assert "Font Awesome 6 Pro" in font_assets
