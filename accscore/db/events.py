from __future__ import annotations

from typing import Any, Optional
from datetime import datetime
import json

from sqlalchemy import text
from sqlalchemy.engine import Connection


_ALLOWED_LEVELS = {"debug", "info", "warn", "error"}
_ALLOWED_TYPES = {"status", "progress", "log", "artifact", "heartbeat", "retry"}


def log_event(
    level: str,
    type: str,
    message: str,
    *,
    data: Optional[dict[str, Any]] = None,
    job_id: Optional[str] = None,
    job_task_id: Optional[str] = None,
    source: str = "service:unknown",
    conn: Connection,
    ts: Optional[datetime] = None,
) -> int:
    """Insert a row into ``task_events`` and return the new id.

    Parameters
    ----------
    level:
        Log level, must be one of ``debug``, ``info``, ``warn``, ``error``.
    type:
        Event type according to specification.
    message:
        Event message text.
    data:
        Optional JSON serialisable payload.
    job_id:
        Related job identifier. Required unless ``job_task_id`` is provided
        and resolves to a job.
    job_task_id:
        Optional task identifier. When provided the function validates that
        the supplied ``job_id`` matches the task's job.
    source:
        Source string, defaults to ``service:unknown``.
    conn:
        Open SQLAlchemy connection.
    ts:
        Optional timestamp. If omitted the database current timestamp is used.
    """

    if level not in _ALLOWED_LEVELS:
        raise ValueError(f"invalid level: {level!r}")
    if type not in _ALLOWED_TYPES:
        raise ValueError(f"invalid type: {type!r}")

    # sanity check for job/task relation
    if job_task_id is not None:
        row = conn.execute(
            text("SELECT job_id FROM job_tasks WHERE id = :tid"), {"tid": job_task_id}
        ).fetchone()
        if row is None:
            raise ValueError(f"job_task_id {job_task_id!r} not found")
        task_job_id = row[0]
        if job_id is None:
            job_id = task_job_id
        elif job_id != task_job_id:
            raise ValueError("job_id does not match job_task_id")

    if job_id is None:
        raise ValueError("job_id is required")

    payload = data or {}
    if conn.dialect.name == "sqlite":
        payload = json.dumps(payload)

    sql = text(
        """
        INSERT INTO task_events (job_id, job_task_id, ts, source, level, type, message, data)
        VALUES (:job_id, :job_task_id, COALESCE(:ts, CURRENT_TIMESTAMP), :source, :level, :type, :message, :data)
        RETURNING id
        """
    )

    result = conn.execute(
        sql,
        {
            "job_id": job_id,
            "job_task_id": job_task_id,
            "ts": ts,
            "source": source,
            "level": level,
            "type": type,
            "message": message,
            "data": payload,
        },
    )
    return result.scalar_one()
