"""Per-request auth context.

- ``_auth_header_var``: forwarded ``Authorization`` header captured by the
  FastAPI middleware in ``web_app_studio.py``. Used by ``domino_auth``
  so outbound Domino API calls run as the viewing user.
- ``get_viewing_user()``: resolves the current viewer via ``GET /v4/users/self``
  on the Domino API. Cached per-request in a ContextVar so each request
  makes at most one call. Returns an opaque user id plus a display name.
  Raises if no forwarded JWT is available.
"""

from __future__ import annotations

from contextvars import ContextVar
from dataclasses import dataclass
from typing import Optional

_auth_header_var: ContextVar[Optional[str]] = ContextVar(
    "forwarded_authorization_header", default=None
)


def set_request_auth_header(value: Optional[str]) -> None:
    _auth_header_var.set(value)


def get_request_auth_header() -> Optional[str]:
    return _auth_header_var.get()


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


_user_var: ContextVar[Optional[User]] = ContextVar("viewing_user", default=None)


def _fetch_viewing_user() -> User:
    """Hit ``/v4/users/self`` using the forwarded JWT."""
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


def get_viewing_user() -> User:
    """Return the current request's Domino user, fetching once per context.

    Raises if no forwarded JWT is available or the Domino API call fails.
    """
    cached = _user_var.get()
    if cached is not None:
        return cached
    fetched = _fetch_viewing_user()
    _user_var.set(fetched)
    return fetched


def set_viewing_user(user: Optional[User]) -> None:
    """Test hook / middleware seam. Normally ``get_viewing_user`` populates this."""
    _user_var.set(user)
