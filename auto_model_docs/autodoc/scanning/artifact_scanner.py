"""MLflow artifact scanner for extracting model metadata."""

import asyncio
import fnmatch
import logging
import os
from typing import Callable, List, Optional, Set

from autodoc.core.exceptions import ScannerError
from autodoc.core.models import ArtifactContext, ModelInfo

# Type alias for progress callback
ProgressCallback = Callable[[float], None]

logger = logging.getLogger(__name__)


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
        self.experiment_name = experiment_name  # Keep for backward compatibility
        self.experiment_names = experiment_names or []
        self.model_names = model_names or []
        self.latest_only = latest_only
        self._client = None

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
            """Report progress if callback is provided."""
            if on_progress:
                on_progress(progress)

        report_progress(0.0)

        client = self._get_client()
        if client is None:
            # MLflow not available, return empty context
            report_progress(1.0)
            return ArtifactContext(
                models=models,
                datasets=datasets,
                project_metadata={"mlflow_available": False},
            )


        try:
            report_progress(0.05)

            domino_project_id = os.environ.get("DOMINO_PROJECT_ID")
            if domino_project_id:
                project_metadata["domino_project_id"] = domino_project_id
                project_metadata["domino_project_name"] = os.environ.get("DOMINO_PROJECT_NAME")

            report_progress(0.1)

            # Get target experiments based on filtering
            target_experiments = self._get_target_experiments(client, domino_project_id)

            report_progress(0.15)

            # Get registered models with filtering (progress 0.2 to 0.95)
            models = self._scan_registered_models(
                client, target_experiments, on_progress=on_progress
            )

            report_progress(0.95)

            # Get experiment info if specified (backward compatibility)
            if self.experiment_name:
                project_metadata.update(self._get_experiment_metadata(client))

            project_metadata["mlflow_available"] = True
            project_metadata["tracking_uri"] = self.tracking_uri
            project_metadata["models_found"] = len(models)
            project_metadata["filtering_applied"] = {
                "project_filtering": domino_project_id is not None,
                "experiment_filtering": bool(self.experiment_names),
                "model_filtering": bool(self.model_names),
                "latest_only": self.latest_only,
            }

        except Exception as e:
            logger.error(f"Error scanning MLflow artifacts: {e}")
            # Log but don't fail - MLflow might not be configured
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

    def _get_target_experiments(self, client, domino_project_id: Optional[str]) -> dict:
        """Get target experiments based on filtering criteria.
        
        Returns:
            Dict mapping experiment name to experiment ID for target experiments.
        """
        target_experiments = {}
        
        try:
            # Get all experiments
            experiments = client.search_experiments()
            
            excluded_count = 0
            for exp in experiments:
                # Skip deleted experiments
                if exp.lifecycle_stage == "deleted":
                    excluded_count += 1
                    continue
                    
                if domino_project_id:
                    project_tag = exp.tags.get("mlflow.domino.project_id")
                    if project_tag != domino_project_id:
                        excluded_count += 1
                        continue
                
                # Apply experiment name filtering
                if self.experiment_names:
                    # Check if any pattern matches this experiment
                    matched = False
                    matching_pattern = None
                    for pattern in self.experiment_names:
                        # Use wildcard matching if pattern contains wildcards
                        if '*' in pattern or '?' in pattern:
                            if fnmatch.fnmatch(exp.name, pattern):
                                matched = True
                                matching_pattern = pattern
                                break
                        else:
                            # Exact match for non-wildcard patterns
                            if exp.name == pattern:
                                matched = True
                                matching_pattern = pattern
                                break
                    
                    if not matched:
                        excluded_count += 1
                        continue

                elif self.experiment_name:  # Backward compatibility
                    if exp.name != self.experiment_name:
                        excluded_count += 1
                        continue

                target_experiments[exp.name] = exp.experiment_id

        except Exception as e:
            logger.warning(f"Error getting target experiments: {e}")

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
                
                # Get all runs from this experiment
                runs = client.search_runs(
                    experiment_ids=[exp_id],
                    max_results=10000  # Large number to get all runs
                )
                
                exp_model_count = 0
                for run in runs:
                    # Look for model registry references in run tags
                    if hasattr(run.data, 'tags') and run.data.tags:
                        # Check for MLflow model registry tags
                        for tag_key, tag_value in run.data.tags.items():
                            if 'mlflow.log-model' in tag_key and tag_value:
                                # This run logged a model
                                # Try to find registered model versions that reference this run
                                try:
                                    # Search for model versions with this run_id
                                    versions = client.search_model_versions(f"run_id='{run.info.run_id}'")
                                    for version in versions:
                                        model_names.add(version.name)
                                        exp_model_count += 1
                                except Exception as e:
                                    logger.debug(f"    Error searching model versions for run {run.info.run_id}: {e}")
                                    continue

            except Exception as e:
                logger.warning(f"  ⚠ Error scanning experiment '{exp_name}': {e}")
                continue

        return model_names

    def _scan_registered_models(
        self,
        client,
        target_experiments: Optional[dict] = None,
        on_progress: Optional[ProgressCallback] = None,
    ) -> list[ModelInfo]:
        """Scan MLflow model registry for registered models."""
        models = []
        model_versions_by_name = {}  # For latest_only filtering

        # Progress range for model scanning: 0.2 to 0.95
        progress_start = 0.2
        progress_end = 0.95
        progress_range = progress_end - progress_start

        def report_progress(fraction: float) -> None:
            """Report progress scaled to the model scanning range."""
            if on_progress:
                scaled_progress = progress_start + (fraction * progress_range)
                on_progress(scaled_progress)

        try:
            # Optimization: Use experiment-based pre-filtering when both experiment and model filters are specified
            if target_experiments and self.model_names:
                
                # Get models from target experiments first
                experiment_models = self._get_models_from_experiments(client, target_experiments)
                
                if not experiment_models:
                    report_progress(1.0)
                    return models
                
                # Filter experiment models by model name patterns
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
                
                
                # Get registered model objects for the matching names
                matching_models = []
                for model_name in matching_model_names:
                    try:
                        rm = client.get_registered_model(model_name)
                        matching_models.append(rm)
                    except Exception as e:
                        logger.warning(f"⚠ Could not fetch registered model '{model_name}': {e}")
                        continue
                        
            else:
                # Original approach: get all registered models first, then filter
                registered_models = list(client.search_registered_models())

                # Filter to matching models
                matching_models = []
                for rm in registered_models:
                    if self.model_names:
                        matched = False
                        for pattern in self.model_names:
                            if '*' in pattern or '?' in pattern:
                                if fnmatch.fnmatch(rm.name, pattern):
                                    matched = True
                                    break
                            else:
                                if rm.name == pattern:
                                    matched = True
                                    break
                        if matched:
                            matching_models.append(rm)
                    else:
                        matching_models.append(rm)

            total_models = len(matching_models)
            if total_models == 0:
                report_progress(1.0)
                return models

            # Process each model
            for i, rm in enumerate(matching_models):
                # Report progress based on models processed
                report_progress(i / total_models)

                # Get all versions of this model
                versions = client.search_model_versions(f"name='{rm.name}'")

                for version in versions:
                    try:
                        # Get the run associated with this version
                        run = client.get_run(version.run_id)
                        
                        # Check if the experiment is deleted
                        experiment = client.get_experiment(run.info.experiment_id)
                        if experiment and experiment.lifecycle_stage == "deleted":
                            # Skip models from deleted experiments
                            continue

                        # Apply experiment filtering if specified
                        # Check if experiment filtering was requested (not just if matches exist)
                        if self.experiment_names is not None and experiment.name not in target_experiments:
                            continue

                        artifact_paths = self._list_artifacts(client, version.run_id)
                        
                        if artifact_paths:
                            artifact_data = self._download_and_parse_artifacts(client, version.run_id, artifact_paths)
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

                        # Summary for this model version
                        
                        # For latest_only filtering, track versions by model name
                        if self.latest_only:
                            if rm.name not in model_versions_by_name:
                                model_versions_by_name[rm.name] = []
                            model_versions_by_name[rm.name].append(model_info)
                        else:
                            models.append(model_info)

                    except Exception as e:
                        logger.debug(f"    ✗ Version {version.version}: Error - {str(e)}")
                        # Skip versions that can't be loaded - already filtered by model name patterns above

            # Apply latest_only filtering
            if self.latest_only:
                for model_name, model_list in model_versions_by_name.items():
                    # Sort by version number (descending) and take the first one
                    latest_model = max(model_list, key=lambda m: int(m.version))
                    models.append(latest_model)

            report_progress(1.0)

        except Exception as e:
            logger.warning(f"Error scanning registered models: {e}")

        return models

    def _list_artifacts(self, client, run_id: str, path: str = "") -> list[str]:
        """Recursively list all artifacts for a run.

        Args:
            client: MLflow client instance.
            run_id: The run ID to list artifacts from.
            path: The artifact path to start from (for recursion).

        Returns:
            List of artifact paths.
        """
        artifact_paths = []
        try:
            artifacts = client.list_artifacts(run_id, path)
            for artifact in artifacts:
                if artifact.is_dir:
                    # Recursively list artifacts in subdirectories
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
        """Download and parse CSV/text/image artifacts.

        Args:
            client: MLflow client instance.
            run_id: The run ID to download artifacts from.
            artifact_paths: List of artifact paths to process.

        Returns:
            Dict mapping artifact path to parsed content.
        """
        import base64
        import tempfile

        import pandas as pd

        artifact_data = {}
        

        for path in artifact_paths:
            try:
                if path.endswith('.csv'):
                    # Download to temp directory
                    local_path = client.download_artifacts(run_id, path, tempfile.gettempdir())
                    df = pd.read_csv(local_path)
                    artifact_data[path] = df.to_dict('records')
                    os.remove(local_path)
                elif path.endswith('.txt'):
                    local_path = client.download_artifacts(run_id, path, tempfile.gettempdir())
                    with open(local_path, 'r') as f:
                        content = f.read()
                        artifact_data[path] = content
                    os.remove(local_path)
                elif path.endswith(('.png', '.jpg', '.jpeg')):
                    # Download and embed images as base64
                    local_path = client.download_artifacts(run_id, path, tempfile.gettempdir())
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
                continue  # Skip artifacts that can't be parsed

        return artifact_data

    def _get_experiment_metadata(self, client) -> dict:
        """Get experiment metadata."""
        metadata = {}

        try:
            experiment = client.get_experiment_by_name(self.experiment_name)
            if experiment:
                # Skip deleted experiments
                if experiment.lifecycle_stage == "deleted":
                    metadata["experiment_skipped"] = True
                    metadata["skip_reason"] = f"Experiment '{self.experiment_name}' is deleted"
                    return metadata
                    
                metadata["experiment_id"] = experiment.experiment_id
                metadata["experiment_name"] = experiment.name
                metadata["artifact_location"] = experiment.artifact_location
                metadata["lifecycle_stage"] = experiment.lifecycle_stage

                # Get run count
                runs = client.search_runs(
                    experiment_ids=[experiment.experiment_id],
                    max_results=1,
                )
                metadata["has_runs"] = len(runs) > 0

        except Exception:
            pass

        return metadata
