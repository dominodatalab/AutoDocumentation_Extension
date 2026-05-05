"""MLflow artifact scanner for extracting model metadata."""

import asyncio
import logging
import os
from typing import Any, Callable, List, Optional

from autodoc.core.exceptions import ScannerError
from autodoc.core.models import ArtifactContext, ModelInfo

ProgressCallback = Callable[[float], None]

logger = logging.getLogger(__name__)

_DOMINO_PROJECT_TAG = "mlflow.domino.project_id"


def _escape_mlflow_string(value: str) -> str:
    return value.replace("'", "''")


def _require_domino_project_id() -> str:
    project_id = (os.environ.get("DOMINO_PROJECT_ID") or "").strip()
    if not project_id:
        raise ScannerError("DOMINO_PROJECT_ID is required for MLflow scanning")
    return project_id


def _project_tag_filter(project_id: str) -> str:
    escaped = _escape_mlflow_string(project_id)
    return f"tags.`{_DOMINO_PROJECT_TAG}` = '{escaped}'"


def _pattern_has_wildcards(pattern: str) -> bool:
    return "*" in pattern or "?" in pattern


def _pattern_to_ilike(pattern: str) -> str:
    return pattern.replace("*", "%").replace("?", "_")


def _name_filter_for_pattern(pattern: str) -> str:
    if _pattern_has_wildcards(pattern):
        ilike = _pattern_to_ilike(pattern)
        return f"name ILIKE '{_escape_mlflow_string(ilike)}'"
    return f"name = '{_escape_mlflow_string(pattern)}'"


