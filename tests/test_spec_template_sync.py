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
    names = st.allowed_template_filenames()
    assert "doc_spec.yaml" in names
    assert "doc_spec_regulated.yaml" in names
    assert "unknown.yaml" not in names


def test_packaged_template_count():
    names = st.packaged_template_filenames()
    assert len(names) == 2
    assert set(names) == {"doc_spec.yaml", "doc_spec_regulated.yaml"}


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
    monkeypatch.setattr(
        "dataset_manager.DatasetManager.list_files",
        staticmethod(
            lambda snap, prefix: [{"fileName": "doc_spec_executive.yaml", "isDirectory": False}],
        ),
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
    monkeypatch.setattr(st, "_REPO_DIR", tmp_path)
    (tmp_path / "doc_spec.yaml").write_text(
        "slug: packaged-only\ncard_title: Packaged Title\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(
        "dataset_manager.DatasetManager.list_files",
        staticmethod(
            lambda snap, prefix: [{"fileName": "doc_spec.yaml", "isDirectory": False}],
        ),
    )
    monkeypatch.setattr(
        "dataset_manager.DatasetManager.read_file",
        staticmethod(lambda snap, rel: b"scalar-only"),
    )
    got = st.catalog_from_dataset("snap-1")
    assert len(got) == 0


def test_catalog_section_count_zero_when_dataset_yaml_has_no_sections(monkeypatch):
    monkeypatch.setattr(
        "dataset_manager.DatasetManager.list_files",
        staticmethod(
            lambda snap, prefix: [{"fileName": "doc_spec.yaml", "isDirectory": False}],
        ),
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
    assert got == []


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
    monkeypatch.setattr(
        "dataset_manager.DatasetManager.list_files",
        staticmethod(
            lambda snap, prefix: [{"fileName": "doc_spec.yaml", "isDirectory": False}],
        ),
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
    monkeypatch.setattr(
        "dataset_manager.DatasetManager.list_files",
        staticmethod(
            lambda snap, prefix: [
                {"fileName": "spec-templates/doc_spec.yaml", "isDirectory": False},
            ],
        ),
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
def test_catalog_from_dataset_returns_user_saved_template(mock_dm):
    user_yaml = (
        b"slug: executive\n"
        b'card_title: "Executive Summary by bira"\n'
        b"card_description: High-level model summary written for non-technical stakeholders and leadership.\n"
        b"sections:\n  - Overview\n"
    )
    mock_dm.list_files.return_value = [
        {"fileName": "doc_spec_executive.yaml", "isDirectory": False},
    ]
    mock_dm.read_file.return_value = user_yaml
    got = st.catalog_from_dataset("snap-1")
    assert len(got) == 1
    assert got[0]["name"] == "Executive Summary by bira"


@patch.object(st, "DatasetManager")
def test_sync_builtins_skips_existing_file_even_when_content_differs(mock_dm, tmp_path, monkeypatch):
    monkeypatch.setattr(st, "_REPO_DIR", tmp_path)
    monkeypatch.setattr(st.domino_datasets, "get_rw_snapshot_id", lambda _ds: "snap-dst")
    (tmp_path / "doc_spec.yaml").write_bytes(
        b"slug: s\ncard_title: T\ncard_description: D\nsections:\n  - new\n"
    )
    mock_dm.file_exists.return_value = True
    st.sync_builtins_to_autodoc_dataset("ds-1")
    mock_dm.write_file.assert_not_called()


@patch.object(st, "DatasetManager")
def test_sync_builtins_skips_when_packaged_content_unchanged(mock_dm, tmp_path, monkeypatch):
    monkeypatch.setattr(st, "_REPO_DIR", tmp_path)
    monkeypatch.setattr(st.domino_datasets, "get_rw_snapshot_id", lambda _ds: "snap-dst")
    body = b"slug: s\ncard_title: T\ncard_description: D\nsections:\n  - same\n"
    (tmp_path / "doc_spec.yaml").write_bytes(body)
    mock_dm.file_exists.return_value = True
    mock_dm.read_file.return_value = body
    st.sync_builtins_to_autodoc_dataset("ds-1")
    mock_dm.write_file.assert_not_called()


@patch.object(st, "DatasetManager")
def test_sync_builtins_writes_each_template(mock_dm, tmp_path, monkeypatch):
    monkeypatch.setattr(st, "_REPO_DIR", tmp_path)
    # Destination snapshot id resolution is required for the no-overwrite logic.
    monkeypatch.setattr(st.domino_datasets, "get_rw_snapshot_id", lambda _ds: "snap-dst")

    (tmp_path / "a.yaml").write_bytes(
        b"slug: a-slug\ncard_title: A\ncard_description: AD\nsections:\n  - s1\n"
    )
    (tmp_path / "b.yml").write_bytes(
        b"slug: b-slug\ncard_title: B\ncard_description: BD\nsections: [x]\n"
    )
    (tmp_path / "not-yaml.txt").write_text("ignore", encoding="utf-8")

    mock_dm.file_exists.return_value = False
    st.sync_builtins_to_autodoc_dataset("ds-1")

    assert mock_dm.write_file.call_count == 2
    write_paths = [c.args[1] for c in mock_dm.write_file.call_args_list]
    assert st.dataset_rel_path("a.yaml") in write_paths
    assert st.dataset_rel_path("b.yml") in write_paths


def test_all_packaged_yaml_are_gallery_valid():
    for fn in st.packaged_template_filenames():
        raw = (st._REPO_DIR / fn).read_bytes()
        st.validate_gallery_template_yaml(raw)


def test_all_packaged_templates_include_governance_sections():
    import yaml

    dev_section = "Development History: per_model"
    gov_section = "Governance & Risk"
    for fn in st.packaged_template_filenames():
        data = yaml.safe_load((st._REPO_DIR / fn).read_text(encoding="utf-8"))
        sections = data.get("sections") or []
        assert dev_section in sections, fn
        assert gov_section in sections, fn
        hints = data.get("hints") or {}
        assert "Development History" in hints, fn
        assert "Governance & Risk" in hints, fn
        assert "model_of_record" in hints["Governance & Risk"], fn
        assert "development candidates" in hints["Development History"], fn


def test_non_governance_hints_direct_readers_to_governance_section():
    import yaml

    gov_section = "Governance & Risk"
    for fn in st.packaged_template_filenames():
        data = yaml.safe_load((st._REPO_DIR / fn).read_text(encoding="utf-8"))
        hints = data.get("hints") or {}
        for key, value in hints.items():
            if key == gov_section:
                continue
            assert "Governance & Risk" in value, f"{fn}:{key}"
            if key == "Development History":
                assert "governed model status" in value, f"{fn}:{key}"
            else:
                assert "see Governance & Risk" in value, f"{fn}:{key}"
