from autodoc.llm import prompt_loader
from autodoc.llm.prompts import (
    GOVERNANCE_INSTRUCTIONS,
    GOVERNANCE_NARRATIVE_NOTE,
    build_code_analysis_prompt,
    build_narrative_prompt,
    build_ranking_prompt,
)


def test_loaded_prompt_sections_are_non_empty():
    bundle = prompt_loader.active_prompts()
    for key in prompt_loader.PROMPT_SECTIONS:
        assert bundle.templates[key].strip()
        assert bundle.system[key].strip()
    assert bundle.governance["instructions"].strip()
    assert bundle.governance["narrative_note"].strip()


def test_builders_use_yaml_templates():
    ranking = build_ranking_prompt([])
    assert prompt_loader.template_prompt("ranking").split("{")[0] in ranking

    code_prompt = build_code_analysis_prompt([{"file": "train.py", "content": "x = 1"}])
    assert "Analyze this machine learning codebase" in code_prompt
    assert "train.py" in code_prompt

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
    assert prompt_loader.template_prompt("narrative").split("{")[0] in narrative
    assert GOVERNANCE_INSTRUCTIONS
    assert GOVERNANCE_NARRATIVE_NOTE
