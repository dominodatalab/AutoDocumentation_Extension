import logging
from unittest.mock import MagicMock

from env_diag import _format_env_value, log_process_environment


def test_format_env_value_redacts_secrets():
    assert _format_env_value("DOMINO_USER_API_KEY", "secret") == "<redacted>"
    assert _format_env_value("DOMINO_API_HOST", "https://host.example") == "https://host.example"


def test_log_process_environment_emits_sorted_keys(monkeypatch):
    monkeypatch.setenv("ZZZ_LAST", "z")
    monkeypatch.setenv("AAA_FIRST", "a")
    monkeypatch.setenv("DOMINO_USER_API_KEY", "secret")
    logger = MagicMock()
    log_process_environment(logger, "test")
    assert logger.info.call_args_list[0].args[0] == "=== %s environment (%d vars) ==="
    env_lines = [
        (call.args[1], call.args[2])
        for call in logger.info.call_args_list
        if call.args and call.args[0] == "ENV %s=%s"
    ]
    assert ("AAA_FIRST", "a") in env_lines
    assert ("DOMINO_USER_API_KEY", "<redacted>") in env_lines


def test_log_process_environment_force_uses_warning(monkeypatch):
    monkeypatch.setenv("DOMINO_API_PROXY", "http://localhost:8899")
    logger = MagicMock()
    log_process_environment(logger, "job", force=True)
    assert logger.warning.called
    assert not logger.info.called
