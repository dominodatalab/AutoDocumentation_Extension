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


class TestDatasetManagerReadFileRaw:
    def _patch_client(self, monkeypatch, resp):
        import dataset_manager as dm

        monkeypatch.setattr(dm, "_resolve_api_host", lambda: "https://api.example")
        monkeypatch.setattr(dm, "_get_auth_headers", lambda: {})

        class Inner:
            def get(self, *a, **k):
                return resp

        class Client:
            def __enter__(self):
                return Inner()

            def __exit__(self, *a):
                return False

        monkeypatch.setattr(dm.httpx, "Client", lambda **kw: Client())

    def test_read_file_returns_plain_yaml_bytes_unchanged(self, monkeypatch):
        body = b"slug: z\ncard_title: ZZ\n"

        class Resp:
            content = body
            headers = {"content-type": "text/plain"}

            def raise_for_status(self):
                return None

        self._patch_client(monkeypatch, Resp())
        assert DatasetManager.read_file("snap", "spec-templates/x.yaml") == body

    def test_read_file_calls_file_raw_endpoint(self, monkeypatch):
        body = b"slug: z\ncard_title: ZZ\n"
        captured = {}

        class Resp:
            content = body
            headers = {"content-type": "text/plain"}

            def raise_for_status(self):
                return None

        class Inner:
            def get(self, url, **kwargs):
                captured["url"] = url
                captured["params"] = kwargs.get("params")
                return Resp()

        class Client:
            def __enter__(self):
                return Inner()

            def __exit__(self, *a):
                return False

        import dataset_manager as dm

        monkeypatch.setattr(dm, "_resolve_api_host", lambda: "https://api.example")
        monkeypatch.setattr(dm, "_get_auth_headers", lambda: {})
        monkeypatch.setattr(dm.httpx, "Client", lambda **kw: Client())

        DatasetManager.read_file("snap-99", "spec-templates/x.yaml")
        assert captured["url"].endswith("/v4/datasetrw/snapshot/snap-99/file/raw")
        assert captured["params"] == {"path": "spec-templates/x.yaml"}

    def test_read_file_does_not_transform_json_shaped_body(self, monkeypatch):
        body = b'{"content":"slug: z\\ncard_title: ZZ\\n"}'

        class Resp:
            content = body
            headers = {"content-type": "text/plain"}

            def raise_for_status(self):
                return None

        self._patch_client(monkeypatch, Resp())
        assert DatasetManager.read_file("snap", "spec-templates/x.yaml") == body

    def test_read_file_raises_on_http_error(self, monkeypatch):
        import httpx

        import dataset_manager as dm

        monkeypatch.setattr(dm, "_resolve_api_host", lambda: "https://api.example")
        monkeypatch.setattr(dm, "_get_auth_headers", lambda: {})

        req = httpx.Request(
            "GET",
            "https://api.example/v4/datasetrw/snapshot/snap/file/raw",
        )
        err_resp = httpx.Response(404, request=req, content=b"not found")

        class Inner:
            def get(self, *a, **k):
                return err_resp

        class Client:
            def __enter__(self):
                return Inner()

            def __exit__(self, *a):
                return False

        monkeypatch.setattr(dm.httpx, "Client", lambda **kw: Client())
        with pytest.raises(httpx.HTTPStatusError):
            DatasetManager.read_file("snap", "spec-templates/missing.yaml")