class ArtifactScanner:
    """Scans MLflow for registered models and experiment metadata."""

    def __init__(
        self,
        tracking_uri: Optional[str] = None,
        experiment_name: Optional[str] = None,
        experiment_names: Optional[List[str]] = None,
        model_names: Optional[List[str]] = None,
        latest_only: bool = False,
    ):
        self.tracking_uri = tracking_uri
        self.experiment_name = experiment_name
        self.experiment_names = experiment_names or []
        self.model_names = model_names or []
        self.latest_only = latest_only
        self._client = None

    def _get_client(self):
        if self._client is None:
            try:
                import mlflow

                if self.tracking_uri:
                    mlflow.set_tracking_uri(self.tracking_uri)
                self._client = mlflow.tracking.MlflowClient()
            except ImportError:
                return None
            except Exception:
                return None
        return self._client

    async def scan(
        self, on_progress: Optional[ProgressCallback] = None
    ) -> ArtifactContext:
        return await asyncio.to_thread(self._scan_sync, on_progress)

    def _scan_sync(
        self, on_progress: Optional[ProgressCallback] = None
    ) -> ArtifactContext:
        models = []
        datasets = []
        project_metadata = {}

        def report_progress(progress: float) -> None:
            if on_progress:
                on_progress(progress)

        report_progress(0.0)

        client = self._get_client()
        if client is None:
            report_progress(1.0)
            return ArtifactContext(
                models=models,
                datasets=datasets,
                project_metadata={"mlflow_available": False},
            )

        try:
            import mlflow

            domino_project_id = _require_domino_project_id()
            domino_project_name = os.environ.get("DOMINO_PROJECT_NAME")
            project_metadata["domino_project_id"] = domino_project_id
            project_metadata["domino_project_name"] = domino_project_name

            report_progress(0.1)
            target_experiments = self._get_target_experiments(client, domino_project_id)

            report_progress(0.15)
            models = self._scan_registered_models(
                client,
                domino_project_id,
                target_experiments,
                on_progress=on_progress,
            )

            report_progress(0.95)

            if self.experiment_name:
                project_metadata.update(self._get_experiment_metadata(client))

            resolved_uri = mlflow.get_tracking_uri()
            project_metadata["mlflow_available"] = True
            project_metadata["tracking_uri"] = self.tracking_uri or resolved_uri
            project_metadata["models_found"] = len(models)
            project_metadata["filtering_applied"] = {
                "project_filtering": True,
                "experiment_filtering": bool(self.experiment_names),
                "model_filtering": bool(self.model_names),
                "latest_only": self.latest_only,
            }
            logger.info(
                "MLflow scan complete models_found=%s names=%s",
                len(models),
                [m.name for m in models],
            )

        except ScannerError:
            raise
        except Exception as e:
            logger.error(f"Error scanning MLflow artifacts: {e}")
            project_metadata["mlflow_error"] = str(e)
            project_metadata["mlflow_available"] = False

        report_progress(1.0)

        mlflow_metrics: List[dict[str, str]] = []
        mlflow_params: List[dict[str, str]] = []
        mlflow_tags: List[dict[str, str]] = []
        mlflow_artifacts: List[dict[str, str]] = []

        for model in models:
            for key in model.metrics.keys():
                mlflow_metrics.append(
                    {
                        "run_id": model.run_id,
                        "experiment_id": model.experiment_id or "",
                        "key": key,
                    }
                )
            for key in model.params.keys():
                mlflow_params.append(
                    {
                        "run_id": model.run_id,
                        "experiment_id": model.experiment_id or "",
                        "key": key,
                    }
                )
            for key in model.tags.keys():
                mlflow_tags.append(
                    {
                        "run_id": model.run_id,
                        "experiment_id": model.experiment_id or "",
                        "key": key,
                    }
                )
            for path in model.artifacts:
                mlflow_artifacts.append(
                    {
                        "run_id": model.run_id,
                        "experiment_id": model.experiment_id or "",
                        "path": path,
                    }
                )

        return ArtifactContext(
            models=models,
            datasets=datasets,
            project_metadata=project_metadata,
            mlflow_metrics=mlflow_metrics,
            mlflow_params=mlflow_params,
            mlflow_tags=mlflow_tags,
            mlflow_artifacts=mlflow_artifacts,
        )

    def _get_target_experiments(self, client, project_id: str) -> dict:
        target_experiments: dict[str, str] = {}
        project_filter = _project_tag_filter(project_id)

        patterns: List[str] = []
        if self.experiment_names:
            patterns = list(self.experiment_names)
        elif self.experiment_name:
            patterns = [self.experiment_name]

        try:
            if not patterns:
                experiments = client.search_experiments(filter_string=project_filter)
            else:
                experiments = []
                for pattern in patterns:
                    filter_string = f"{project_filter} AND {_name_filter_for_pattern(pattern)}"
                    experiments.extend(
                        client.search_experiments(filter_string=filter_string)
                    )

            for exp in experiments:
                if exp.lifecycle_stage == "deleted":
                    continue
                target_experiments[exp.name] = exp.experiment_id

        except Exception as e:
            logger.warning(f"Error getting target experiments: {e}")

        return target_experiments

    def _resolve_registered_models(self, client, project_id: str) -> list:
        project_filter = _project_tag_filter(project_id)
        by_name: dict[str, Any] = {}

        try:
            if not self.model_names:
                for rm in client.search_registered_models(filter_string=project_filter):
                    by_name[rm.name] = rm
            else:
                for pattern in self.model_names:
                    filter_string = (
                        f"{project_filter} AND {_name_filter_for_pattern(pattern)}"
                    )
                    for rm in client.search_registered_models(filter_string=filter_string):
                        by_name[rm.name] = rm
        except Exception as e:
            logger.warning(f"Error resolving registered models: {e}")

        return list(by_name.values())

    def _scan_registered_models(
        self,
        client,
        project_id: str,
        target_experiments: dict,
        on_progress: Optional[ProgressCallback] = None,
    ) -> list[ModelInfo]:
        models: list[ModelInfo] = []
        experiment_filter_active = bool(self.experiment_names)

        progress_start = 0.2
        progress_end = 0.95
        progress_range = progress_end - progress_start

        def report_progress(fraction: float) -> None:
            if on_progress:
                scaled_progress = progress_start + (fraction * progress_range)
                on_progress(scaled_progress)

        try:
            registered_models = self._resolve_registered_models(client, project_id)
            total_models = len(registered_models)
            if total_models == 0:
                report_progress(1.0)
                return models

            for i, rm in enumerate(registered_models):
                report_progress(i / total_models)

                version_kwargs: dict[str, Any] = {
                    "filter_string": f"name = '{_escape_mlflow_string(rm.name)}'",
                }
                if self.latest_only:
                    version_kwargs["order_by"] = ["version_number DESC"]
                    version_kwargs["max_results"] = 1

                versions = list(client.search_model_versions(**version_kwargs))

                for version in versions:
                    try:
                        run = client.get_run(version.run_id)
                        experiment = client.get_experiment(run.info.experiment_id)
                        if experiment and experiment.lifecycle_stage == "deleted":
                            continue

                        if (
                            experiment_filter_active
                            and experiment.name not in target_experiments
                        ):
                            continue

                        artifact_paths = self._list_artifacts(client, version.run_id)
                        if artifact_paths:
                            artifact_data = self._download_and_parse_artifacts(
                                client, version.run_id, artifact_paths
                            )
                        else:
                            artifact_data = {}

                        models.append(
                            ModelInfo(
                                name=rm.name,
                                version=version.version,
                                stage=version.current_stage,
                                run_id=version.run_id,
                                experiment_id=run.info.experiment_id,
                                experiment_name=experiment.name if experiment else None,
                                metrics=dict(run.data.metrics),
                                params=dict(run.data.params),
                                tags=dict(run.data.tags)
                                if hasattr(run.data, "tags")
                                else {},
                                artifacts=artifact_paths,
                                artifact_data=artifact_data,
                            )
                        )

                    except Exception as e:
                        logger.warning(
                            "Skipping model version %s/%s: %s",
                            rm.name,
                            getattr(version, "version", "?"),
                            e,
                        )

            report_progress(1.0)

        except Exception as e:
            logger.warning(f"Error scanning registered models: {e}")

        return models

    def _list_artifacts(self, client, run_id: str, path: str = "") -> list[str]:
        artifact_paths = []
        try:
            artifacts = client.list_artifacts(run_id, path)
            for artifact in artifacts:
                if artifact.is_dir:
                    nested = self._list_artifacts(client, run_id, artifact.path)
                    artifact_paths.extend(nested)
                else:
                    artifact_paths.append(artifact.path)
        except Exception as e:
            logger.warning(f"Error listing artifacts for run {run_id}: {e}")
        return artifact_paths

    def _download_and_parse_artifacts(
        self, client, run_id: str, artifact_paths: list[str]
    ) -> dict[str, any]:
        import base64
        import tempfile

        import pandas as pd

        artifact_data = {}

        for path in artifact_paths:
            try:
                if path.endswith(".csv"):
                    local_path = client.download_artifacts(
                        run_id, path, tempfile.gettempdir()
                    )
                    df = pd.read_csv(local_path)
                    artifact_data[path] = df.to_dict("records")
                    os.remove(local_path)
                elif path.endswith(".txt"):
                    local_path = client.download_artifacts(
                        run_id, path, tempfile.gettempdir()
                    )
                    with open(local_path, "r") as f:
                        content = f.read()
                        artifact_data[path] = content
                    os.remove(local_path)
                elif path.endswith((".png", ".jpg", ".jpeg")):
                    local_path = client.download_artifacts(
                        run_id, path, tempfile.gettempdir()
                    )
                    with open(local_path, "rb") as f:
                        image_bytes = f.read()
                    artifact_data[path] = {
                        "type": "image",
                        "format": path.split(".")[-1].lower(),
                        "data": base64.b64encode(image_bytes).decode("utf-8"),
                    }
                    os.remove(local_path)
            except Exception as e:
                logger.warning(f"Failed to download/parse {path}: {str(e)}")
                continue

        return artifact_data

    def _get_experiment_metadata(self, client) -> dict:
        metadata = {}

        try:
            experiment = client.get_experiment_by_name(self.experiment_name)
            if experiment:
                if experiment.lifecycle_stage == "deleted":
                    metadata["experiment_skipped"] = True
                    metadata["skip_reason"] = (
                        f"Experiment '{self.experiment_name}' is deleted"
                    )
                    return metadata

                metadata["experiment_id"] = experiment.experiment_id
                metadata["experiment_name"] = experiment.name
                metadata["artifact_location"] = experiment.artifact_location
                metadata["lifecycle_stage"] = experiment.lifecycle_stage

                runs = client.search_runs(
                    experiment_ids=[experiment.experiment_id],
                    max_results=1,
                )
                metadata["has_runs"] = len(runs) > 0

        except Exception:
            pass

        return metadata
