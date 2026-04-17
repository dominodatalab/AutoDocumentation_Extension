from pathlib import Path

import pytest

from autodoc.llm import prompt_loader
from autodoc.llm.prompt_loader import PromptLoadError, configure_prompts_file, default_prompts_file
from autodoc.llm.prompts import (
    GOVERNANCE_INSTRUCTIONS,
    build_narrative_prompt,
    build_ranking_prompt,
    narrative_system_prompt,
)


@pytest.fixture(autouse=True)
def _reset_prompt_state():
    prompt_loader.reset_prompt_cache()
    configure_prompts_file(None)
    yield
    prompt_loader.reset_prompt_cache()


def test_default_prompts_file_exists():
    path = default_prompts_file()
    assert path.is_file()


def test_load_default_prompt_sections():
    bundle = configure_prompts_file(None)
    assert bundle.version == 1
    for key in prompt_loader.PROMPT_SECTIONS:
        assert bundle.system[key].strip()
        assert bundle.templates[key].strip()
    assert bundle.system["default"].strip()
    assert bundle.governance["instructions"].strip()
    assert bundle.governance["narrative_note"].strip()


def test_configure_prompts_file_override(tmp_path):
    custom = tmp_path / "custom_prompts.yaml"
    custom.write_text(
        (default_prompts_file().read_text(encoding="utf-8")).replace(
            "You are a technical documentation expert.",
            "You are a custom default system prompt.",
            1,
        ),
        encoding="utf-8",
    )
    bundle = configure_prompts_file(custom)
    assert bundle.source_path == custom.resolve()
    assert "custom default system prompt" in prompt_loader.system_prompt("default")


def test_missing_prompts_file_raises():
    with pytest.raises(PromptLoadError, match="not found"):
        configure_prompts_file("/no/such/prompts.yaml")


def test_invalid_prompts_file_raises(tmp_path):
    bad = tmp_path / "bad.yaml"
    bad.write_text("version: 1\nsystem: {}\n", encoding="utf-8")
    with pytest.raises(PromptLoadError, match="invalid 'templates' section"):
        configure_prompts_file(bad)


def test_builders_use_loaded_templates():
    ranking = build_ranking_prompt([])
    assert "Analyze the following file cards" in ranking

    narrative = build_narrative_prompt(
        section_name="Overview",
        purpose="Summarize",
        data_needed=None,
        model_classes="XGB",
        ml_task_type="classification",
        target_variable="y",
        features="a,b",
        data_sources="csv",
        model_name=None,
        model_info="",
        insights="",
    )
    assert "Write professional documentation content." in narrative
    assert GOVERNANCE_INSTRUCTIONS not in narrative


def test_governance_instructions_alias():
    assert GOVERNANCE_INSTRUCTIONS == prompt_loader.governance_text("instructions")
    assert narrative_system_prompt("x") != narrative_system_prompt("")
