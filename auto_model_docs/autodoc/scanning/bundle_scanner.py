"""Governance bundle scanner: resolve Active bundles for scanned MLflow models."""

from __future__ import annotations

import asyncio
import logging
import os
from typing import Callable, List, Optional, Set

from autodoc.core.models import BundleSummary, ComputedPolicy, ModelInfo
from domino_client import compute_policy, get_findings, list_bundles

ProgressCallback = Callable[[float], None]

logger = logging.getLogger(__name__)

ACTIVE_BUNDLE_STATE = "Active"


def bundle_matches_models(bundle: BundleSummary, model_names: Set[str]) -> bool:
    for att in bundle.attachments:
        if att.type != "ModelVersion":
            continue
        name = (att.identifier or {}).get("name", "")
        if str(name) in model_names:
            return True
    return False


class BundleScanner:
    """Fetches governance compliance data for Active bundles tied to scanned models.

    Runs synchronously against the governance API via domino_client.
    Intended to be invoked from the orchestrator scan phase after MLflow scan.
    """

    def scan_for_models(
        self,
        model_names: Set[str],
        project_id: Optional[str] = None,
        api_host: Optional[str] = None,
        on_progress: Optional[ProgressCallback] = None,
    ) -> List[ComputedPolicy]:
        pid = (project_id or os.environ.get("DOMINO_PROJECT_ID", "")).strip()
        host = (api_host or "").strip()
        if not pid or not model_names or not host:
            if on_progress:
                on_progress(1.0)
            return []

        policies: List[ComputedPolicy] = []
        bundles = list_bundles(pid, api_host=host)
        matching = [
            b
            for b in bundles
            if b.state == ACTIVE_BUNDLE_STATE and bundle_matches_models(b, model_names)
        ]
        total = len(matching)

        for idx, bundle in enumerate(matching):
            cp = compute_policy(str(bundle.id), str(bundle.policy_id), api_host=host)
            if cp is not None:
                cp.findings = get_findings(str(bundle.id), api_host=host)
                policies.append(cp)
            if on_progress and total:
                on_progress((idx + 1) / total)

        if on_progress and not total:
            on_progress(1.0)

        return policies

    async def scan(
        self,
        models: List[ModelInfo],
        project_id: Optional[str] = None,
        on_progress: Optional[ProgressCallback] = None,
    ) -> List[ComputedPolicy]:
        names = {m.name for m in models if m.name}
        return await asyncio.to_thread(
            self.scan_for_models,
            names,
            project_id,
            on_progress,
        )
