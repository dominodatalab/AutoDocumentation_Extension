from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import yaml  # type: ignore

from dataset_manager import DatasetManager
import domino_datasets

logger = logging.getLogger(__name__)

SPEC_TEMPLATES_PREFIX = "spec-templates"

_REPO_DIR = Path(__file__).resolve().parent / "spec-templates"

_YAML_EXTS = (".yaml", ".yml")


def packaged_template_filenames() -> list[str]:
    """Return basenames of packaged spec-template YAMLs.

    This must be dynamic so new built-ins can be added by dropping YAML
    files into `_REPO_DIR`.
    """
    if not _REPO_DIR.exists():
        return []
    names: list[str] = []
    for p in _REPO_DIR.iterdir():
        if not p.is_file():
            continue
        if p.suffix.lower() not in _YAML_EXTS:
            continue
        names.append(p.name)
    return sorted(names)


def allowed_template_filenames() -> frozenset[str]:
    """Compatibility shim for older endpoints/tests.

    Returns packaged template basenames available under `_REPO_DIR`.
    """
    return frozenset(packaged_template_filenames())


def validate_gallery_template_yaml(content: bytes) -> dict[str, Any]:
    """Validate a gallery template YAML.

    Required fields:
    - slug
    - title (card_title)
    - description (card_description)
    - sections: non-empty list or non-empty mapping
    """
    meta = card_meta_from_yaml(content)
    errors: list[str] = []
    if not str(meta.get("slug") or "").strip():
        errors.append("Missing required field: slug")
    if not str(meta.get("name") or "").strip():
        errors.append("Missing required field: card_title")
    if not str(meta.get("description") or "").strip():
        errors.append("Missing required field: card_description")
    if int(meta.get("section_count") or 0) <= 0:
        errors.append("Missing required field: sections (must be non-empty)")
    if errors:
        raise ValueError("; ".join(errors))
    return meta


def dataset_rel_path(filename: str) -> str:
    return f"{SPEC_TEMPLATES_PREFIX}/{filename}"


def section_count_from_spec_dict(data: dict[str, Any]) -> int:
    sec = data.get("sections")
    if isinstance(sec, list):
        return len(sec)
    if isinstance(sec, dict):
        return len(sec)
    return 0


def card_meta_from_spec_dict(data: dict[str, Any]) -> dict[str, Any]:
    slug = str(data.get("slug") or "").strip()
    name = str(data.get("card_title") or "").strip()
    desc = str(data.get("card_description") or "").strip()
    section_count = section_count_from_spec_dict(data)
    return {
        "slug": slug,
        "name": name,
        "description": desc,
        "section_count": section_count,
    }


def card_meta_from_yaml(content: bytes) -> dict[str, Any]:
    text = (content or b"").decode("utf-8", errors="replace").lstrip("\ufeff")
    try:
        parsed = yaml.safe_load(text)
    except yaml.YAMLError:
        return {
            "slug": "",
            "name": "",
            "description": "",
            "section_count": 0,
        }
    if not isinstance(parsed, dict):
        return {
            "slug": "",
            "name": "",
            "description": "",
            "section_count": 0,
        }
    return card_meta_from_spec_dict(parsed)


def sync_builtins_to_autodoc_dataset(dataset_id: str, dest_snapshot_id: str | None = None) -> None:
    if dest_snapshot_id is None:
        dest_snapshot_id = domino_datasets.get_rw_snapshot_id(dataset_id)
    if not dest_snapshot_id:
        raise RuntimeError("Could not resolve destination snapshot for model docs dataset")

    filenames = packaged_template_filenames()
    for filename in filenames:
        src = _REPO_DIR / filename
        if not src.is_file():
            continue
        rel = dataset_rel_path(filename)
        body = src.read_bytes()
        if DatasetManager.file_exists(dest_snapshot_id, rel):
            try:
                existing = DatasetManager.read_file(dest_snapshot_id, rel)
            except Exception:
                existing = None
            if existing == body:
                continue
        DatasetManager.write_file(dataset_id, rel, body)


def catalog_from_dataset(snapshot_id: str) -> list[dict[str, Any]]:
    try:
        rows = DatasetManager.list_files(snapshot_id, SPEC_TEMPLATES_PREFIX)
    except Exception:
        logger.exception("catalog_from_dataset: list_files failed")
        return []

    names: set[str] = set()
    for row in rows:
        fn_raw = (row.get("fileName") or "").strip().replace("\\", "/")
        if row.get("isDirectory"):
            continue
        if not fn_raw.lower().endswith((".yaml", ".yml")):
            continue
        fn = fn_raw.split("/")[-1]
        if not fn:
            continue
        names.add(fn)

    out: list[dict[str, Any]] = []
    for filename in sorted(names):
        rel = dataset_rel_path(filename)
        try:
            raw = DatasetManager.read_file(snapshot_id, rel)
        except Exception:
            logger.exception("catalog_from_dataset: read_file failed")
            continue
        try:
            meta = validate_gallery_template_yaml(raw)
        except Exception:
            continue
        out.append(
            {
                "slug": str(meta.get("slug") or "").strip(),
                "name": str(meta.get("name") or "").strip(),
                "description": str(meta.get("description") or "").strip(),
                "template_file": filename,
                "section_count": int(meta.get("section_count") or 0),
            }
        )
    return out
