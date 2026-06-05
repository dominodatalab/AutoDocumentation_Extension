"""CLI tests for --bundle-id (B6)."""

from __future__ import annotations

import os
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from click.testing import CliRunner

_repo_root = Path(__file__).resolve().parents[2]
_pkg_dir = _repo_root / "auto_model_docs"
for p in (str(_repo_root), str(_pkg_dir)):
    if p not in sys.path:
        sys.path.insert(0, p)

from autodoc.core.models import GovernanceContext
from main import main


@pytest.fixture(autouse=True)
def _env(monkeypatch, tmp_path):
    monkeypatch.setenv("DOMINO_PROJECT_ID", "proj-123")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    monkeypatch.chdir(tmp_path)


def _spec_file(tmp_path: Path) -> str:
    spec = tmp_path / "spec.yaml"
    spec.write_text(
        "title: Test\nsections:\n  - Overview\n",
        encoding="utf-8",
    )
    code = tmp_path / "code"
    code.mkdir()
    (code / "train.py").write_text("print('ok')\n", encoding="utf-8")
    return str(spec), str(code)


class TestMainGovernanceCli:
    def test_without_bundle_id_does_not_load_governance(self, tmp_path):
        spec_path, code_path = _spec_file(tmp_path)
        runner = CliRunner()

        with patch("main.Orchestrator") as mock_orch_cls, patch(
            "main.LLMClient"
        ), patch("main.ContentSanitizer"), patch(
            "autodoc.governance_read.load_governance_context"
        ) as mock_load:
            mock_orch = MagicMock()
            mock_orch.generate = AsyncMock(return_value=tmp_path / "out.docx")
            mock_orch.run_dir = "docs/test"
            mock_orch_cls.return_value = mock_orch

            result = runner.invoke(
                main,
                ["--spec", spec_path, "--code-root", code_path, "--provider", "anthropic"],
            )

        assert result.exit_code == 0
        mock_load.assert_not_called()
        assert mock_orch.generate.await_args.kwargs.get("governance_context") is None

    def test_with_bundle_id_loads_and_passes_context(self, tmp_path):
        spec_path, code_path = _spec_file(tmp_path)
        runner = CliRunner()
        gov = GovernanceContext(bundle_id="bundle-uuid-1", bundle_name="Test Bundle")

        with patch("main.Orchestrator") as mock_orch_cls, patch(
            "main.LLMClient"
        ), patch("main.ContentSanitizer"), patch(
            "autodoc.governance_read.load_governance_context", return_value=gov
        ) as mock_load, patch("domino_auth.configure_auth") as mock_configure_auth:
            mock_orch = MagicMock()
            mock_orch.generate = AsyncMock(return_value=tmp_path / "out.docx")
            mock_orch.run_dir = "docs/test"
            mock_orch_cls.return_value = mock_orch

            result = runner.invoke(
                main,
                [
                    "--spec",
                    spec_path,
                    "--code-root",
                    code_path,
                    "--provider",
                    "anthropic",
                    "--bundle-id",
                    "bundle-uuid-1",
                    "--findings-scope",
                    "open",
                ],
            )

        assert result.exit_code == 0
        from domino_auth import cli_auth

        mock_configure_auth.assert_called_once_with(cli_auth)
        mock_load.assert_called_once()
        passed = mock_orch.generate.await_args.kwargs.get("governance_context")
        assert passed is gov

    def test_bundle_load_failure_exits(self, tmp_path):
        spec_path, code_path = _spec_file(tmp_path)
        runner = CliRunner()

        from autodoc.governance_read import GovernanceLoadError

        with patch("main.LLMClient"), patch("main.ContentSanitizer"), patch(
            "autodoc.governance_read.load_governance_context",
            side_effect=GovernanceLoadError("boom"),
        ), patch("domino_auth.configure_auth"), patch("domino_auth.cli_auth"):
            result = runner.invoke(
                main,
                [
                    "--spec",
                    spec_path,
                    "--code-root",
                    code_path,
                    "--provider",
                    "anthropic",
                    "--bundle-id",
                    "missing-bundle",
                ],
            )

        assert result.exit_code == 1
