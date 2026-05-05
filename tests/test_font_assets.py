from __future__ import annotations

import os
import sys

_repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_pkg_dir = os.path.join(_repo_root, "auto_model_docs")
for p in (_repo_root, _pkg_dir):
    if p not in sys.path:
        sys.path.insert(0, p)


def test_studio_asset_url_apps_prefix():
    from starlette.requests import Request

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
    assert studio_asset_url(req, "static/example.js") == "/apps/myapp/static/example.js"


def test_studio_asset_url_root():
    from starlette.requests import Request

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
    assert studio_asset_url(req, "static/example.js") == "/static/example.js"


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
