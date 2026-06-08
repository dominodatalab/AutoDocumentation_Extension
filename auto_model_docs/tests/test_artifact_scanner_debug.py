"""Tests for MLflow artifact scanner debug logging."""

from __future__ import annotations

import logging
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from autodoc.scanning.artifact_scanner import ArtifactScanner


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


def _run(run_id: str, tags: dict | None = None):
    return SimpleNamespace(
        info=_run_info(run_id),
        data=SimpleNamespace(
            metrics={},
            params={},
            tags=tags or {},
        ),
    )


def _registered_model(name: str):
    return SimpleNamespace(name=name)


def _model_version(name: str, version: str, run_id: str):
    return SimpleNamespace(
        name=name,
        version=version,
        run_id=run_id,
        current_stage="None",
    )


@pytest.mark.asyncio
async def test_scan_logs_registry_and_unbound_path(caplog):
    caplog.set_level(logging.WARNING)

    client = MagicMock()
    client.search_registered_models.return_value = [
        _registered_model("mlflow3-mixed-logged-and-registered1"),
    ]
    client.search_experiments.return_value = [
        _experiment(
            "proj-exp",
            "exp-1",
            tags={"mlflow.domino.project_id": "proj-123"},
        ),
    ]
    client.search_runs.return_value = [
        _run(
            "run-1",
            tags={"mlflow.log-model.history": "abc"},
        ),
    ]
    client.search_model_versions.return_value = [
        _model_version("mlflow3-mixed-logged-and-registered1", "1", "run-1"),
    ]
    client.get_registered_model.return_value = _registered_model(
        "mlflow3-mixed-logged-and-registered1"
    )
    client.get_run.return_value = _run("run-1")
    client.get_experiment.return_value = _experiment("other-exp", "exp-9")
    client.list_artifacts.return_value = []

    scanner = ArtifactScanner(
        model_names=["mlflow3-mixed-logged-and-registered1"],
        latest_only=True,
    )

    with patch.dict("os.environ", {"DOMINO_PROJECT_ID": "proj-123"}, clear=False):
        with patch.object(scanner, "_get_client", return_value=client):
            ctx = await scanner.scan()

    assert ctx.models == []
    messages = "\n".join(r.message for r in caplog.records)
    assert "[AUTODOC_MLFLOW_SCAN]" in messages
    assert "registry inventory" in messages
    assert "experiment discovery" in messages
    assert "skip version" in messages
    assert "experiment_not_in_target_experiments" in messages
    assert "scan complete models_found=0" in messages


@pytest.mark.asyncio
async def test_scan_logs_bound_model_when_version_accepted(caplog):
    caplog.set_level(logging.WARNING)

    client = MagicMock()
    client.search_registered_models.return_value = [
        _registered_model("target-model"),
    ]
    client.search_experiments.return_value = [
        _experiment(
            "proj-exp",
            "exp-1",
            tags={"mlflow.domino.project_id": "proj-123"},
        ),
    ]
    client.search_runs.return_value = [
        _run("run-1", tags={"mlflow.log-model.history": "abc"}),
    ]
    client.search_model_versions.return_value = [
        _model_version("target-model", "1", "run-1"),
    ]
    client.get_registered_model.return_value = _registered_model("target-model")
    client.get_run.return_value = SimpleNamespace(
        info=_run_info("run-1", "exp-1"),
        data=SimpleNamespace(metrics={"acc": 0.9}, params={"p": "1"}, tags={}),
    )
    client.get_experiment.return_value = _experiment(
        "proj-exp",
        "exp-1",
        tags={"mlflow.domino.project_id": "proj-123"},
    )
    client.list_artifacts.return_value = []

    scanner = ArtifactScanner(model_names=["target-model"], latest_only=True)

    with patch.dict("os.environ", {"DOMINO_PROJECT_ID": "proj-123"}, clear=False):
        with patch.object(scanner, "_get_client", return_value=client):
            ctx = await scanner.scan()

    assert len(ctx.models) == 1
    assert ctx.models[0].name == "target-model"
    messages = "\n".join(r.message for r in caplog.records)
    assert "accepted version" in messages
    assert "scan complete models_found=1" in messages
