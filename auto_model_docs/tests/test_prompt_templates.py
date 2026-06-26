from autodoc.llm import prompt_templates as templates
from autodoc.llm.prompts import (
    build_code_analysis_prompt,
    build_narrative_prompt,
    build_ranking_prompt,
)


def test_prompt_templates_are_non_empty():
    for name in (
        "DEFAULT_SYSTEM_PROMPT",
        "SYSTEM_NARRATIVE_WRITER",
        "GOVERNANCE_ANTI_FABRICATION",
        "RANKING_PROMPT_TEMPLATE",
        "CODE_ANALYSIS_PROMPT_TEMPLATE",
        "NARRATIVE_PROMPT_TEMPLATE",
    ):
        value = getattr(templates, name)
        assert isinstance(value, str)
        assert value.strip()


def test_builders_use_templates():
    ranking = build_ranking_prompt([])
    assert templates.RANKING_PROMPT_TEMPLATE.split("{")[0] in ranking

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
    assert templates.NARRATIVE_PROMPT_TEMPLATE.split("{")[0] in narrative
