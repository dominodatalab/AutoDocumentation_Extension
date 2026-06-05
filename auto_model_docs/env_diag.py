from __future__ import annotations

import logging
import os

_REDACT_SUFFIXES = ("_API_KEY", "_TOKEN", "_SECRET", "_PASSWORD")
_REDACT_EXACT = frozenset({"AUTHORIZATION"})


def _format_env_value(key: str, value: str) -> str:
    upper = key.upper()
    if upper in _REDACT_EXACT or any(upper.endswith(suffix) for suffix in _REDACT_SUFFIXES):
        return "<redacted>" if value else "<empty>"
    return value


def log_process_environment(
    logger: logging.Logger,
    label: str,
    *,
    force: bool = False,
) -> None:
    log = logger.warning if force else logger.info
    env = os.environ
    log("=== %s environment (%d vars) ===", label, len(env))
    for key in sorted(env):
        log("ENV %s=%s", key, _format_env_value(key, env.get(key, "")))
    log("=== end %s environment ===", label)
