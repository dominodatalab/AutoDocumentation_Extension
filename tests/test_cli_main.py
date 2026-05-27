"""Smoke tests for auto_model_docs/main.py CLI entry."""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest
from click.testing import CliRunner

_repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_pkg_dir = os.path.join(_repo_root, "auto_model_docs")
if _pkg_dir not in sys.path:
    sys.path.insert(0, _pkg_dir)

from main import main


def _minimal_paths(tmp_path: Path) -> tuple[str, str, str]:
    spec = tmp_path / "spec.yaml"
    spec.write_text("title: T\nsections:\n  - A\n")
    code = tmp_path / "code"
    code.mkdir()
    (code / "x.py").write_text("a = 1\n")
    ds = tmp_path / "dataset"
    ds.mkdir()
    return str(spec), str(code), str(ds)


def test_help_includes_filtered_flags():
    runner = CliRunner()
    r = runner.invoke(main, ["--help"])
    assert r.exit_code == 0
    assert "--filtered-experiments" in r.output
    assert "--filtered-models" in r.output


def test_requires_domino_project_id(tmp_path):
    spec, code, ds = _minimal_paths(tmp_path)
    runner = CliRunner()
    env = dict(os.environ)
    env.pop("DOMINO_PROJECT_ID", None)
    r = runner.invoke(
        main,
        ["--spec", spec, "--code-root", code, "--output_dir", ds],
        env=env,
    )
    assert r.exit_code == 1
    assert "DOMINO_PROJECT_ID" in r.output


def test_requires_code_root_option(tmp_path):
    spec, _, ds = _minimal_paths(tmp_path)
    runner = CliRunner()
    env = {**os.environ, "DOMINO_PROJECT_ID": "p1"}
    r = runner.invoke(
        main,
        ["--spec", spec, "--output_dir", ds],
        env=env,
    )
    assert r.exit_code != 0
