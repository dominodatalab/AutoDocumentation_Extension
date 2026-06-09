"""Tests for MLflow artifact scanner."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from autodoc.core.exceptions import ScannerError
from autodoc.scanning.artifact_scanner import (
    ArtifactScanner,
    _name_filter_for_pattern,
    _pattern_to_ilike,
    _project_tag_filter,
)


def _run_info(run_id: str, experiment_id: str = "exp-1"):
    return SimpleNamespace(run_id=run_id, experiment_id=experiment_id)


def _experiment(
    name: str,
    experiment_id: str,
    *,
    lifecycle_stage: str = "active",
    tags: dict | None = None,
):
    return SimpleNamespace(
        name=name,
        experiment_id=experiment_id,
        lifecycle_stage=lifecycle_stage,
        tags=tags or {},
    )


def _registered_model(name: str):
    return SimpleNamespace(name=name, tags={})


def _model_version(name: str, version: str, run_id: str):
    return SimpleNamespace(
        name=name,
        version=version,
        run_id=run_id,
        current_stage="None",
    )


def test_project_tag_filter():
    assert _project_tag_filter("proj-123") == (
        "tags.`mlflow.domino.project_id` = 'proj-123'"
    )


def test_pattern_to_ilike():
    assert _pattern_to_ilike("*mixed*") == "%mixed%"
    assert _pattern_to_ilike("churn*") == "churn%"
    assert _pattern_to_ilike("a?c") == "a_c"


def test_name_filter_literal():
    assert _name_filter_for_pattern("my-model") == "name = 'my-model'"


def test_name_filter_glob():
    assert _name_filter_for_pattern("*mixed*") == "name ILIKE '%mixed%'"


@pytest.mark.asyncio
async def test_scan_requires_domino_project_id():
    scanner = ArtifactScanner()
    with patch.dict("os.environ", {}, clear=True):
        with patch.object(scanner, "_get_client", return_value=MagicMock()):
            with pytest.raises(ScannerError, match="DOMINO_PROJECT_ID"):
                await scanner.scan()


@pytest.mark.asyncio
async def test_scan_finds_model_with_literal_filter():
    client = MagicMock()
    client.search_experiments.return_value = [
        _experiment("mlflow3-models", "exp-1", tags={"mlflow.domino.project_id": "proj-123"}),
    ]
    client.search_registered_models.return_value = [
        _registered_model("target-model"),
    ]
    client.search_model_versions.return_value = [
        _model_version("target-model", "1", "run-1"),
    ]
    client.get_run.return_value = SimpleNamespace(
        info=_run_info("run-1", "exp-1"),
        data=SimpleNamespace(metrics={"acc": 0.9}, params={}, tags={}),
    )
    client.get_experiment.return_value = _experiment("mlflow3-models", "exp-1")
    client.list_artifacts.return_value = []

    scanner = ArtifactScanner(model_names=["target-model"], latest_only=True)

    with patch.dict("os.environ", {"DOMINO_PROJECT_ID": "proj-123"}, clear=False):
        with patch.object(scanner, "_get_client", return_value=client):
            ctx = await scanner.scan()

    assert len(ctx.models) == 1
    assert ctx.models[0].name == "target-model"
    filter_string = client.search_registered_models.call_args.kwargs["filter_string"]
    assert "tags.`mlflow.domino.project_id` = 'proj-123'" in filter_string
    assert "name = 'target-model'" in filter_string
    client.search_model_versions.assert_called_once()
    assert client.search_model_versions.call_args.kwargs["max_results"] == 1


@pytest.mark.asyncio
async def test_scan_glob_model_filter_uses_ilike():
    client = MagicMock()
    client.search_experiments.return_value = [
        _experiment("mlflow3-models", "exp-1", tags={"mlflow.domino.project_id": "proj-123"}),
    ]
    client.search_registered_models.return_value = [
        _registered_model("mlflow3-mixed-logged-and-registered1"),
    ]
    client.search_model_versions.return_value = [
        _model_version("mlflow3-mixed-logged-and-registered1", "1", "run-1"),
    ]
    client.get_run.return_value = SimpleNamespace(
        info=_run_info("run-1", "exp-1"),
        data=SimpleNamespace(metrics={}, params={}, tags={}),
    )
    client.get_experiment.return_value = _experiment("mlflow3-models", "exp-1")
    client.list_artifacts.return_value = []

    scanner = ArtifactScanner(model_names=["*mixed*"], latest_only=True)

    with patch.dict("os.environ", {"DOMINO_PROJECT_ID": "proj-123"}, clear=False):
        with patch.object(scanner, "_get_client", return_value=client):
            ctx = await scanner.scan()

    assert len(ctx.models) == 1
    filter_string = client.search_registered_models.call_args.kwargs["filter_string"]
    assert "name ILIKE '%mixed%'" in filter_string


@pytest.mark.asyncio
async def test_scan_without_model_filter_queries_project_only():
    client = MagicMock()
    client.search_experiments.return_value = [
        _experiment("mlflow3-models", "exp-1", tags={"mlflow.domino.project_id": "proj-123"}),
        _experiment("other-exp", "exp-2", tags={"mlflow.domino.project_id": "proj-123"}),
    ]
    client.search_registered_models.return_value = [
        _registered_model("model-a"),
        _registered_model("model-b"),
    ]
    client.search_model_versions.side_effect = [
        [_model_version("model-a", "1", "run-a")],
        [_model_version("model-b", "1", "run-b")],
    ]
    client.get_run.side_effect = [
        SimpleNamespace(
            info=_run_info("run-a", "exp-1"),
            data=SimpleNamespace(metrics={}, params={}, tags={}),
        ),
        SimpleNamespace(
            info=_run_info("run-b", "exp-2"),
            data=SimpleNamespace(metrics={}, params={}, tags={}),
        ),
    ]
    client.get_experiment.side_effect = [
        _experiment("mlflow3-models", "exp-1"),
        _experiment("other-exp", "exp-2"),
    ]
    client.list_artifacts.return_value = []

    scanner = ArtifactScanner(latest_only=False)

    with patch.dict("os.environ", {"DOMINO_PROJECT_ID": "proj-123"}, clear=False):
        with patch.object(scanner, "_get_client", return_value=client):
            ctx = await scanner.scan()

    assert len(ctx.models) == 2
    filter_string = client.search_registered_models.call_args.kwargs["filter_string"]
    assert filter_string == "tags.`mlflow.domino.project_id` = 'proj-123'"
    assert "name ILIKE" not in filter_string
    assert "name =" not in filter_string


@pytest.mark.asyncio
async def test_scan_experiment_filter_skips_wrong_experiment():
    client = MagicMock()
    client.search_experiments.return_value = [
        _experiment("mlflow3-models", "exp-1", tags={"mlflow.domino.project_id": "proj-123"}),
    ]
    client.search_registered_models.return_value = [
        _registered_model("target-model"),
    ]
    client.search_model_versions.return_value = [
        _model_version("target-model", "1", "run-1"),
    ]
    client.get_run.return_value = SimpleNamespace(
        info=_run_info("run-1", "exp-9"),
        data=SimpleNamespace(metrics={}, params={}, tags={}),
    )
    client.get_experiment.return_value = _experiment("other-exp", "exp-9")
    client.list_artifacts.return_value = []

    scanner = ArtifactScanner(
        model_names=["target-model"],
        experiment_names=["mlflow3-models"],
        latest_only=True,
    )

    with patch.dict("os.environ", {"DOMINO_PROJECT_ID": "proj-123"}, clear=False):
        with patch.object(scanner, "_get_client", return_value=client):
            ctx = await scanner.scan()

    assert ctx.models == []
    exp_filter = client.search_experiments.call_args.kwargs["filter_string"]
    assert "name = 'mlflow3-models'" in exp_filter


@pytest.mark.asyncio
async def test_scan_multiple_model_patterns_one_query_each():
    client = MagicMock()
    client.search_experiments.return_value = []
    client.search_registered_models.side_effect = [
        [_registered_model("model-a")],
        [_registered_model("model-b")],
    ]
    client.search_model_versions.return_value = []
    client.list_artifacts.return_value = []

    scanner = ArtifactScanner(model_names=["model-a", "model-b"])

    with patch.dict("os.environ", {"DOMINO_PROJECT_ID": "proj-123"}, clear=False):
        with patch.object(scanner, "_get_client", return_value=client):
            await scanner.scan()

    assert client.search_registered_models.call_count == 2
