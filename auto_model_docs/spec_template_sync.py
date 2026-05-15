from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import yaml

from dataset_manager import DatasetManager

logger = logging.getLogger(__name__)

SPEC_TEMPLATES_PREFIX = "spec-templates"

_REPO_DIR = Path(__file__).resolve().parent / "spec-templates"

_ORDERED_BUILTIN_FILENAMES: tuple[str, ...] = (
    "doc_spec.yaml",
    "doc_spec_llm_eval.yaml",
    "doc_spec_fairness.yaml",
    "doc_spec_executive.yaml",
)

_ALLOWED_FILENAMES = frozenset(_ORDERED_BUILTIN_FILENAMES)


def allowed_template_filenames() -> frozenset[str]:
    return _ALLOWED_FILENAMES


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


def sync_builtins_to_autodoc_dataset(dataset_id: str) -> None:
    for filename in _ORDERED_BUILTIN_FILENAMES:
        src = _REPO_DIR / filename
        if not src.is_file():
            logger.warning("Missing repo spec template %s", src)
            continue
        DatasetManager.write_file(dataset_id, dataset_rel_path(filename), src.read_bytes())


def catalog_from_dataset(snapshot_id: str) -> list[dict[str, Any]]:
    from domino_datasets import list_files as ds_list_files

    try:
        rows = ds_list_files(snapshot_id, SPEC_TEMPLATES_PREFIX)
    except Exception:
        logger.exception("list_files for spec-templates failed")
        return []

    names: set[str] = set()
    for row in rows:
        fn_raw = (row.get("fileName") or "").strip().replace("\\", "/")
        if row.get("isDirectory") or not fn_raw.lower().endswith((".yaml", ".yml")):
            continue
        fn = fn_raw.split("/")[-1]
        if not fn:
            continue
        names.add(fn)

    out: list[dict[str, Any]] = []
    for filename in _ORDERED_BUILTIN_FILENAMES:
        if filename not in names:
            continue
        try:
            raw = DatasetManager.read_file(snapshot_id, dataset_rel_path(filename))
        except Exception:
            logger.warning("read_file failed for %s", filename, exc_info=True)
            continue
        text = (raw or b"").decode("utf-8", errors="replace").lstrip("\ufeff")
        try:
            parsed = yaml.safe_load(text)
        except yaml.YAMLError:
            logger.warning("yaml parse failed for %s", filename)
            continue
        if not isinstance(parsed, dict):
            continue
        meta = card_meta_from_spec_dict(parsed)
        slug = meta.get("slug") or ""
        name = meta.get("name") or ""
        if not slug.strip() or not name.strip():
            continue
        out.append(
            {
                "slug": slug.strip(),
                "name": name.strip(),
                "description": str(meta.get("description") or "").strip(),
                "template_file": filename,
                "section_count": int(meta.get("section_count") or 0),
            }
        )
    return out
