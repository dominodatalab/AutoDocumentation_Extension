"""Per-request auth context.

- ``_auth_header_var``: forwarded ``Authorization`` header captured by the
  FastAPI middleware in ``web_app_studio.py``. Used by ``domino_auth``
  so outbound Domino API calls run as the viewing user.
- ``get_viewing_user()``: resolves the current viewer via ``GET /v4/users/self``
  on the Domino API using the forwarded JWT. Raises if no JWT is available.
"""

from __future__ import annotations

from contextvars import ContextVar
from dataclasses import dataclass
from typing import Optional

_auth_header_var: ContextVar[Optional[str]] = ContextVar(
    "forwarded_authorization_header", default=None
)
_request_origin_var: ContextVar[Optional[str]] = ContextVar(
    "request_origin", default=None
)


def set_request_auth_header(value: Optional[str]) -> None:
    _auth_header_var.set(value)


def get_request_auth_header() -> Optional[str]:
    return _auth_header_var.get()


def set_request_origin(value: Optional[str]) -> None:
    _request_origin_var.set(value)


def get_request_origin() -> Optional[str]:
    return _request_origin_var.get()


def build_request_origin(host_header: str, scheme: str = "https") -> Optional[str]:
    from urllib.parse import urlparse, urlunparse

    raw = (host_header or "").strip()
    if not raw:
        return None

    if "://" not in raw:
        raw = f"{scheme}://{raw.split(',')[0].strip()}"

    parsed = urlparse(raw)
    hostname = (parsed.hostname or "").strip()
    if not hostname:
        return None

    if hostname.startswith("apps."):
        hostname = hostname[len("apps.") :]
    if not hostname:
        return None

    netloc = f"{hostname}:{parsed.port}" if parsed.port else hostname
    return urlunparse((parsed.scheme or scheme, netloc, "", "", "", "")).rstrip("/")


def get_user_auth_headers() -> dict[str, str]:
    """Build auth headers from the forwarded user token.

    Raises ``RuntimeError`` if no token was forwarded, preventing
    silent escalation to the app-owner identity.
    """
    forwarded = get_request_auth_header()
    if not forwarded:
        raise RuntimeError(
            "No forwarded user token available. "
            "Domino API calls require a user token from the incoming request."
        )
    return {"Authorization": forwarded}


@dataclass(frozen=True)
class User:
    id: str
    user_name: str


def get_viewing_user() -> User:
    """Resolve the current request's Domino user via ``/v4/users/self``.

    Raises if no forwarded JWT is available or the Domino API call fails.
    """
    import httpx
    from domino_auth import current_auth, resolve_api_host

    host = resolve_api_host()
    if not host:
        raise RuntimeError("DOMINO_API_HOST is not configured.")

    headers = current_auth().to_headers()
    with httpx.Client(timeout=10.0) as client:
        resp = client.get(f"{host}/v4/users/self", headers=headers)
        resp.raise_for_status()
        data = resp.json()

    uid = data.get("id")
    uname = data.get("userName") or ""
    if not uid:
        raise RuntimeError("Domino /v4/users/self returned no id.")
    return User(id=uid, user_name=uname)
