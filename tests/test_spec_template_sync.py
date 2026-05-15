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


def test_card_meta_from_yaml_reads_slug_sections():
    raw = (
        b"slug: my-slug\n"
        b'card_title: "T"\n'
        b'card_description: "D"\n'
        b"sections:\n  - a\n  - b\n"
    )
    meta = st.card_meta_from_yaml(raw, default_slug="fallback")
    assert meta["slug"] == "my-slug"
    assert meta["name"] == "T"
    assert meta["description"] == "D"
    assert meta["section_count"] == 2


def test_card_meta_default_slug_from_filename_stem():
    raw = b"card_title: X\nsections:\n  - one\n"
    meta = st.card_meta_from_yaml(raw, default_slug="fromfile")
    assert meta["slug"] == "fromfile"
    assert meta["section_count"] == 1


def test_section_count_from_dict_sections():
    assert st.section_count_from_spec_dict({"sections": {"A": 1, "B": 2}}) == 2


def test_catalog_merges_section_count_from_repo_when_dataset_yaml_omits_sections(
    tmp_path,
    monkeypatch,
):
    import domino_datasets as dd

    monkeypatch.setattr(st, "_REPO_DIR", tmp_path)
    (tmp_path / "doc_spec_executive.yaml").write_text(
        "slug: executive\ncard_title: Executive Summary\n"
        "card_description: High-level.\n"
        "sections:\n  - A\n  - B\n  - C\n  - D\n  - E\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(
        dd,
        "list_files",
        lambda snap, prefix: [{"fileName": "doc_spec_executive.yaml", "isDirectory": False}],
    )
    monkeypatch.setattr(
        "dataset_manager.DatasetManager.read_file",
        staticmethod(
            lambda snap, rel: (
                b"slug: executive\ncard_title: Executive Summary\n"
                b"card_description: High-level.\n"
            ),
        ),
    )
    got = st.catalog_from_dataset("snap-1")
    assert len(got) == 1
    assert got[0]["section_count"] == 5


def test_card_meta_ignores_doc_title_for_card_name():
    raw = b'card_description: "D"\ntitle: "Document Title Only"\n'
    meta = st.card_meta_from_yaml(raw, default_slug="s")
    assert meta["name"] == "Template"
    assert meta["description"] == "D"


def test_card_meta_scalar_root_becomes_empty_dict():
    meta = st.card_meta_from_yaml(b"just-a-string\n", default_slug="stem")
    assert meta["slug"] == "stem"
    assert meta["name"] == "Template"
    assert meta["section_count"] == 0


def test_catalog_falls_back_to_repo_yaml(tmp_path, monkeypatch):
    import domino_datasets as dd

    monkeypatch.setattr(st, "_REPO_DIR", tmp_path)
    (tmp_path / "doc_spec.yaml").write_text(
        "slug: rv-slug\ncard_title: RV Title\ncard_description: RV Desc\nsections:\n  - a\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(
        dd,
        "list_files",
        lambda snap, prefix: [{"fileName": "doc_spec.yaml", "isDirectory": False}],
    )
    monkeypatch.setattr(
        "dataset_manager.DatasetManager.read_file",
        staticmethod(lambda snap, rel: b"scalar-only"),
    )
    got = st.catalog_from_dataset("snap-1")
    assert len(got) == 1
    assert got[0]["slug"] == "rv-slug"
    assert got[0]["name"] == "RV Title"
    assert got[0]["description"] == "RV Desc"
    assert got[0]["section_count"] == 1


def test_catalog_from_dataset(monkeypatch):
    import domino_datasets as dd

    monkeypatch.setattr(
        dd,
        "list_files",
        lambda snap, prefix: [{"fileName": "doc_spec.yaml", "isDirectory": False}],
    )
    monkeypatch.setattr(
        "dataset_manager.DatasetManager.read_file",
        staticmethod(
            lambda snap, rel: (
                b"slug: cat-slug\n"
                b"card_title: CT\n"
                b"card_description: CD\n"
                b"sections:\n  - a\n  - b\n  - c\n"
            ),
        ),
    )
    got = st.catalog_from_dataset("snap-1")
    assert len(got) == 1
    assert got[0]["slug"] == "cat-slug"
    assert got[0]["name"] == "CT"
    assert got[0]["description"] == "CD"
    assert got[0]["template_file"] == "doc_spec.yaml"
    assert got[0]["section_count"] == 3


@patch.object(st, "DatasetManager")
def test_sync_builtins_writes_each_template(mock_dm, tmp_path, monkeypatch):
    monkeypatch.setattr(st, "_REPO_DIR", tmp_path)
    for fn in st._ORDERED_BUILTIN_FILENAMES:
        (tmp_path / fn).write_bytes(b"card_title: t\ncard_description: d\n")
    st.sync_builtins_to_autodoc_dataset("ds-1")
    assert mock_dm.write_file.call_count == len(st._ORDERED_BUILTIN_FILENAMES)
