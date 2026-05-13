"""SQLite-backed job history for Studio (WAL, under DOMINO_DATASETS_DIR / DOMINO_PROJECT_NAME)."""

from __future__ import annotations

import logging
import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

_ACTIVE_REFRESH_STATUSES = frozenset({"queued", "submitted", "pending", "running"})


def _job_db_not_configured_msg() -> str | None:
    if not (os.environ.get("DOMINO_DATASETS_DIR") or "").strip():
        return "DOMINO_DATASETS_DIR is not set"
    if not (os.environ.get("DOMINO_PROJECT_NAME") or "").strip():
        return "DOMINO_PROJECT_NAME is not set"
    return None


def _db_path() -> Path | None:
    root = (os.environ.get("DOMINO_DATASETS_DIR") or "").strip()
    name = (os.environ.get("DOMINO_PROJECT_NAME") or "").strip()
    if not root or not name:
        return None
    return Path(root) / name / ".data" / "jobs.sqlite"


def _connect(db_file: Path) -> sqlite3.Connection:
    db_file.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(
        str(db_file),
        timeout=30.0,
        check_same_thread=False,
        isolation_level=None,
    )
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    conn.execute("PRAGMA busy_timeout=30000")
    return conn


def _ensure_schema(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS studio_jobs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            owner_id TEXT NOT NULL,
            project_id TEXT NOT NULL,
            domino_run_id TEXT NOT NULL,
            job_url TEXT,
            status TEXT NOT NULL,
            branch TEXT,
            hardware_tier TEXT,
            spec_path TEXT,
            submitted_at TEXT NOT NULL
        )
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_studio_jobs_owner_project
        ON studio_jobs(owner_id, project_id, submitted_at DESC)
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_studio_jobs_run
        ON studio_jobs(domino_run_id)
        """
    )


def ensure_database() -> None:
    db_file = _db_path()
    if db_file is None:
        msg = _job_db_not_configured_msg()
        if msg:
            logger.warning("%s; job database was not created", msg)
        return
    try:
        conn = _connect(db_file)
        try:
            _ensure_schema(conn)
        finally:
            conn.close()
        logger.info("Job history database initialized at %s", db_file)
    except Exception:
        logger.exception("Failed to initialize job history database at %s", db_file)


def _domino_client():
    import domino_client

    return domino_client


def _refresh_active_rows(conn: sqlite3.Connection, project_id: str, owner_id: str) -> None:
    client = _domino_client()
    cur = conn.execute(
        """
        SELECT id, domino_run_id, status FROM studio_jobs
        WHERE owner_id = ? AND project_id = ?
        """,
        (owner_id, project_id),
    )
    rows = cur.fetchall()
    for row in rows:
        st = (row["status"] or "").strip().lower()
        if st not in _ACTIVE_REFRESH_STATUSES:
            continue
        info = client.get_job_status(row["domino_run_id"])
        local = (info.get("local_status") or "submitted").strip().lower()
        conn.execute(
            "UPDATE studio_jobs SET status = ? WHERE id = ?",
            (local, row["id"]),
        )


def record_job(
    owner_id: str,
    project_id: str,
    *,
    domino_run_id: str,
    job_url: str,
    hardware_tier: str,
    spec_path: str,
    status: str = "submitted",
) -> None:
    if not owner_id or not project_id or not domino_run_id:
        return
    db_file = _db_path()
    if db_file is None:
        msg = _job_db_not_configured_msg()
        if msg:
            logger.warning("%s; job history not persisted", msg)
        return
    submitted_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    try:
        conn = _connect(db_file)
        try:
            _ensure_schema(conn)
            conn.execute(
                """
                INSERT INTO studio_jobs (
                    owner_id, project_id, domino_run_id, job_url, status,
                    branch, hardware_tier, spec_path, submitted_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    owner_id,
                    project_id,
                    domino_run_id,
                    job_url or "",
                    (status or "submitted").strip().lower(),
                    "",
                    hardware_tier or "",
                    spec_path or "",
                    submitted_at,
                ),
            )
        finally:
            conn.close()
    except Exception:
        logger.exception("record_job failed for project %s", project_id)


def get_user_jobs(project_id: str, owner_id: str, limit: int = 50) -> list[dict[str, Any]]:
    if not owner_id or not project_id:
        return []
    db_file = _db_path()
    if db_file is None:
        return []
    limit = max(1, min(int(limit), 500))
    try:
        conn = _connect(db_file)
        try:
            _ensure_schema(conn)
            try:
                _refresh_active_rows(conn, project_id, owner_id)
            except Exception:
                logger.warning(
                    "Refreshing job status failed for project %s", project_id, exc_info=True
                )

            cur = conn.execute(
                """
                SELECT id, domino_run_id, job_url, status, hardware_tier,
                       spec_path, submitted_at
                FROM studio_jobs
                WHERE owner_id = ? AND project_id = ?
                ORDER BY submitted_at DESC
                LIMIT ?
                """,
                (owner_id, project_id, limit),
            )
            out: list[dict[str, Any]] = []
            for row in cur.fetchall():
                rid = row["domino_run_id"] or ""
                st = (row["status"] or "submitted").strip().lower()
                out.append(
                    {
                        "id": str(row["id"]),
                        "domino_run_id": rid,
                        "job_url": row["job_url"] or "",
                        "status": st,
                        "hardware_tier": row["hardware_tier"] or "",
                        "spec_path": row["spec_path"] or "",
                        "submitted_at": row["submitted_at"] or "",
                    }
                )
            return out
        finally:
            conn.close()
    except Exception:
        logger.exception("get_user_jobs failed for project %s", project_id)
        return []


def cancel_queued_jobs(project_id: str, owner_id: str) -> None:
    return None
