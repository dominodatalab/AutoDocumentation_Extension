"""Load LLM prompts from llm_prompts/prompts.yaml."""

from __future__ import annotations

from dataclasses import dataclass
from importlib import resources
from pathlib import Path
from typing import Any, Dict, Optional

import yaml

PROMPT_SECTIONS = (
    "ranking",
    "code_analysis",
    "section_planning",
    "narrative",
    "table",
    "chart",
    "list",
)

_DEFAULT_PROMPTS_FILENAME = "prompts.yaml"


@dataclass(frozen=True)
class PromptBundle:
    version: int
    system: Dict[str, str]
    templates: Dict[str, str]
    governance: Dict[str, str]
    source_path: Path


_active: Optional[PromptBundle] = None
_cache: Dict[str, PromptBundle] = {}


class PromptLoadError(Exception):
    pass


def default_prompts_file() -> Path:
    return Path(resources.files("autodoc.llm_prompts") / _DEFAULT_PROMPTS_FILENAME)


def _validate_bundle(raw: Any, source: Path) -> PromptBundle:
    if not isinstance(raw, dict):
        raise PromptLoadError(f"{source}: root must be a mapping")

    version = raw.get("version")
    if version is None:
        raise PromptLoadError(f"{source}: missing 'version'")
    if not isinstance(version, int):
        raise PromptLoadError(f"{source}: 'version' must be an integer")

    system = raw.get("system")
    templates = raw.get("templates")
    governance = raw.get("governance")
    for key, value in (("system", system), ("templates", templates), ("governance", governance)):
        if not isinstance(value, dict):
            raise PromptLoadError(f"{source}: missing or invalid '{key}' section")

    required_system = ("default", *PROMPT_SECTIONS)
    for key in required_system:
        text = system.get(key)
        if not isinstance(text, str) or not text.strip():
            raise PromptLoadError(f"{source}: system.{key} must be a non-empty string")

    for key in PROMPT_SECTIONS:
        text = templates.get(key)
        if not isinstance(text, str) or not text.strip():
            raise PromptLoadError(f"{source}: templates.{key} must be a non-empty string")

    for key in ("instructions", "narrative_note"):
        text = governance.get(key)
        if not isinstance(text, str) or not text.strip():
            raise PromptLoadError(f"{source}: governance.{key} must be a non-empty string")

    return PromptBundle(
        version=version,
        system={k: str(system[k]).strip() for k in required_system},
        templates={k: str(templates[k]).strip() for k in PROMPT_SECTIONS},
        governance={k: str(governance[k]).strip() for k in ("instructions", "narrative_note")},
        source_path=source,
    )


def load_prompts_file(path: Path) -> PromptBundle:
    resolved = path.expanduser().resolve()
    cache_key = str(resolved)
    if cache_key in _cache:
        return _cache[cache_key]

    if not resolved.is_file():
        raise PromptLoadError(f"Prompts file not found: {resolved}")

    try:
        raw = yaml.safe_load(resolved.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise PromptLoadError(f"{resolved}: invalid YAML: {exc}") from exc

    bundle = _validate_bundle(raw, resolved)
    _cache[cache_key] = bundle
    return bundle


def configure_prompts_file(path: str | Path | None = None) -> PromptBundle:
    global _active
    if path is None or not str(path).strip():
        target = default_prompts_file()
    else:
        target = Path(path)
    bundle = load_prompts_file(target)
    _active = bundle
    return bundle


def active_prompts() -> PromptBundle:
    global _active
    if _active is None:
        configure_prompts_file(None)
    return _active


def system_prompt(section: str) -> str:
    bundle = active_prompts()
    try:
        return bundle.system[section]
    except KeyError as exc:
        raise PromptLoadError(f"Unknown system prompt section: {section}") from exc


def template_prompt(section: str) -> str:
    bundle = active_prompts()
    try:
        return bundle.templates[section]
    except KeyError as exc:
        raise PromptLoadError(f"Unknown template prompt section: {section}") from exc


def governance_text(key: str) -> str:
    bundle = active_prompts()
    try:
        return bundle.governance[key]
    except KeyError as exc:
        raise PromptLoadError(f"Unknown governance prompt key: {key}") from exc


def reset_prompt_cache() -> None:
    global _active
    _active = None
    _cache.clear()
