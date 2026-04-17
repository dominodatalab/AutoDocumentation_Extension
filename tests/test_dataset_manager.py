"""Invariants for the stateless DatasetManager facade and local_data_manager module."""

from __future__ import annotations

import inspect
import os
import sys
import tempfile

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


class TestLocalDataManager:
    def test_write_and_read(self):
        import local_data_manager
        with tempfile.TemporaryDirectory() as tmp:
            local_data_manager.write_file(tmp, "test/hello.txt", b"world")
            assert local_data_manager.read_file(tmp, "test/hello.txt") == b"world"

    def test_file_exists(self):
        import local_data_manager
        with tempfile.TemporaryDirectory() as tmp:
            assert not local_data_manager.file_exists(tmp, "nope.txt")
            local_data_manager.write_file(tmp, "yep.txt", b"hi")
            assert local_data_manager.file_exists(tmp, "yep.txt")

    def test_list_files(self):
        import local_data_manager
        with tempfile.TemporaryDirectory() as tmp:
            local_data_manager.write_file(tmp, "a.txt", b"aa")
            local_data_manager.write_file(tmp, "sub/b.txt", b"bb")
            root_files = local_data_manager.list_files(tmp)
            names = {f["fileName"] for f in root_files}
            assert "a.txt" in names
            assert "sub" in names
            sub_files = local_data_manager.list_files(tmp, "sub")
            assert len(sub_files) == 1
            assert sub_files[0]["fileName"] == "b.txt"
