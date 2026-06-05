"""Domino API host resolution and auth provider configuration.

- ``user_auth``: forwarded user JWT from the incoming HTTP request (Studio).
- ``cli_auth``: API key from ``DOMINO_USER_API_KEY`` / ``DOMINO_API_KEY``.
  Used by dataset helpers when the process configures it (e.g. some jobs).
  The ``main.py`` CLI entry does not call ``configure_auth``; it does not
  use Domino REST APIs.

Configure once via ``configure_auth(provider)``. Modules such as
``domino_client`` call ``current_auth()`` when making Domino API requests.
"""

from __future__ import annotations

import logging
import os
import threading
from dataclasses import dataclass
from typing import Callable, Literal, Optional

from auth_context import get_request_auth_header

logger = logging.getLogger(__name__)


class MissingAuthError(RuntimeError):
    """No auth credentials available for a Domino API call."""


@dataclass(frozen=True)
class AuthCredentials:
    kind: Literal["jwt", "api_key"]
    token: str

    def to_headers(self) -> dict[str, str]:
        if self.kind == "jwt":
            value = self.token if self.token.startswith("Bearer ") else f"Bearer {self.token}"
            return {"Authorization": value}
        return {"X-Domino-Api-Key": self.token}


AuthProvider = Callable[[], AuthCredentials]

_auth_provider: Optional[AuthProvider] = None


def configure_auth(provider: AuthProvider) -> None:
    """Set the process-wide auth provider (e.g. ``user_auth`` for Studio)."""
    global _auth_provider
    _auth_provider = provider


def reset_auth() -> None:
    """Clear the configured provider. Mainly for tests."""
    global _auth_provider
    _auth_provider = None


def current_auth() -> AuthCredentials:
    """Return credentials from the configured provider.

    Raises ``MissingAuthError`` if no provider has been configured or
    if the provider itself cannot build credentials.
    """
    if _auth_provider is None:
        raise MissingAuthError(
            "Auth provider not configured. Call configure_auth(user_auth) "
            "or configure_auth(cli_auth) at process startup."
        )
    return _auth_provider()


def get_user_token() -> str:
    """Return the forwarded user JWT. Raises if absent."""
    forwarded = get_request_auth_header()
    if not forwarded:
        raise MissingAuthError(
            "No forwarded user token available. "
            "Domino API calls require a user token from the incoming request."
        )
    return forwarded


def get_cli_token() -> str:
    """Return the CLI/job API key from env. Raises if absent."""
    api_key = os.environ.get("DOMINO_USER_API_KEY") or os.environ.get("DOMINO_API_KEY") or ""
    if not api_key:
        raise MissingAuthError(
            "DOMINO_USER_API_KEY is not set. "
            "CLI and Domino job containers require an API key."
        )
    return api_key


def user_auth() -> AuthCredentials:
    """Provider: forwarded user JWT from the current request."""
    return AuthCredentials(kind="jwt", token=get_user_token())


def cli_auth() -> AuthCredentials:
    """Provider: API key from env. For CLI / Domino job container use only."""
    return AuthCredentials(kind="api_key", token=get_cli_token())


def resolve_api_host() -> str:
    """Return the Domino API host.

    Priority: ``DOMINO_API_PROXY`` > ``DOMINO_API_HOST``. Inside a Domino App
    container, ``DOMINO_API_PROXY`` points at the local sidecar that handles
    identity propagation; ``DOMINO_API_HOST`` is the nucleus URL.
    """
    host = os.environ.get("DOMINO_API_PROXY") or os.environ.get("DOMINO_API_HOST") or ""
    return host.rstrip("/")


def resolve_user_host() -> str:
    """Return the Domino user-facing API host for governance calls.

    Priority: ``DOMINO_USER_HOST`` > request origin (Studio UI) > ``DOMINO_API_HOST``.
    """
    host = os.environ.get("DOMINO_USER_HOST") or ""
    if host:
        return host.rstrip("/")

    from auth_context import get_request_origin

    origin = get_request_origin()
    if origin:
        return origin.rstrip("/")

    return (os.environ.get("DOMINO_API_HOST") or "").rstrip("/")
