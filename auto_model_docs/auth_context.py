"""Per-request auth context."""

from __future__ import annotations

import base64
import json
from contextvars import ContextVar
from dataclasses import dataclass
from typing import Any, Optional

_auth_header_var: ContextVar[Optional[str]] = ContextVar(
    "forwarded_authorization_header", default=None
)


def set_request_auth_header(value: Optional[str]) -> None:
    _auth_header_var.set(value)


def get_request_auth_header() -> Optional[str]:
    return _auth_header_var.get()


@dataclass(frozen=True)
class User:
    id: str
    user_name: str


def _bearer_token(auth_header: str) -> Optional[str]:
    parts = auth_header.split(None, 1)
    if len(parts) != 2 or parts[0].lower() != "bearer":
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


def get_viewing_user() -> User:
    from domino_auth import get_user_token

    auth_header = get_user_token()
    token = _bearer_token(auth_header)
    if not token:
        raise RuntimeError("Authorization header is not a bearer token.")

    payload = _decode_jwt_payload(token)
    uid = payload.get("sub")
    if not uid or not isinstance(uid, str):
        raise RuntimeError("JWT payload has no sub claim.")

    uname = payload.get("preferred_username") or payload.get("userName") or ""
    if not isinstance(uname, str):
        uname = str(uname) if uname else ""

    return User(id=uid, user_name=uname)
