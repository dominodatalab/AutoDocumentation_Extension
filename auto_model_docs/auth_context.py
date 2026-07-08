"""Per-request auth context.

- ``_auth_header_var``: forwarded ``Authorization`` header captured by the
  FastAPI middleware in ``web_app_studio.py``. Used by ``domino_auth``
  so outbound Domino API calls run as the viewing user.
- ``get_viewing_user()``: resolves the current viewer via ``GET /v4/users/self``
  on the Domino API using the forwarded JWT. Raises if no JWT is available.
"""

from __future__ import annotations

import base64
import json
import logging
from contextvars import ContextVar
from dataclasses import dataclass
from typing import Any, Optional

logger = logging.getLogger(__name__)

_USER_ID_CLAIM_KEYS = ("id", "userId", "user_id", "sub", "dominoUserId")
_USERNAME_CLAIM_KEYS = ("userName", "username", "preferred_username", "name")

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


def _bearer_token(auth_header: Optional[str]) -> Optional[str]:
    if not auth_header:
        return None
    parts = auth_header.split(None, 1)
    if len(parts) != 2:
        return None
    return parts[1]


def _decode_jwt_payload(token: str) -> dict[str, Any]:
    segments = token.split(".")
    if len(segments) < 2:
        return {}
    padding = "=" * (-len(segments[1]) % 4)
    raw = base64.urlsafe_b64decode(segments[1] + padding)
    data = json.loads(raw)
    if not isinstance(data, dict):
        return {}
    return data


def _jwt_claim_snapshot(payload: dict[str, Any]) -> dict[str, Any]:
    keys = _USER_ID_CLAIM_KEYS + _USERNAME_CLAIM_KEYS
    return {key: payload[key] for key in keys if key in payload}


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
    with httpx.Client(follow_redirects=True, timeout=10.0) as client:
        resp = client.get(f"{host}/v4/users/self", headers=headers)
        resp.raise_for_status()
        data = resp.json()

    uid = data.get("id")
    uname = data.get("userName") or ""
    if not uid:
        raise RuntimeError("Domino /v4/users/self returned no id.")

    jwt_claims: dict[str, Any] = {}
    token = _bearer_token(get_request_auth_header())
    if token:
        try:
            jwt_claims = _jwt_claim_snapshot(_decode_jwt_payload(token))
        except Exception as exc:
            logger.warning("viewing_user jwt decode failed: %s", exc)
    logger.info(
        "viewing_user comparison users_self_id=%s users_self_userName=%s jwt_claims=%s",
        uid,
        uname,
        jwt_claims,
    )

    return User(id=uid, user_name=uname)
