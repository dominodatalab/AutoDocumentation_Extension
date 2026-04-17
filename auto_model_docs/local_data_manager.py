"""Filesystem-backed dataset I/O for the CLI.

The CLI runs inside a Domino job where datasets are mounted as local
directories. All functions take mount_path as an explicit argument.
"""

from __future__ import annotations

from pathlib import Path


def write_file(mount_path: str, relative_path: str, content: bytes) -> None:
    full = Path(mount_path) / relative_path.lstrip("/")
    full.parent.mkdir(parents=True, exist_ok=True)
    full.write_bytes(content)


def read_file(mount_path: str, relative_path: str) -> bytes:
    full = Path(mount_path) / relative_path.lstrip("/")
    return full.read_bytes()


def file_exists(mount_path: str, relative_path: str) -> bool:
    full = Path(mount_path) / relative_path.lstrip("/")
    return full.is_file()


def list_files(mount_path: str, relative_path: str = "") -> list[dict]:
    base = Path(mount_path)
    target = base / relative_path.lstrip("/") if relative_path else base
    if not target.is_dir():
        return []
    results = []
    for entry in sorted(target.iterdir()):
        results.append({
            "fileName": entry.name,
            "isDirectory": entry.is_dir(),
            "sizeInBytes": entry.stat().st_size if entry.is_file() else 0,
        })
    return results
