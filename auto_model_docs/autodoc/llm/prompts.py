"""LLM prompt builders and JSON schemas for Auto Model Documentation."""

from typing import Any, Dict, List, Optional, TYPE_CHECKING

from autodoc.llm import prompt_loader

__all__ = [
    "CHART_SCHEMA",
    "CODE_ANALYSIS_SCHEMA",
    "GOVERNANCE_INSTRUCTIONS",
    "GOVERNANCE_NARRATIVE_NOTE",
    "LIST_SCHEMA",
    "RANKING_SCHEMA",
    "SECTION_PLANNING_SCHEMA",
    "SYSTEM_CHART_GENERATOR",
    "SYSTEM_CODE_ANALYZER",
    "SYSTEM_FILE_RANKER",
    "SYSTEM_LIST_GENERATOR",
    "SYSTEM_NARRATIVE_WRITER",
    "SYSTEM_SECTION_PLANNER",
    "SYSTEM_TABLE_GENERATOR",
    "TABLE_SCHEMA",
    "build_chart_prompt",
    "build_code_analysis_prompt",
    "build_list_prompt",
    "build_narrative_prompt",
    "build_ranking_prompt",
    "build_section_planning_prompt",
    "build_table_prompt",
    "narrative_system_prompt",
]

_EXPORT_ALIASES = {
    "DEFAULT_SYSTEM_PROMPT": lambda: prompt_loader.system_prompt("default"),
    "GOVERNANCE_ANTI_FABRICATION": lambda: prompt_loader.governance_text("instructions"),
    "GOVERNANCE_INSTRUCTIONS": lambda: prompt_loader.governance_text("instructions"),
    "GOVERNANCE_NARRATIVE_NOTE": lambda: prompt_loader.governance_text("narrative_note"),
    "GOVERNANCE_SYSTEM_NOTE": lambda: prompt_loader.governance_text("narrative_note"),
    "RANKING_PROMPT_TEMPLATE": lambda: prompt_loader.template_prompt("ranking"),
    "CODE_ANALYSIS_PROMPT_TEMPLATE": lambda: prompt_loader.template_prompt("code_analysis"),
    "SECTION_PLANNING_PROMPT_TEMPLATE": lambda: prompt_loader.template_prompt("section_planning"),
    "NARRATIVE_PROMPT_TEMPLATE": lambda: prompt_loader.template_prompt("narrative"),
    "TABLE_PROMPT_TEMPLATE": lambda: prompt_loader.template_prompt("table"),
    "CHART_PROMPT_TEMPLATE": lambda: prompt_loader.template_prompt("chart"),
    "LIST_PROMPT_TEMPLATE": lambda: prompt_loader.template_prompt("list"),
    "SYSTEM_FILE_RANKER": lambda: prompt_loader.system_prompt("ranking"),
    "SYSTEM_CODE_ANALYZER": lambda: prompt_loader.system_prompt("code_analysis"),
    "SYSTEM_SECTION_PLANNER": lambda: prompt_loader.system_prompt("section_planning"),
    "SYSTEM_NARRATIVE_WRITER": lambda: prompt_loader.system_prompt("narrative"),
    "SYSTEM_TABLE_GENERATOR": lambda: prompt_loader.system_prompt("table"),
    "SYSTEM_CHART_GENERATOR": lambda: prompt_loader.system_prompt("chart"),
    "SYSTEM_LIST_GENERATOR": lambda: prompt_loader.system_prompt("list"),
}


def __getattr__(name: str):
    if name in _EXPORT_ALIASES:
        return _EXPORT_ALIASES[name]()
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

if TYPE_CHECKING:
    from autodoc.core.models import LanguageProfile
    from autodoc.scanning.file_card import FileCard


def build_ranking_prompt(
    file_cards: List["FileCard"],
    profile: Optional["LanguageProfile"] = None,
) -> str:
    cards_text = "\n\n".join(card.to_prompt_text() for card in file_cards)
    framework_line = ""
    if profile:
        framework_line = f"\nLanguage: {profile.display_name}\n{profile.framework_hints}"
    return prompt_loader.template_prompt("ranking").format(
        framework_line=framework_line,
        cards_text=cards_text,
    )


RANKING_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "ranked_files": {
            "type": "array",
            "description": "Files ranked by documentation importance, most important first",
            "items": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Relative file path"},
                    "role": {
                        "type": "string",
                        "description": "ML role: entrypoint, training, preprocessing, inference, evaluation, config, utility, irrelevant",
                    },
                    "confidence": {
                        "type": "number",
                        "description": "Confidence in classification (0.0 to 1.0)",
                    },
                    "reason": {
                        "type": "string",
                        "description": "Brief reason for this classification",
                    },
                },
                "required": ["path", "role"],
            },
        }
    },
    "required": ["ranked_files"],
}


