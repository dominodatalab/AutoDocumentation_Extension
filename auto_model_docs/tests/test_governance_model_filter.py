"""Contract tests for governance bundle model-name filter (mirrors artifact_scanner fnmatch)."""

from __future__ import annotations

import fnmatch
import json
from pathlib import Path
from typing import Any

FIXTURES_DIR = Path(__file__).parent / "fixtures" / "governance"


def _parse_patterns(raw: str) -> list[str]:
    return [p.strip() for p in raw.split(",") if p.strip()]


def _name_matches(name: str, pattern: str) -> bool:
    if "*" in pattern or "?" in pattern:
        return fnmatch.fnmatch(name, pattern)
    return name == pattern


def _bundle_model_names(bundle: dict[str, Any]) -> list[str]:
    names: list[str] = []
    for att in bundle.get("attachments") or []:
        if not isinstance(att, dict):
            continue
        idf = att.get("identifier") or {}
        if isinstance(idf, dict) and idf.get("name"):
            names.append(str(idf["name"]))
    return names


def _bundle_matches_filters(bundle: dict[str, Any], patterns: list[str]) -> bool:
    if not patterns:
        return True
    names = _bundle_model_names(bundle)
    return any(_name_matches(n, p) for n in names for p in patterns)


def _filter_bundles(bundles: list[dict[str, Any]], raw: str) -> list[dict[str, Any]]:
    patterns = _parse_patterns(raw)
    return [b for b in bundles if _bundle_matches_filters(b, patterns)]


def _load_bundles() -> list[dict[str, Any]]:
    payload = json.loads((FIXTURES_DIR / "bundles-list.json").read_text())
    return list(payload.get("data") or [])


def test_wildcard_matches_fraud_and_churn_bundles():
    bundles = _load_bundles()
    matched = _filter_bundles(bundles, "fraud*,churn*")
    assert len(matched) == 3
    names = {_bundle_model_names(b)[0] for b in matched}
    assert names == {
        "fraud-detector-v1",
        "churn-predictor-v1",
    }


def test_exact_model_name_matches_one():
    bundles = _load_bundles()
    matched = _filter_bundles(bundles, "legacy-classifier-v1")
    assert len(matched) == 1
    assert matched[0]["name"] == "legacy-classifier-v1-governance-bundle"


def test_comma_separated_patterns_union():
    bundles = _load_bundles()
    matched = _filter_bundles(bundles, "legacy-classifier-v1, fraud-detector-v1")
    assert len(matched) == 2


def test_empty_filter_returns_all():
    bundles = _load_bundles()
    assert len(_filter_bundles(bundles, "")) == len(bundles)


def test_no_match_returns_empty():
    bundles = _load_bundles()
    assert _filter_bundles(bundles, "nonexistent-model-*") == []
