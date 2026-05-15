"""Tests for spec_template_sync."""

from __future__ import annotations

import os
import sys
from unittest.mock import patch

import pytest

_repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_pkg_dir = os.path.join(_repo_root, "auto_model_docs")
for p in (_repo_root, _pkg_dir):
    if p not in sys.path:
        sys.path.insert(0, p)

import spec_template_sync as st


def test_allowed_template_filenames():
    assert "doc_spec.yaml" in st.allowed_template_filenames()
    assert "unknown.yaml" not in st.allowed_template_filenames()


def test_card_meta_from_yaml():
    raw = b'card_title: "T"\ncard_description: "D"\ntitle: Other\n'
    name, desc = st.card_meta_from_yaml(raw)
    assert name == "T"
    assert desc == "D"


@patch.object(st, "DatasetManager")
def test_sync_builtins_writes_each_template(mock_dm, tmp_path, monkeypatch):
    monkeypatch.setattr(st, "_REPO_DIR", tmp_path)
    for _slug, fn in st._ORDERED_BUILTIN:
        (tmp_path / fn).write_bytes(b"card_title: t\ncard_description: d\n")
    st.sync_builtins_to_autodoc_dataset("ds-1")
    assert mock_dm.write_file.call_count == len(st._ORDERED_BUILTIN)