def build_code_analysis_prompt(
    code_contents: List[Dict[str, str]],
    profile: Optional["LanguageProfile"] = None,
    file_roles: Optional[Dict[str, str]] = None,
) -> str:
    fence_lang = profile.code_fence_lang if profile else "python"
    parts = []
    for c in code_contents:
        role_hint = ""
        if file_roles and c["file"] in file_roles:
            role_hint = f" (role: {file_roles[c['file']]})"
        parts.append(f"### File: {c['file']}{role_hint}\n```{fence_lang}\n{c['content']}\n```")
    code_text = "\n\n".join(parts)

    if profile:
        framework_line = f"\n\nLanguage: {profile.display_name}\n{profile.framework_hints}"
        lib_examples = ", ".join(profile.library_examples)
        transform_cats = ", ".join(profile.transformation_categories)
    else:
        framework_line = ""
        lib_examples = "sklearn, xgboost, tensorflow, pytorch"
        transform_cats = "scaling, encoding, feature engineering"

    return prompt_loader.template_prompt("code_analysis").format(
        framework_line=framework_line,
        code_text=code_text,
        lib_examples=lib_examples,
        transform_cats=transform_cats,
    )


CODE_ANALYSIS_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "model_classes": {
            "type": "array",
            "items": {"type": "string"},
            "description": "ML model classes/algorithms used",
        },
        "features": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Feature names/columns",
        },
        "target_variable": {
            "type": "string",
            "description": "Target variable name",
        },
        "transformations": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "type": {"type": "string"},
                    "method": {"type": "string"},
                    "columns": {
                        "type": "array",
                        "items": {"type": "string"},
                    },
                },
            },
            "description": "Data transformations applied",
        },
        "ml_task_type": {
            "type": "string",
            "description": "Type of ML task",
        },
        "hyperparameters": {
            "type": "object",
            "description": "Hyperparameter values",
        },
        "data_sources": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Data sources (files, databases)",
        },
        "insights": {
            "type": "string",
            "description": "Additional insights about the codebase",
        },
        "code_evidence": {
            "type": "array",
            "description": "Evidence statements linking claims to code",
            "items": {
                "type": "object",
                "properties": {
                    "statement": {"type": "string"},
                    "file": {"type": "string"},
                    "symbol": {"type": "string"},
                    "snippet": {"type": "string"},
                },
                "required": ["statement", "file"],
            },
        },
    },
    "required": ["model_classes", "features"],
}


def build_section_planning_prompt(
    section_name: str,
    hint: Optional[str],
    model_name: Optional[str],
    model_classes: str,
    ml_task_type: str,
    features_preview: str,
    target_variable: str,
    registered_models: str,
    data_sources: str,
    metrics_info: str = "",
    artifacts_info: str = "",
    governance_evidence: str = "",
) -> str:
    model_line = f"\n## Specific Model: {model_name}" if model_name else ""
    governance_section = f"\n\n{governance_evidence}" if governance_evidence else ""
    return prompt_loader.template_prompt("section_planning").format(
        section_name=section_name,
        user_guidance=hint or "None provided",
        model_line=model_line,
        model_classes=model_classes,
        ml_task_type=ml_task_type,
        features_preview=features_preview,
        target_variable=target_variable,
        registered_models=registered_models,
        metrics_info=metrics_info,
        artifacts_info=artifacts_info,
        data_sources=data_sources,
        governance_section=governance_section,
    )


SECTION_PLANNING_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "section_title": {
            "type": "string",
            "description": "Display title for the section",
        },
        "content_blocks": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "type": {
                        "type": "string",
                        "enum": [
                            "narrative",
                            "table",
                            "chart",
                            "bullet_list",
                            "numbered_list",
                            "image",
                        ],
                    },
                    "purpose": {
                        "type": "string",
                        "description": "What this content block should accomplish",
                    },
                    "data_needed": {
                        "type": "string",
                        "description": "What data/information to include",
                    },
                    "specifics": {
                        "type": "object",
                        "description": "Additional specifications. For charts: 'chart_type'. For images: 'image_name' and 'title' (a descriptive title with model context, e.g., 'Confusion Matrix - RandomForest Credit Risk Classifier')",
                    },
                },
                "required": ["type", "purpose"],
            },
            "minItems": 1,
            "maxItems": 5,
        },
    },
    "required": ["section_title", "content_blocks"],
}


def _governance_instructions(governance_evidence: str) -> str:
    if not governance_evidence:
        return ""
    return f"\n{prompt_loader.governance_text('instructions')}\n"


def narrative_system_prompt(governance_evidence: str = "") -> str:
    system = prompt_loader.system_prompt("narrative")
    if not governance_evidence:
        return system
    note = prompt_loader.governance_text("narrative_note")
    return f"{system} {note}"


