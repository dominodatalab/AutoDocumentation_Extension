from __future__ import annotations

import importlib.resources
import re
from functools import lru_cache

from starlette.requests import Request
from starlette.responses import Response

_ALLOWED_OTF = frozenset(
    {
        "fa-brands-regular-400.otf",
        "fa-duotone-solid-900.otf",
        "fa-pro-light-300.otf",
        "fa-pro-regular-400.otf",
        "fa-pro-solid-900.otf",
        "fa-pro-thin-100.otf",
        "fa-sharp-light-300.otf",
        "fa-sharp-regular-400.otf",
        "fa-sharp-solid-900.otf",
        "fa-sharp-thin-100.otf",
    }
)

_ALLOWED_STEMS = frozenset({p[:-4] for p in _ALLOWED_OTF})

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

    def u(stem: str) -> str:
        return f"{font_dir_base}/{stem}"

    return (
        """
@font-face {
    font-family: "Font Awesome 6 Pro";
    font-style: normal;
    font-weight: 100;
    font-display: block;
    src: url("U1") format("opentype");
}
@font-face {
    font-family: "Font Awesome 6 Pro";
    font-style: normal;
    font-weight: 300;
    font-display: block;
    src: url("U2") format("opentype");
}
@font-face {
    font-family: "Font Awesome 6 Pro";
    font-style: normal;
    font-weight: 400;
    font-display: block;
    src: url("U3") format("opentype");
}
@font-face {
    font-family: "Font Awesome 6 Pro";
    font-style: normal;
    font-weight: 900;
    font-display: block;
    src: url("U4") format("opentype");
}
@font-face {
    font-family: "Font Awesome 6 Sharp";
    font-style: normal;
    font-weight: 100;
    font-display: block;
    src: url("U5") format("opentype");
}
@font-face {
    font-family: "Font Awesome 6 Sharp";
    font-style: normal;
    font-weight: 300;
    font-display: block;
    src: url("U6") format("opentype");
}
@font-face {
    font-family: "Font Awesome 6 Sharp";
    font-style: normal;
    font-weight: 400;
    font-display: block;
    src: url("U7") format("opentype");
}
@font-face {
    font-family: "Font Awesome 6 Sharp";
    font-style: normal;
    font-weight: 900;
    font-display: block;
    src: url("U8") format("opentype");
}
@font-face {
    font-family: "Font Awesome 6 Duotone";
    font-style: normal;
    font-weight: 900;
    font-display: block;
    src: url("U9") format("opentype");
}
@font-face {
    font-family: "Font Awesome 6 Brands";
    font-style: normal;
    font-weight: 400;
    font-display: block;
    src: url("UA") format("opentype");
}
body::before {
    content: "\\f059";
    font-family: "Font Awesome 6 Pro";
    font-weight: 300;
    font-style: normal;
    position: fixed;
    left: -9999px;
    top: 0;
    width: 1px;
    height: 1px;
    overflow: hidden;
    clip-path: inset(50%);
    pointer-events: none;
}
"""
        .replace("U1", u("fa-pro-thin-100"))
        .replace("U2", u("fa-pro-light-300"))
        .replace("U3", u("fa-pro-regular-400"))
        .replace("U4", u("fa-pro-solid-900"))
        .replace("U5", u("fa-sharp-thin-100"))
        .replace("U6", u("fa-sharp-light-300"))
        .replace("U7", u("fa-sharp-regular-400"))
        .replace("U8", u("fa-sharp-solid-900"))
        .replace("U9", u("fa-duotone-solid-900"))
        .replace("UA", u("fa-brands-regular-400"))
        .strip()
    )


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
