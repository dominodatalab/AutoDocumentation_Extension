from __future__ import annotations

import importlib.resources
import re
from functools import lru_cache

from starlette.requests import Request
from starlette.responses import Response

_STEM = "fa-pro-light-300"
_ALLOWED_STEMS = frozenset({_STEM})

STUDIO_FONT_BASE_MARKER = "__STUDIO_FONT_BASE__"

STUDIO_FONT_BASE_PATCH_JS = (
    r"(function(){"
    r"var m=(location.pathname||'').match(/^(\/apps(?:-internal)?\/[^/]+)/i);"
    r"var b=m?m[1]+'/studio-static/fontawesome':'/studio-static/fontawesome';"
    r"var nodes=document.getElementsByTagName('style');"
    r"for(var i=0;i<nodes.length;i++){"
    r"var t=nodes[i].textContent||'';"
    r"if(t.indexOf('"
    + STUDIO_FONT_BASE_MARKER
    + r"')!==-1){"
    r"nodes[i].textContent=t.split('"
    + STUDIO_FONT_BASE_MARKER
    + r"').join(b);break;}"
    r"}"
    r"})();"
)


def studio_public_prefix(req: Request) -> str:
    rp = req.scope.get("root_path") or ""
    if isinstance(rp, str) and rp.strip():
        return rp.rstrip("/")
    path = req.url.path or ""
    m = re.match(r"^(/apps(?:-internal)?/[^/]+)", path)
    if m:
        return m.group(1)
    return ""


def studio_asset_url(req: Request, rel: str) -> str:
    rel = rel.lstrip("/")
    pre = studio_public_prefix(req).rstrip("/")
    if pre:
        return f"{pre}/{rel}"
    return f"/{rel}"


@lru_cache(maxsize=64)
def _fontawesome_faces_css_for_base(font_dir_base: str) -> str:
    src = f'{font_dir_base}/{_STEM}'
    return (
        f"""
@font-face {{
    font-family: "Font Awesome 6 Pro";
    font-style: normal;
    font-weight: 300;
    font-display: block;
    src: url("{src}") format("opentype");
}}
"""
    ).strip()


def fontawesome_faces_css() -> str:
    return _fontawesome_faces_css_for_base(STUDIO_FONT_BASE_MARKER)


def register_font_assets(rt):
    @rt("/studio-static/fontawesome/{stem}")
    async def _serve_fontawesome_otf(stem: str):
        if stem not in _ALLOWED_STEMS:
            return Response(status_code=404)
        fname = f"{stem}.otf"
        root = importlib.resources.files("studio").joinpath("static/fontawesome")
        try:
            data = root.joinpath(fname).read_bytes()
        except Exception:
            return Response(status_code=404)
        return Response(content=data, media_type="font/otf")
