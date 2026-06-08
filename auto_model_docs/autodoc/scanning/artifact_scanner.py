"""MLflow artifact scanner for extracting model metadata."""

import asyncio
import fnmatch
import logging
import os
from typing import Any, Callable, Dict, List, Optional, Set

from autodoc.core.exceptions import ScannerError
from autodoc.core.models import ArtifactContext, ModelInfo

ProgressCallback = Callable[[float], None]

logger = logging.getLogger(__name__)

_DEBUG_PREFIX = "[AUTODOC_MLFLOW_SCAN]"
_LOG_MODEL_TAG_SUBSTR = "mlflow.log-model"


class ArtifactScanner:
    """Scans MLflow for registered models and experiment metadata.

    This scanner queries MLflow's model registry and experiment tracking
    to extract model versions, metrics, parameters, and artifacts.
    """

    def __init__(
        self,
        tracking_uri: Optional[str] = None,
        experiment_name: Optional[str] = None,
        experiment_names: Optional[List[str]] = None,
        model_names: Optional[List[str]] = None,
        latest_only: bool = False,
    ):
        """Initialize the artifact scanner.

        Args:
            tracking_uri: MLflow tracking server URI.
            experiment_name: Specific experiment to query (optional, deprecated).
            experiment_names: List of experiment names to include.
            model_names: List of specific model names to include.
            latest_only: Only include the latest version of each model.
        """
        self.tracking_uri = tracking_uri
        self.experiment_name = experiment_name
        self.experiment_names = experiment_names or []
        self.model_names = model_names or []
        self.latest_only = latest_only
        self._client = None

    def _debug(self, message: str, *args: Any) -> None:
        logger.warning(_DEBUG_PREFIX + " " + message, *args)

    def _get_client(self):
        """Lazily initialize MLflow client."""
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
        """Scan MLflow for registered models and metrics.

        Args:
            on_progress: Optional callback for progress updates (0.0 to 1.0).

        Returns:
            ArtifactContext with model information.
        """
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
            self._debug("MLflow client unavailable (import/init failed)")
            report_progress(1.0)
            return ArtifactContext(
                models=models,
                datasets=datasets,
                project_metadata={"mlflow_available": False},
            )

        try:
            import mlflow

            resolved_uri = mlflow.get_tracking_uri()
            self._debug(
                "scan start tracking_uri=%s resolved_uri=%s model_filters=%s "
                "experiment_filters=%s latest_only=%s",
                self.tracking_uri,
                resolved_uri,
                self.model_names,
                self.experiment_names,
                self.latest_only,
            )

            report_progress(0.05)

            domino_project_id = os.environ.get("DOMINO_PROJECT_ID")
            domino_project_name = os.environ.get("DOMINO_PROJECT_NAME")
            if domino_project_id:
                project_metadata["domino_project_id"] = domino_project_id
                project_metadata["domino_project_name"] = domino_project_name

            self._debug(
                "domino env DOMINO_PROJECT_ID=%s DOMINO_PROJECT_NAME=%s",
                domino_project_id,
                domino_project_name,
            )

            report_progress(0.1)

            self._debug_dump_registry_inventory(client)
            target_experiments = self._get_target_experiments(client, domino_project_id)
            self._debug_dump_experiments(client, domino_project_id, target_experiments)
            self._debug_dump_log_model_tags(client, target_experiments)

            report_progress(0.15)

            models = self._scan_registered_models(
                client, target_experiments, on_progress=on_progress
            )

            report_progress(0.95)

            if self.experiment_name:
                project_metadata.update(self._get_experiment_metadata(client))

            project_metadata["mlflow_available"] = True
            project_metadata["tracking_uri"] = self.tracking_uri or resolved_uri
            project_metadata["models_found"] = len(models)
            project_metadata["filtering_applied"] = {
                "project_filtering": domino_project_id is not None,
                "experiment_filtering": bool(self.experiment_names),
                "model_filtering": bool(self.model_names),
                "latest_only": self.latest_only,
            }
            self._debug(
                "scan complete models_found=%s model_names=%s",
                len(models),
                [m.name for m in models],
            )
            for m in models:
                self._debug(
                    "selected model name=%s version=%s run_id=%s experiment=%s "
                    "metric_keys=%s",
                    m.name,
                    m.version,
                    m.run_id,
                    m.experiment_name,
                    list((m.metrics or {}).keys())[:20],
                )

        except Exception as e:
            logger.error(f"Error scanning MLflow artifacts: {e}")
            self._debug("scan failed with exception: %s", e)
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

    def _debug_dump_registry_inventory(self, client) -> None:
        try:
            registered = list(client.search_registered_models())
            self._debug("registry inventory count=%s", len(registered))
            for rm in registered:
                try:
                    versions = client.search_model_versions(f"name='{rm.name}'")
                except Exception as exc:
                    self._debug(
                        "registry model=%s version_query_error=%s",
                        rm.name,
                        exc,
                    )
                    continue
                version_summaries = []
                for v in versions:
                    version_summaries.append(
                        {
                            "version": getattr(v, "version", None),
                            "run_id": getattr(v, "run_id", None),
                            "stage": getattr(v, "current_stage", None),
                        }
                    )
                self._debug(
                    "registry model=%s versions=%s",
                    rm.name,
                    version_summaries,
                )
        except Exception as exc:
            self._debug("registry inventory dump failed: %s", exc)

    def _debug_dump_experiments(
        self,
        client,
        domino_project_id: Optional[str],
        target_experiments: dict,
    ) -> None:
        try:
            experiments = client.search_experiments()
            self._debug("all experiments count=%s", len(experiments))
            for exp in experiments:
                tags = dict(exp.tags or {})
                domino_tag = tags.get("mlflow.domino.project_id")
                in_target = exp.name in target_experiments
                self._debug(
                    "experiment name=%s id=%s lifecycle=%s in_target=%s "
                    "domino.project_id tag=%s all_tags=%s",
                    exp.name,
                    exp.experiment_id,
                    exp.lifecycle_stage,
                    in_target,
                    domino_tag,
                    tags,
                )
                if domino_project_id and domino_tag != domino_project_id:
                    self._debug(
                        "experiment excluded by domino project filter name=%s "
                        "tag=%s expected=%s",
                        exp.name,
                        domino_tag,
                        domino_project_id,
                    )
            self._debug(
                "target_experiments count=%s names=%s",
                len(target_experiments),
                sorted(target_experiments.keys()),
            )
        except Exception as exc:
            self._debug("experiment dump failed: %s", exc)

    def _debug_dump_log_model_tags(self, client, target_experiments: dict) -> None:
        log_model_runs: List[Dict[str, Any]] = []
        all_run_tag_keys: Set[str] = set()
        try:
            for exp_name, exp_id in target_experiments.items():
                runs = client.search_runs(
                    experiment_ids=[exp_id],
                    max_results=10000,
                )
                self._debug(
                    "experiment runs experiment=%s run_count=%s",
                    exp_name,
                    len(runs),
                )
                for run in runs:
                    tags = dict(run.data.tags or {}) if hasattr(run.data, "tags") else {}
                    for key in tags:
                        all_run_tag_keys.add(key)
                    self._debug(
                        "run tags experiment=%s run_id=%s all_tags=%s",
                        exp_name,
                        run.info.run_id,
                        tags,
                    )
                    log_model_keys = {
                        k: v
                        for k, v in tags.items()
                        if _LOG_MODEL_TAG_SUBSTR in k
                    }
                    if not log_model_keys:
                        continue
                    version_names: List[str] = []
                    try:
                        versions = client.search_model_versions(
                            f"run_id='{run.info.run_id}'"
                        )
                        version_names = [v.name for v in versions]
                    except Exception as exc:
                        version_names = [f"query_error:{exc}"]
                    entry = {
                        "experiment": exp_name,
                        "run_id": run.info.run_id,
                        "log_model_tags": log_model_keys,
                        "all_tag_keys": sorted(tags.keys()),
                        "registered_names_from_run": version_names,
                    }
                    log_model_runs.append(entry)
                    self._debug(
                        "run with log-model tags experiment=%s run_id=%s "
                        "log_model_tags=%s registered_names=%s all_tag_keys=%s",
                        exp_name,
                        run.info.run_id,
                        log_model_keys,
                        version_names,
                        sorted(tags.keys()),
                    )
            self._debug(
                "log-model run summary count=%s unique_run_tag_keys_sample=%s",
                len(log_model_runs),
                sorted(all_run_tag_keys)[:100],
            )
            if self.model_names:
                for pattern in self.model_names:
                    found_in_registry = False
                    registry_run_ids: List[str] = []
                    try:
                        rm = client.get_registered_model(pattern)
                        found_in_registry = rm is not None
                        if found_in_registry:
                            versions = client.search_model_versions(
                                f"name='{pattern}'"
                            )
                            registry_run_ids = [
                                getattr(v, "run_id", None)
                                for v in versions
                                if getattr(v, "run_id", None)
                            ]
                    except Exception:
                        found_in_registry = False
                    found_in_log_model_runs = any(
                        pattern in (e.get("registered_names_from_run") or [])
                        for e in log_model_runs
                    )
                    self._debug(
                        "filter probe pattern=%s in_registry=%s "
                        "in_log_model_run_discovery=%s registry_run_ids=%s",
                        pattern,
                        found_in_registry,
                        found_in_log_model_runs,
                        registry_run_ids,
                    )
                    for run_id in registry_run_ids:
                        try:
                            run = client.get_run(run_id)
                            run_tags = (
                                dict(run.data.tags)
                                if hasattr(run.data, "tags") and run.data.tags
                                else {}
                            )
                            self._debug(
                                "filter probe registry run tags model=%s "
                                "run_id=%s all_tags=%s",
                                pattern,
                                run_id,
                                run_tags,
                            )
                        except Exception as exc:
                            self._debug(
                                "filter probe registry run tags failed "
                                "model=%s run_id=%s error=%s",
                                pattern,
                                run_id,
                                exc,
                            )
        except Exception as exc:
            self._debug("log-model tag dump failed: %s", exc)

    def _get_target_experiments(self, client, domino_project_id: Optional[str]) -> dict:
        """Get target experiments based on filtering criteria.

        Returns:
            Dict mapping experiment name to experiment ID for target experiments.
        """
        target_experiments = {}

        try:
            experiments = client.search_experiments()

            excluded_count = 0
            for exp in experiments:
                if exp.lifecycle_stage == "deleted":
                    excluded_count += 1
                    continue

                if domino_project_id:
                    project_tag = exp.tags.get("mlflow.domino.project_id")
                    if project_tag != domino_project_id:
                        excluded_count += 1
                        continue

                if self.experiment_names:
                    matched = False
                    for pattern in self.experiment_names:
                        if '*' in pattern or '?' in pattern:
                            if fnmatch.fnmatch(exp.name, pattern):
                                matched = True
                                break
                        else:
                            if exp.name == pattern:
                                matched = True
                                break

                    if not matched:
                        excluded_count += 1
                        continue

                elif self.experiment_name:
                    if exp.name != self.experiment_name:
                        excluded_count += 1
                        continue

                target_experiments[exp.name] = exp.experiment_id

            self._debug(
                "get_target_experiments excluded=%s included=%s",
                excluded_count,
                len(target_experiments),
            )

        except Exception as e:
            logger.warning(f"Error getting target experiments: {e}")
            self._debug("get_target_experiments error: %s", e)

        return target_experiments

    def _get_models_from_experiments(
        self,
        client,
        target_experiments: dict,
    ) -> set[str]:
        """Get unique model names from runs in target experiments."""
        model_names = set()

        for exp_name, exp_id in target_experiments.items():
            try:
                runs = client.search_runs(
                    experiment_ids=[exp_id],
                    max_results=10000,
                )

                exp_model_count = 0
                for run in runs:
                    if hasattr(run.data, 'tags') and run.data.tags:
                        for tag_key, tag_value in run.data.tags.items():
                            if _LOG_MODEL_TAG_SUBSTR in tag_key and tag_value:
                                try:
                                    versions = client.search_model_versions(
                                        f"run_id='{run.info.run_id}'"
                                    )
                                    for version in versions:
                                        model_names.add(version.name)
                                        exp_model_count += 1
                                        self._debug(
                                            "experiment discovery hit experiment=%s "
                                            "run_id=%s tag_key=%s tag_value=%s "
                                            "registered_name=%s version=%s",
                                            exp_name,
                                            run.info.run_id,
                                            tag_key,
                                            tag_value,
                                            version.name,
                                            version.version,
                                        )
                                except Exception as e:
                                    self._debug(
                                        "experiment discovery version query failed "
                                        "experiment=%s run_id=%s error=%s",
                                        exp_name,
                                        run.info.run_id,
                                        e,
                                    )
                                    continue

                self._debug(
                    "experiment discovery summary experiment=%s "
                    "discovered_model_links=%s",
                    exp_name,
                    exp_model_count,
                )

            except Exception as e:
                logger.warning(f"  ⚠ Error scanning experiment '{exp_name}': {e}")
                self._debug(
                    "experiment discovery failed experiment=%s error=%s",
                    exp_name,
                    e,
                )
                continue

        self._debug(
            "experiment discovery total unique model names=%s",
            sorted(model_names),
        )
        return model_names

    def _scan_registered_models(
        self,
        client,
        target_experiments: Optional[dict] = None,
        on_progress: Optional[ProgressCallback] = None,
    ) -> list[ModelInfo]:
        """Scan MLflow model registry for registered models."""
        models = []
        model_versions_by_name = {}
        target_experiments = target_experiments or {}

        progress_start = 0.2
        progress_end = 0.95
        progress_range = progress_end - progress_start

        def report_progress(fraction: float) -> None:
            if on_progress:
                scaled_progress = progress_start + (fraction * progress_range)
                on_progress(scaled_progress)

        try:
            scan_path = "unknown"
            matching_models = []

            if target_experiments and self.model_names:
                scan_path = "experiment_discovery_then_registry"
                self._debug(
                    "scan path=%s target_experiment_count=%s model_filters=%s",
                    scan_path,
                    len(target_experiments),
                    self.model_names,
                )

                experiment_models = self._get_models_from_experiments(
                    client, target_experiments
                )

                if not experiment_models:
                    self._debug(
                        "scan path=%s early exit: experiment_models empty",
                        scan_path,
                    )
                    report_progress(1.0)
                    return models

                matching_model_names = set()
                for model_name in experiment_models:
                    for pattern in self.model_names:
                        if '*' in pattern or '?' in pattern:
                            if fnmatch.fnmatch(model_name, pattern):
                                matching_model_names.add(model_name)
                                break
                        else:
                            if model_name == pattern:
                                matching_model_names.add(model_name)
                                break

                self._debug(
                    "scan path=%s experiment_models=%s matching_model_names=%s",
                    scan_path,
                    sorted(experiment_models),
                    sorted(matching_model_names),
                )

                if not matching_model_names:
                    self._debug(
                        "scan path=%s early exit: no name intersection with filters",
                        scan_path,
                    )
                    report_progress(1.0)
                    return models

                for model_name in matching_model_names:
                    try:
                        rm = client.get_registered_model(model_name)
                        matching_models.append(rm)
                        self._debug(
                            "fetched registered model name=%s",
                            model_name,
                        )
                    except Exception as e:
                        logger.warning(
                            f"⚠ Could not fetch registered model '{model_name}': {e}"
                        )
                        self._debug(
                            "get_registered_model failed name=%s error=%s",
                            model_name,
                            e,
                        )
                        continue

            else:
                scan_path = "registry_search"
                self._debug(
                    "scan path=%s reason=target_experiments_empty=%s "
                    "model_filters_empty=%s",
                    scan_path,
                    not bool(target_experiments),
                    not bool(self.model_names),
                )
                registered_models = list(client.search_registered_models())
                self._debug(
                    "registry_search count=%s names=%s",
                    len(registered_models),
                    [rm.name for rm in registered_models],
                )

                for rm in registered_models:
                    if self.model_names:
                        matched = False
                        matched_pattern = None
                        for pattern in self.model_names:
                            if '*' in pattern or '?' in pattern:
                                if fnmatch.fnmatch(rm.name, pattern):
                                    matched = True
                                    matched_pattern = pattern
                                    break
                            else:
                                if rm.name == pattern:
                                    matched = True
                                    matched_pattern = pattern
                                    break
                        if matched:
                            matching_models.append(rm)
                            self._debug(
                                "registry_search matched name=%s pattern=%s",
                                rm.name,
                                matched_pattern,
                            )
                    else:
                        matching_models.append(rm)

            total_models = len(matching_models)
            self._debug(
                "matching registered model objects count=%s names=%s",
                total_models,
                [rm.name for rm in matching_models],
            )
            if total_models == 0:
                self._debug("early exit: matching_models empty")
                report_progress(1.0)
                return models

            for i, rm in enumerate(matching_models):
                report_progress(i / total_models)

                versions = client.search_model_versions(f"name='{rm.name}'")
                self._debug(
                    "processing model=%s version_count=%s",
                    rm.name,
                    len(versions),
                )

                for version in versions:
                    try:
                        run = client.get_run(version.run_id)

                        experiment = client.get_experiment(run.info.experiment_id)
                        if experiment and experiment.lifecycle_stage == "deleted":
                            self._debug(
                                "skip version=%s run_id=%s reason=deleted_experiment "
                                "experiment=%s",
                                version.version,
                                version.run_id,
                                experiment.name,
                            )
                            continue

                        if (
                            self.experiment_names is not None
                            and experiment.name not in target_experiments
                        ):
                            self._debug(
                                "skip version=%s run_id=%s reason=experiment_not_in_"
                                "target_experiments experiment=%s "
                                "experiment_names_filter=%s target_keys=%s",
                                version.version,
                                version.run_id,
                                experiment.name,
                                self.experiment_names,
                                sorted(target_experiments.keys()),
                            )
                            continue

                        artifact_paths = self._list_artifacts(client, version.run_id)

                        if artifact_paths:
                            artifact_data = self._download_and_parse_artifacts(
                                client, version.run_id, artifact_paths
                            )
                        else:
                            artifact_data = {}

                        model_info = ModelInfo(
                            name=rm.name,
                            version=version.version,
                            stage=version.current_stage,
                            run_id=version.run_id,
                            experiment_id=run.info.experiment_id,
                            experiment_name=experiment.name if experiment else None,
                            metrics=dict(run.data.metrics),
                            params=dict(run.data.params),
                            tags=dict(run.data.tags) if hasattr(run.data, "tags") else {},
                            artifacts=artifact_paths,
                            artifact_data=artifact_data,
                        )

                        self._debug(
                            "accepted version=%s model=%s run_id=%s experiment=%s "
                            "metrics=%s params=%s run_tag_keys=%s",
                            version.version,
                            rm.name,
                            version.run_id,
                            experiment.name if experiment else None,
                            list(model_info.metrics.keys()),
                            list(model_info.params.keys())[:20],
                            sorted(model_info.tags.keys())[:30],
                        )

                        if self.latest_only:
                            if rm.name not in model_versions_by_name:
                                model_versions_by_name[rm.name] = []
                            model_versions_by_name[rm.name].append(model_info)
                        else:
                            models.append(model_info)

                    except Exception as e:
                        self._debug(
                            "skip version=%s model=%s run_id=%s reason=exception %s",
                            getattr(version, "version", "?"),
                            rm.name,
                            getattr(version, "run_id", "?"),
                            e,
                        )

            if self.latest_only:
                for model_name, model_list in model_versions_by_name.items():
                    latest_model = max(model_list, key=lambda m: int(m.version))
                    models.append(latest_model)
                    self._debug(
                        "latest_only selected model=%s version=%s run_id=%s",
                        model_name,
                        latest_model.version,
                        latest_model.run_id,
                    )
                if not model_versions_by_name:
                    self._debug(
                        "latest_only produced no models; all versions were skipped"
                    )

            report_progress(1.0)

        except Exception as e:
            logger.warning(f"Error scanning registered models: {e}")
            self._debug("scan_registered_models exception: %s", e)

        return models

    def _list_artifacts(self, client, run_id: str, path: str = "") -> list[str]:
        """Recursively list all artifacts for a run."""
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
            logger.warning(f"        Error listing artifacts for run {run_id}: {e}")
        return artifact_paths

    def _download_and_parse_artifacts(
        self, client, run_id: str, artifact_paths: list[str]
    ) -> dict[str, any]:
        """Download and parse CSV/text/image artifacts."""
        import base64
        import tempfile

        import pandas as pd

        artifact_data = {}

        for path in artifact_paths:
            try:
                if path.endswith('.csv'):
                    local_path = client.download_artifacts(
                        run_id, path, tempfile.gettempdir()
                    )
                    df = pd.read_csv(local_path)
                    artifact_data[path] = df.to_dict('records')
                    os.remove(local_path)
                elif path.endswith('.txt'):
                    local_path = client.download_artifacts(
                        run_id, path, tempfile.gettempdir()
                    )
                    with open(local_path, 'r') as f:
                        content = f.read()
                        artifact_data[path] = content
                    os.remove(local_path)
                elif path.endswith(('.png', '.jpg', '.jpeg')):
                    local_path = client.download_artifacts(
                        run_id, path, tempfile.gettempdir()
                    )
                    with open(local_path, 'rb') as f:
                        image_bytes = f.read()
                    artifact_data[path] = {
                        "type": "image",
                        "format": path.split('.')[-1].lower(),
                        "data": base64.b64encode(image_bytes).decode('utf-8'),
                    }
                    os.remove(local_path)
            except Exception as e:
                logger.warning(f"        ✗ Failed to download/parse {path}: {str(e)}")
                continue

        return artifact_data

    def _get_experiment_metadata(self, client) -> dict:
        """Get experiment metadata."""
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
