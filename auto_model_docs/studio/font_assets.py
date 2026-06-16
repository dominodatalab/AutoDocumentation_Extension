from __future__ import annotations

import re

from starlette.requests import Request


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
