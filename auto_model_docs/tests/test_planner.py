import pytest

from autodoc.core.models import (
    ArtifactContext,
    CodeContext,
    ContentType,
    GenerationContext,
    SectionSpec,
)
from autodoc.generation.planner import SectionPlanner
from autodoc.scanning.sanitizer import ContentSanitizer


@pytest.fixture
def planner(mock_llm):
    return SectionPlanner(llm=mock_llm, sanitizer=ContentSanitizer())


@pytest.fixture
def plan_context():
    return GenerationContext(
        code_context=CodeContext(
            model_classes=["XGBClassifier"],
            features=["x1", "x2"],
            ml_task_type="classification",
            target_variable="y",
            data_sources=["data.csv"],
        ),
        artifact_context=ArtifactContext(),
        section_name="Model Overview",
    )


@pytest.fixture
def section():
    return SectionSpec(name="Model Overview")


class TestSectionPlanner:
    @pytest.mark.asyncio
    async def test_valid_plan(self, planner, mock_llm, section, plan_context):
        mock_llm.complete_json.return_value = {
            "section_title": "Overview",
            "content_blocks": [
                {
                    "type": "table",
                    "purpose": "Show metrics",
                    "data_needed": "metrics",
                },
            ],
        }

        plan = await planner.plan_section(section, plan_context)

        assert plan.title == "Overview"
        assert len(plan.content_blocks) == 1
        assert plan.content_blocks[0].type == ContentType.TABLE

    @pytest.mark.asyncio
    async def test_string_content_blocks_uses_fallback(self, planner, mock_llm, section, plan_context):
        mock_llm.complete_json.return_value = {
            "section_title": "Overview",
            "content_blocks": "bad",
        }

        plan = await planner.plan_section(section, plan_context)

        assert len(plan.content_blocks) == 1
        assert plan.content_blocks[0].type == ContentType.NARRATIVE
        assert "Describe" in plan.content_blocks[0].purpose

    @pytest.mark.asyncio
    async def test_null_content_blocks_uses_fallback(self, planner, mock_llm, section, plan_context):
        mock_llm.complete_json.return_value = {
            "section_title": "Overview",
            "content_blocks": None,
        }

        plan = await planner.plan_section(section, plan_context)

        assert len(plan.content_blocks) == 1
        assert plan.content_blocks[0].type == ContentType.NARRATIVE

    @pytest.mark.asyncio
    async def test_skips_non_dict_blocks(self, planner, mock_llm, section, plan_context):
        mock_llm.complete_json.return_value = {
            "section_title": "Overview",
            "content_blocks": [
                "bad",
                {"type": "bullet_list", "purpose": "Key points", "data_needed": "context"},
            ],
        }

        plan = await planner.plan_section(section, plan_context)

        assert len(plan.content_blocks) == 1
        assert plan.content_blocks[0].type == ContentType.BULLET_LIST
