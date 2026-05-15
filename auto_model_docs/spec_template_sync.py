from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import yaml

from dataset_manager import DatasetManager

logger = logging.getLogger(__name__)

SPEC_TEMPLATES_PREFIX = "spec-templates"

_REPO_DIR = Path(__file__).resolve().parent / "spec-templates"

_ORDERED_BUILTIN: tuple[tuple[str, str], ...] = (
    ("standard_ml", "doc_spec.yaml"),
    ("llm_eval", "doc_spec_llm_eval.yaml"),
    ("fairness", "doc_spec_fairness.yaml"),
    ("executive", "doc_spec_executive.yaml"),
)

_ALLOWED_FILENAMES = frozenset(fn for _, fn in _ORDERED_BUILTIN)


def allowed_template_filenames() -> frozenset[str]:
    return _ALLOWED_FILENAMES


def dataset_rel_path(filename: str) -> str:
    return f"{SPEC_TEMPLATES_PREFIX}/{filename}"


def card_meta_from_yaml(content: bytes) -> tuple[str, str]:
    data = yaml.safe_load(content.decode("utf-8")) or {}
    name = str(data.get("card_title") or data.get("title") or "Template").strip()
    desc = str(data.get("card_description") or "").strip()
    return name, desc


def sync_builtins_to_autodoc_dataset(dataset_id: str) -> None:
    for _slug, filename in _ORDERED_BUILTIN:
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
        fn = (row.get("fileName") or "").strip()
        if row.get("isDirectory") or not fn.lower().endswith((".yaml", ".yml")):
            continue
        if "/" in fn:
            continue
        names.add(fn)

    out: list[dict[str, Any]] = []
    for slug, filename in _ORDERED_BUILTIN:
        if filename not in names:
            continue
        try:
            raw = DatasetManager.read_file(snapshot_id, dataset_rel_path(filename))
        except Exception:
            logger.warning("read_file failed for %s", filename, exc_info=True)
            continue
        try:
            title, desc = card_meta_from_yaml(raw)
        except Exception:
            logger.warning("yaml parse failed for %s", filename, exc_info=True)
            title, desc = filename, ""
        out.append(
            {
                "slug": slug,
                "name": title,
                "description": desc,
                "template_file": filename,
            }
        )
    return out
