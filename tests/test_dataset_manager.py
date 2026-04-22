"""Invariants for the stateless DatasetManager facade.

These tests are structural, not behavioral: they exist to detect regressions
if someone later adds instance state, a class attribute, or a non-static
method to DatasetManager. The whole point of the class is that it holds no
state; tests here guard that promise.
"""

from __future__ import annotations

import inspect
import os
import sys

import pytest

_repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_pkg_dir = os.path.join(_repo_root, "auto_model_docs")
for p in (_repo_root, _pkg_dir):
    if p not in sys.path:
        sys.path.insert(0, p)

import dataset_manager
from dataset_manager import DatasetManager


class TestDatasetManagerShape:
    def test_has_no_custom_init(self):
        assert DatasetManager.__init__ is object.__init__

    def test_instance_has_no_attributes(self):
        inst = DatasetManager()
        assert vars(inst) == {}

    def test_has_no_class_level_data_attributes(self):
        own = set(vars(DatasetManager).keys()) - set(vars(object).keys())
        allowed_dunders = {"__module__", "__qualname__", "__dict__", "__weakref__", "__doc__"}
        for name in own:
            if name in allowed_dunders:
                continue
            value = vars(DatasetManager)[name]
            assert isinstance(value, staticmethod), (
                f"DatasetManager.{name!r} is {type(value).__name__}; "
                "all members must be staticmethods (no instance or class state)."
            )

    def test_all_public_methods_are_static(self):
        for name, member in inspect.getmembers(DatasetManager):
            if name.startswith("_"):
                continue
            raw = inspect.getattr_static(DatasetManager, name)
            assert isinstance(raw, staticmethod), (
                f"DatasetManager.{name} must be defined as @staticmethod"
            )

    def test_has_no_slots(self):
        assert not hasattr(DatasetManager, "__slots__") or DatasetManager.__slots__ == ()

    def test_expected_static_methods_exist(self):
        expected = {"write_file", "read_file", "read_file_meta", "list_files", "file_exists"}
        actual = {
            n for n in dir(DatasetManager)
            if not n.startswith("_") and callable(getattr(DatasetManager, n))
        }
        missing = expected - actual
        assert not missing, f"missing expected static methods: {missing}"


class TestResolveAutodocDataset:
    def test_returns_ids_from_rw_snapshot_id(self, monkeypatch):
        import domino_datasets

        monkeypatch.setattr(
            domino_datasets, "ensure_dataset",
            lambda project_id, name, description: {
                "id": "ds-1", "rwSnapshotId": "snap-1",
            },
        )
        monkeypatch.setattr(
            domino_datasets, "get_rw_snapshot_id",
            lambda *a, **kw: "should-not-be-called",
        )

        ds_id, snap_id = dataset_manager.resolve_autodoc_dataset("proj-1")
        assert ds_id == "ds-1"
        assert snap_id == "snap-1"

    def test_falls_back_to_get_rw_snapshot_id(self, monkeypatch):
        import domino_datasets

        monkeypatch.setattr(
            domino_datasets, "ensure_dataset",
            lambda project_id, name, description: {"id": "ds-2"},
        )
        monkeypatch.setattr(
            domino_datasets, "get_rw_snapshot_id",
            lambda *a, **kw: "snap-2",
        )

        ds_id, snap_id = dataset_manager.resolve_autodoc_dataset("proj-2")
        assert (ds_id, snap_id) == ("ds-2", "snap-2")

    def test_raises_when_no_dataset_id(self, monkeypatch):
        import domino_datasets

        monkeypatch.setattr(
            domino_datasets, "ensure_dataset",
            lambda project_id, name, description: {"rwSnapshotId": "snap-x"},
        )
        with pytest.raises(RuntimeError, match="no ID"):
            dataset_manager.resolve_autodoc_dataset("proj-3")

    def test_raises_when_no_snapshot_id(self, monkeypatch):
        import domino_datasets

        monkeypatch.setattr(
            domino_datasets, "ensure_dataset",
            lambda project_id, name, description: {"id": "ds-4"},
        )
        monkeypatch.setattr(
            domino_datasets, "get_rw_snapshot_id",
            lambda *a, **kw: "",
        )
        with pytest.raises(RuntimeError, match="rw snapshot"):
            dataset_manager.resolve_autodoc_dataset("proj-4")


class TestDatasetCtx:
    def test_set_requires_both_ids(self):
        import dataset_ctx
        with pytest.raises(ValueError):
            dataset_ctx.set_dataset_ctx("", "snap")
        with pytest.raises(ValueError):
            dataset_ctx.set_dataset_ctx("ds", "")

    def test_get_raises_when_unset(self):
        import dataset_ctx
        dataset_ctx.clear_dataset_ctx()
        with pytest.raises(RuntimeError, match="Dataset context not set"):
            dataset_ctx.get_dataset_ctx()

    def test_round_trip(self):
        import dataset_ctx
        dataset_ctx.set_dataset_ctx("ds-abc", "snap-abc")
        ctx = dataset_ctx.get_dataset_ctx()
        assert ctx.dataset_id == "ds-abc"
        assert ctx.snapshot_id == "snap-abc"
        dataset_ctx.clear_dataset_ctx()
