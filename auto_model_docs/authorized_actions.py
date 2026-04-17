"""Domino authorized-actions permission probe.

Exposes a single function, ``authorized_action_allowed``, that asks the
Domino authz service whether the current viewing user is allowed to
perform a given action.  All outbound calls go as the forwarded user
JWT via ``domino_auth.current_auth`` so Domino enforces its own RBAC.

The response envelope is tolerated in two shapes Domino has been known
to return:

    [ { "id": ..., "code": ..., "result": true }, ... ]
    { "actions": [ { "id": ..., ... }, ... ] }
"""

from __future__ import annotations

import logging
from typing import Any

import httpx
from pydantic import BaseModel, ConfigDict

from domino_auth import current_auth, resolve_api_host

logger = logging.getLogger(__name__)

AUTHORIZED_ACTIONS_PATH = "/account/authz/permissions/authorizedactions"
_TIMEOUT = 10.0


class AuthorizedActionRequestItem(BaseModel):
    id: str
    code: str
    context: dict[str, object] | None = None


class AuthorizedActionsRequest(BaseModel):
    actions: list[AuthorizedActionRequestItem]


class AuthorizedActionResult(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: str
    code: str
    result: bool | None = None

    def is_allowed(self) -> bool:
        return bool(self.result)


class AuthorizedActionsEnvelope(BaseModel):
    model_config = ConfigDict(extra="ignore")

    actions: list[AuthorizedActionResult] | None = None


def _parse_authorized_actions(payload: Any) -> list[AuthorizedActionResult]:
    if isinstance(payload, list):
        return [AuthorizedActionResult.model_validate(item) for item in payload]
    envelope = AuthorizedActionsEnvelope.model_validate(payload)
    return envelope.actions or []


def _post_authorized_actions(
    request_body: AuthorizedActionsRequest,
) -> list[AuthorizedActionResult]:
    host = resolve_api_host()
    if not host:
        raise RuntimeError(
            "Domino API host is not configured (DOMINO_API_PROXY / DOMINO_API_HOST)."
        )
    url = f"{host}{AUTHORIZED_ACTIONS_PATH}"
    headers = {
        **current_auth().to_headers(),
        "Content-Type": "application/json",
        "Accept": "application/json",
    }
    with httpx.Client(follow_redirects=True, timeout=_TIMEOUT) as client:
        resp = client.post(
            url,
            json=request_body.model_dump(exclude_none=True),
            headers=headers,
        )
        resp.raise_for_status()
        return _parse_authorized_actions(resp.json())


def authorized_action_allowed(action: AuthorizedActionRequestItem) -> bool:
    """Return True when Domino authz allows ``action`` for the current user."""
    request_body = AuthorizedActionsRequest(actions=[action])
    results = _post_authorized_actions(request_body)
    return any(r.is_allowed() for r in results)
