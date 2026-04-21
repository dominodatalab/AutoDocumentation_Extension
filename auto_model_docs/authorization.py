"""Authorization gates for sensitive routes.

Each ``require_*`` helper asks Domino whether the viewing user is allowed
to perform the given action and raises ``HTTPException(403)`` on deny.

Any failure to reach the authz service (network error, non-200, malformed
body, missing project / job id) is treated as deny -- fail closed.
"""

from __future__ import annotations

import logging
from typing import Optional

from starlette.exceptions import HTTPException

from authorized_actions import AuthorizedActionRequestItem, authorized_action_allowed

logger = logging.getLogger(__name__)


def _allowed(action: AuthorizedActionRequestItem) -> bool:
    try:
        return authorized_action_allowed(action)
    except Exception:
        logger.exception("Authz check failed for %s", action.code)
        return False


def _project_action(code: str, project_id: str) -> AuthorizedActionRequestItem:
    return AuthorizedActionRequestItem(
        id=f"{code}-{project_id}",
        code=code,
        context={"projectId": project_id},
    )


def _job_action(code: str, job_id: str) -> AuthorizedActionRequestItem:
    return AuthorizedActionRequestItem(
        id=f"{code}-{job_id}",
        code=code,
        context={"jobId": job_id},
    )


def require_domino_job_start(project_id: Optional[str]) -> None:
    if not project_id or not _allowed(
        _project_action("job.project.start_job", project_id)
    ):
        raise HTTPException(
            status_code=403,
            detail="This operation requires permission to start jobs in the target project.",
        )


def require_domino_job_stop(job_id: Optional[str]) -> None:
    if not job_id or not _allowed(_job_action("job.project.stop_job", job_id)):
        raise HTTPException(
            status_code=403,
            detail="This operation requires permission to stop the target job.",
        )


def require_domino_job_list(project_id: Optional[str]) -> None:
    if not project_id or not _allowed(
        _project_action("job.project.list_jobs", project_id)
    ):
        raise HTTPException(
            status_code=403,
            detail="This operation requires permission to list jobs in the target project.",
        )


def require_project_write(project_id: Optional[str]) -> None:
    if not project_id or not _allowed(
        _project_action("project.change_project_settings", project_id)
    ):
        raise HTTPException(
            status_code=403,
            detail="This operation requires write permission on the target project.",
        )
