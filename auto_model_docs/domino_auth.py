"""Domino API host resolution and auth provider configuration.

Two auth modes exist:

- ``user_auth``: forwarded user JWT from the incoming HTTP request.
  Used on HTTP request paths (Studio routes). Raises if no token.
- ``cli_auth``: API key from env (``DOMINO_USER_API_KEY`` /
  ``DOMINO_API_KEY``). Used from the CLI / Domino job container.
  Raises if no key.

The process picks one mode at startup via ``configure_auth(provider)``.
Shared modules (``domino_client``, ``domino_datasets``, ``dataset_store``)
call ``current_auth()`` to get credentials without knowing which mode
they are in.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Callable, Literal, Optional

from auth_context import get_request_auth_header


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
    """Set the process-wide auth provider.

    Call once at startup: ``user_auth`` for the Studio FastAPI app,
    ``cli_auth`` for the CLI / Domino job container.
    """
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
    """Return the Domino API host (DOMINO_API_HOST)."""
    host = os.environ.get("DOMINO_API_HOST") or ""
    return host.rstrip("/")


def resolve_project_id(project_id: Optional[str] = None) -> str:
    """Return the given project ID. Does not fall back to the app project."""
    if not project_id:
        raise RuntimeError("No project ID available")
    return project_id
