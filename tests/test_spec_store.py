"""Tests for spec_store.py -- spec file persistence via DatasetManager."""

from __future__ import annotations

import os
import sys
from unittest.mock import MagicMock

import pytest

_repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_pkg_dir = os.path.join(_repo_root, "auto_model_docs")
for p in (_repo_root, _pkg_dir):
    if p not in sys.path:
        sys.path.insert(0, p)

import artifact_layout
import dataset_manager
import spec_store

DS = "ds-test"
SNAP = "snap-test"


@pytest.fixture(autouse=True)
def _mock_store(monkeypatch):
    artifact_layout.reset_layout()
    artifact_layout.init_layout()

    write_mock = MagicMock()
    list_mock = MagicMock(return_value=[])
    monkeypatch.setattr(
        dataset_manager.DatasetManager, "write_file",
        staticmethod(write_mock),
    )
    monkeypatch.setattr(
        dataset_manager.DatasetManager, "list_files",
        staticmethod(list_mock),
    )

    bundle = MagicMock()
    bundle.write_file = write_mock
    bundle.list_files = list_mock
    yield bundle

    artifact_layout.reset_layout()


class TestSaveSpec:
    def test_calls_write_file(self, _mock_store):
        spec_store.save_spec(DS, "my_spec.yaml", "title: Test")
        _mock_store.write_file.assert_called_once()
        call_args = _mock_store.write_file.call_args
        assert call_args[0][0] == DS
        path = call_args[0][1]
        content = call_args[0][2]
        assert path.startswith("specs/")
        assert path.endswith("_my_spec.yaml")
        assert content == b"title: Test"

    def test_returns_dataset_path(self, _mock_store):
        result = spec_store.save_spec(DS, "spec.yaml", "content")
        assert isinstance(result, str)
        assert result.startswith("specs/")

    def test_uuid_prefix(self, _mock_store):
        result = spec_store.save_spec(DS, "spec.yaml", "content")
        filename = result.split("/")[-1]
        assert "_spec.yaml" in filename
        assert len(filename) > len("spec.yaml")

    def test_strips_directory_from_filename(self, _mock_store):
        result = spec_store.save_spec(DS, "../../etc/passwd", "sneaky")
        filename = result.split("/")[-1]
        assert "etc" not in filename
        assert "passwd" in filename

    def test_unique_names(self, _mock_store):
        p1 = spec_store.save_spec(DS, "spec.yaml", "v1")
        p2 = spec_store.save_spec(DS, "spec.yaml", "v2")
        assert p1 != p2


class TestListSpecs:
    def test_empty(self, _mock_store):
        assert spec_store.list_specs(SNAP) == []

    def test_returns_metadata(self, _mock_store):
        _mock_store.list_files.return_value = [
            {"fileName": "uuid_test.yaml", "isDirectory": False, "sizeInBytes": 1024, "lastModified": "2026-04-07"},
        ]
        specs = spec_store.list_specs(SNAP)
        assert len(specs) == 1
        assert specs[0]["name"] == "uuid_test.yaml"
        assert specs[0]["size_kb"] == 1.0

    def test_filters_directories(self, _mock_store):
        _mock_store.list_files.return_value = [
            {"fileName": "subdir", "isDirectory": True, "sizeInBytes": 0},
            {"fileName": "spec.yaml", "isDirectory": False, "sizeInBytes": 512},
        ]
        specs = spec_store.list_specs(SNAP)
        assert len(specs) == 1
        assert specs[0]["name"] == "spec.yaml"
