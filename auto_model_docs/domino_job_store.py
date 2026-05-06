"""Job history hooks for Studio (no local persistence).

``/job-history`` and cancel return empty until Domino run listing is implemented.
"""

from __future__ import annotations

from typing import Any


def get_user_jobs(dataset_id: str, snapshot_id: str, owner_id: str, limit: int = 50) -> list[dict[str, Any]]:
    return []


def cancel_queued_jobs(dataset_id: str, snapshot_id: str, owner_id: str) -> None:
    pass
