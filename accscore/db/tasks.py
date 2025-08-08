"""Utilities for selecting and claiming runnable tasks."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.engine import Connection


JobTaskRow = Dict[str, Any]


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _get_capacity(service_name: str, limit: int, *, conn: Connection) -> int:
    """Compute remaining capacity for a service respecting node limits."""

    running = conn.execute(
        text(
            """
            SELECT count(*)
            FROM job_tasks
            WHERE service_name = :service
              AND status IN ('starting', 'running')
            """
        ),
        {"service": service_name},
    ).scalar_one()

    max_concurrency = conn.execute(
        text(
            """
            SELECT sum((max_concurrency->>:service)::int)
            FROM nodes
            WHERE max_concurrency ? :service
            """
        ),
        {"service": service_name},
    ).scalar_one()

    if max_concurrency is None:
        return limit

    remaining = max_concurrency - running
    if remaining <= 0:
        return 0
    return min(limit, remaining)


def select_runnable(
    service_name: str,
    limit: int,
    *,
    conn: Connection,
    now: Optional[datetime] = None,
) -> List[JobTaskRow]:
    """Select runnable tasks for a service using row-level locks.

    The caller is responsible for running this inside a transaction so that the
    selected rows remain locked until :func:`claim_tasks` is invoked.
    """

    now = now or _utcnow()
    capacity = _get_capacity(service_name, limit, conn=conn)
    if capacity <= 0:
        return []

    sql = text(
        """
        SELECT jt.*
        FROM job_tasks jt
        JOIN jobs j ON j.id = jt.job_id
        WHERE jt.service_name = :service
          AND jt.status = 'queued'
          AND (jt.next_attempt_at IS NULL OR jt.next_attempt_at <= :now)
          AND NOT EXISTS (
            SELECT 1 FROM job_tasks dep
            WHERE dep.job_id = jt.job_id
              AND dep.task_key = ANY(jt.depends_on)
              AND dep.status <> 'done'
          )
        ORDER BY j.order_seq ASC, jt.created_at ASC, jt.id ASC
        FOR UPDATE SKIP LOCKED
        LIMIT :limit
        """
    )

    rows = conn.execute(
        sql, {"service": service_name, "now": now, "limit": capacity}
    ).mappings()
    return [dict(row) for row in rows]


def claim_tasks(
    task_ids: List[UUID],
    node_name: str,
    *,
    conn: Connection,
    now: Optional[datetime] = None,
) -> int:
    """Claim previously selected tasks for a node."""

    if not task_ids:
        return 0

    now = now or _utcnow()
    sql = text(
        """
        UPDATE job_tasks
        SET claimed_by = :node,
            assigned_node = :node,
            status = 'starting',
            claimed_at = :now
        WHERE id = ANY(:ids)
        """
    )

    result = conn.execute(sql, {"node": node_name, "now": now, "ids": list(task_ids)})
    return result.rowcount or 0

