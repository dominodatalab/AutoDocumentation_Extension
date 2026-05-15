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
    meta = st.card_meta_from_yaml(raw)
    assert meta["slug"] == "my-slug"
    assert meta["name"] == "T"
    assert meta["description"] == "D"
    assert meta["section_count"] == 2


def test_card_meta_empty_slug_when_slug_missing_in_yaml():
    raw = b"card_title: X\nsections:\n  - one\n"
    meta = st.card_meta_from_yaml(raw)
    assert meta["slug"] == ""
    assert meta["name"] == "X"
    assert meta["section_count"] == 1


def test_section_count_from_dict_sections():
    assert st.section_count_from_spec_dict({"sections": {"A": 1, "B": 2}}) == 2


def test_catalog_from_dataset_uses_section_list_from_dataset_bytes_only(monkeypatch):
    import domino_datasets as dd

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
                b"sections:\n  - A\n  - B\n  - C\n  - D\n  - E\n"
            ),
        ),
    )
    got = st.catalog_from_dataset("snap-1")
    assert len(got) == 1
    assert got[0]["section_count"] == 5


def test_catalog_from_dataset_ignores_packaged_dir_even_if_present(tmp_path, monkeypatch):
    import domino_datasets as dd

    monkeypatch.setattr(st, "_REPO_DIR", tmp_path)
    (tmp_path / "doc_spec.yaml").write_text(
        "slug: packaged-only\ncard_title: Packaged Title\n",
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
    assert len(got) == 0


def test_catalog_section_count_zero_when_dataset_yaml_has_no_sections(monkeypatch):
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
                b"slug: s\ncard_title: Titled\n"
                b"card_description: Described\n"
            ),
        ),
    )
    got = st.catalog_from_dataset("snap-1")
    assert len(got) == 1
    assert got[0]["name"] == "Titled"
    assert got[0]["section_count"] == 0


def test_card_meta_ignores_doc_title_for_card_name():
    raw = b'card_description: "D"\ntitle: "Document Title Only"\n'
    meta = st.card_meta_from_yaml(raw)
    assert meta["name"] == ""
    assert meta["description"] == "D"


def test_card_meta_scalar_root_yields_empty_identifiers():
    meta = st.card_meta_from_yaml(b"just-a-string\n")
    assert meta["slug"] == ""
    assert meta["name"] == ""
    assert meta["section_count"] == 0


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


def test_catalog_from_dataset_matches_builtin_when_fileName_is_full_path(monkeypatch):
    import domino_datasets as dd

    monkeypatch.setattr(
        dd,
        "list_files",
        lambda snap, prefix: [
            {"fileName": "spec-templates/doc_spec.yaml", "isDirectory": False},
        ],
    )
    monkeypatch.setattr(
        "dataset_manager.DatasetManager.read_file",
        staticmethod(
            lambda snap, rel: (
                b"slug: path-slug\n"
                b"card_title: Path Title\n"
                b"card_description: PD\n"
                b"sections:\n  - a\n"
            ),
        ),
    )
    got = st.catalog_from_dataset("snap-1")
    assert len(got) == 1
    assert got[0]["slug"] == "path-slug"
    assert got[0]["name"] == "Path Title"


@patch.object(st, "DatasetManager")
def test_sync_builtins_writes_each_template(mock_dm, tmp_path, monkeypatch):
    monkeypatch.setattr(st, "_REPO_DIR", tmp_path)
    for fn in st._ORDERED_BUILTIN_FILENAMES:
        (tmp_path / fn).write_bytes(b"card_title: t\ncard_description: d\n")
    st.sync_builtins_to_autodoc_dataset("ds-1")
    assert mock_dm.write_file.call_count == len(st._ORDERED_BUILTIN_FILENAMES)
