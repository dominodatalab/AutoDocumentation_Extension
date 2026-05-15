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
    logger.info("sync_builtins_to_autodoc_dataset: start dataset_id=%r", dataset_id)
    for filename in _ORDERED_BUILTIN_FILENAMES:
        src = _REPO_DIR / filename
        if not src.is_file():
            logger.warning("sync_builtins_to_autodoc_dataset: missing packaged file %s", src)
            continue
        rel = dataset_rel_path(filename)
        body = src.read_bytes()
        logger.info(
            "sync_builtins_to_autodoc_dataset: write_file dataset_id=%r path=%r bytes=%d",
            dataset_id,
            rel,
            len(body),
        )
        DatasetManager.write_file(dataset_id, rel, body)
    logger.info("sync_builtins_to_autodoc_dataset: done")


def catalog_from_dataset(snapshot_id: str) -> list[dict[str, Any]]:
    logger.info(
        "catalog_from_dataset: listing via DatasetManager.list_files "
        "GET /v4/datasetrw/files/{snapshot_id} path=%r snapshot_id=%r",
        SPEC_TEMPLATES_PREFIX,
        snapshot_id,
    )
    try:
        rows = DatasetManager.list_files(snapshot_id, SPEC_TEMPLATES_PREFIX)
    except Exception:
        logger.exception("catalog_from_dataset: DatasetManager.list_files failed")
        return []

    for i, row in enumerate(rows[:25]):
        logger.info("catalog_from_dataset: list row[%d]=%r", i, row)
    if len(rows) > 25:
        logger.info("catalog_from_dataset: list row ... %d more rows omitted", len(rows) - 25)

    names: set[str] = set()
    for row in rows:
        fn_raw = (row.get("fileName") or "").strip().replace("\\", "/")
        if row.get("isDirectory"):
            logger.info(
                "catalog_from_dataset: list row skip directory fileName=%r",
                fn_raw,
            )
            continue
        if not fn_raw.lower().endswith((".yaml", ".yml")):
            logger.info(
                "catalog_from_dataset: list row skip non-yaml fileName=%r isDirectory=%r",
                fn_raw,
                row.get("isDirectory"),
            )
            continue
        fn = fn_raw.split("/")[-1]
        if not fn:
            logger.info("catalog_from_dataset: list row skip empty basename fileName=%r", fn_raw)
            continue
        names.add(fn)

    logger.info(
        "catalog_from_dataset: list returned %d rows, yaml basenames=%r",
        len(rows),
        sorted(names),
    )

    out: list[dict[str, Any]] = []
    for filename in _ORDERED_BUILTIN_FILENAMES:
        if filename not in names:
            logger.info(
                "catalog_from_dataset: skip %r (not in list result for path=%r)",
                filename,
                SPEC_TEMPLATES_PREFIX,
            )
            continue
        rel = dataset_rel_path(filename)
        logger.info(
            "catalog_from_dataset: read template %r snapshot_id=%r rel=%r",
            filename,
            snapshot_id,
            rel,
        )
        try:
            raw = DatasetManager.read_file(snapshot_id, rel)
        except Exception:
            logger.warning(
                "catalog_from_dataset: read_file failed for %r rel=%r snapshot_id=%r",
                filename,
                rel,
                snapshot_id,
                exc_info=True,
            )
            continue
        logger.info(
            "catalog_from_dataset: read_file ok %r raw_bytes=%d",
            filename,
            len(raw or b""),
        )
        text = (raw or b"").decode("utf-8", errors="replace").lstrip("\ufeff")
        try:
            parsed = yaml.safe_load(text)
        except yaml.YAMLError:
            head = text[:400].replace("\n", "\\n")
            logger.warning(
                "catalog_from_dataset: yaml parse failed for %r rel=%r "
                "decoded_len=%d head=%r",
                filename,
                rel,
                len(text),
                head,
            )
            continue
        logger.info(
            "catalog_from_dataset: yaml safe_load ok %r root_type=%s",
            filename,
            type(parsed).__name__,
        )
        if not isinstance(parsed, dict):
            head = text[:300].replace("\n", "\\n")
            logger.info(
                "catalog_from_dataset: skip %r parsed type=%s head=%r",
                filename,
                type(parsed).__name__,
                head,
            )
            continue
        meta = card_meta_from_spec_dict(parsed)
        slug = meta.get("slug") or ""
        name = meta.get("name") or ""
        if not slug.strip() or not name.strip():
            logger.info(
                "catalog_from_dataset: skip %r (missing slug or card_title after parse) slug=%r name=%r",
                filename,
                slug,
                name,
            )
            continue
        logger.info(
            "catalog_from_dataset: add entry %r slug=%r name=%r section_count=%r",
            filename,
            slug.strip(),
            name.strip(),
            int(meta.get("section_count") or 0),
        )
        out.append(
            {
                "slug": slug.strip(),
                "name": name.strip(),
                "description": str(meta.get("description") or "").strip(),
                "template_file": filename,
                "section_count": int(meta.get("section_count") or 0),
            }
        )
    logger.info("catalog_from_dataset: built %d catalog entries", len(out))
    return out