def build_narrative_prompt(
    section_name: str,
    purpose: str,
    data_needed: Optional[str],
    model_classes: str,
    ml_task_type: str,
    target_variable: str,
    features: str,
    data_sources: str,
    model_name: Optional[str],
    model_info: str,
    insights: str,
    artifact_data: str = "",
    code_evidence: str = "",
    mlflow_evidence: str = "",
    governance_evidence: str = "",
) -> str:
    data_line = f"\n## Data Needed: {data_needed}" if data_needed else ""
    model_line = f"\n- Specific Model: {model_name}" if model_name else ""
    artifact_section = f"\n\n## Available Artifact Data\n{artifact_data}" if artifact_data else ""
    code_section = f"\n\n{code_evidence}" if code_evidence else ""
    mlflow_section = f"\n\n{mlflow_evidence}" if mlflow_evidence else ""
    governance_section = f"\n\n{governance_evidence}" if governance_evidence else ""
    return prompt_loader.template_prompt("narrative").format(
        section_name=section_name,
        purpose=purpose,
        data_line=data_line,
        model_classes=model_classes,
        ml_task_type=ml_task_type,
        target_variable=target_variable,
        features=features,
        data_sources=data_sources,
        model_line=model_line,
        model_info=model_info,
        insights=insights or "No additional insights available.",
        artifact_section=artifact_section,
        code_section=code_section,
        mlflow_section=mlflow_section,
        governance_section=governance_section,
        governance_instructions=_governance_instructions(governance_evidence),
    )


def build_table_prompt(
    purpose: str,
    data_needed: Optional[str],
    features: str,
    model_classes: str,
    transformations: str,
    hyperparameters: str,
    metrics_info: str = "",
    artifact_data: str = "",
    code_evidence: str = "",
    mlflow_evidence: str = "",
    governance_evidence: str = "",
) -> str:
    artifact_section = f"\n\n## Available Artifact Data\n{artifact_data}" if artifact_data else ""
    code_section = f"\n\n{code_evidence}" if code_evidence else ""
    mlflow_section = f"\n\n{mlflow_evidence}" if mlflow_evidence else ""
    governance_section = f"\n\n{governance_evidence}" if governance_evidence else ""
    return prompt_loader.template_prompt("table").format(
        purpose=purpose,
        data_needed=data_needed or "Relevant data for this section",
        features=features,
        model_classes=model_classes,
        transformations=transformations,
        hyperparameters=hyperparameters,
        metrics_info=metrics_info,
        artifact_section=artifact_section,
        code_section=code_section,
        mlflow_section=mlflow_section,
        governance_section=governance_section,
        governance_instructions=_governance_instructions(governance_evidence),
    )


TABLE_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "caption": {
            "type": "string",
            "description": "Table caption/title",
        },
        "columns": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Column headers",
        },
        "rows": {
            "type": "array",
            "items": {"type": "object"},
            "description": "Row data as objects with column names as keys",
        },
    },
    "required": ["caption", "columns", "rows"],
}


def build_chart_prompt(
    purpose: str,
    data_needed: Optional[str],
    chart_type: str,
    model_classes: str,
    ml_task_type: str,
    metrics_hint: str = "",
    artifact_data: str = "",
    code_evidence: str = "",
    mlflow_evidence: str = "",
    governance_evidence: str = "",
) -> str:
    artifact_section = f"\n\n## Available Artifact Data\n{artifact_data}" if artifact_data else ""
    code_section = f"\n\n{code_evidence}" if code_evidence else ""
    mlflow_section = f"\n\n{mlflow_evidence}" if mlflow_evidence else ""
    governance_section = f"\n\n{governance_evidence}" if governance_evidence else ""
    return prompt_loader.template_prompt("chart").format(
        chart_type=chart_type,
        purpose=purpose,
        data_needed=data_needed or "Relevant data for visualization",
        metrics_hint=metrics_hint,
        artifact_section=artifact_section,
        model_classes=model_classes,
        ml_task_type=ml_task_type,
        code_section=code_section,
        mlflow_section=mlflow_section,
        governance_section=governance_section,
        governance_instructions=_governance_instructions(governance_evidence),
    )


CHART_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "title": {"type": "string", "description": "Chart title"},
        "labels": {
            "type": "array",
            "items": {"type": "string"},
            "description": "X-axis labels or categories",
        },
        "values": {
            "type": "array",
            "items": {"type": "number"},
            "description": "Y-axis values",
        },
        "xlabel": {"type": "string", "description": "X-axis label"},
        "ylabel": {"type": "string", "description": "Y-axis label"},
    },
    "required": ["title", "labels", "values"],
}


def build_list_prompt(
    purpose: str,
    data_needed: Optional[str],
    model_classes: str,
    ml_task_type: str,
    features: str,
    code_evidence: str = "",
    mlflow_evidence: str = "",
    governance_evidence: str = "",
) -> str:
    governance_section = f"\n{governance_evidence}" if governance_evidence else ""
    return prompt_loader.template_prompt("list").format(
        purpose=purpose,
        data_needed=data_needed or "Relevant items for this list",
        model_classes=model_classes,
        ml_task_type=ml_task_type,
        features=features,
        code_evidence=code_evidence,
        mlflow_evidence=mlflow_evidence,
        governance_section=governance_section,
        governance_instructions=_governance_instructions(governance_evidence),
    )


LIST_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "title": {
            "type": "string",
            "description": "A brief, descriptive title for this list section (e.g., 'Key Limitations', 'Recommended Actions')",
        },
        "items": {
            "type": "array",
            "items": {"type": "string"},
            "description": "List items",
            "minItems": 3,
            "maxItems": 15,
        },
    },
    "required": ["items"],
}
