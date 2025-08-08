"""Database utilities using SQLAlchemy."""

from contextlib import contextmanager
from typing import Iterator, List, Dict, Any, Optional

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker, Session

from .settings import Settings


settings = Settings()
engine: Engine = create_engine(settings.postgres_dsn, future=True, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


@contextmanager
def session_scope() -> Iterator[Session]:
    """Provide a transactional scope around a series of operations."""
    session: Session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def check_connection() -> bool:
    """Check database connectivity."""
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception:
        return False


def claim_tasks(session: Session, service: str, capacity: int, agent: str) -> List[Dict[str, Any]]:
    """Claim queued tasks for a service respecting global job order.

    Parameters
    ----------
    session:
        Open SQLAlchemy session.
    service:
        Name of the service to claim tasks for.
    capacity:
        Maximum number of tasks to claim.
    agent:
        Identifier of the claiming agent.
    """

    sql = text(
        """
        WITH c AS (
          SELECT jt.id
          FROM job_tasks jt
          JOIN jobs j ON j.id = jt.job_id
          WHERE jt.service_name = :service
            AND jt.status = 'queued'
            AND (jt.next_attempt_at IS NULL OR jt.next_attempt_at <= now())
            AND NOT EXISTS (
              SELECT 1 FROM job_tasks dep
              WHERE dep.job_id = jt.job_id
                AND dep.task_key = ANY(jt.depends_on)
                AND dep.status <> 'done'
            )
          ORDER BY j.order_seq ASC, jt.created_at ASC, jt.id ASC
          FOR UPDATE SKIP LOCKED
          LIMIT :capacity
        )
        UPDATE job_tasks t
        SET status='starting', claimed_by=:agent, claimed_at=now()
        FROM c
        WHERE t.id = c.id
        RETURNING t.*
        """
    )

    result = session.execute(sql, {"service": service, "capacity": capacity, "agent": agent})
    return [dict(row) for row in result.mappings()]


def instantiate_tasks(session: Session, job_id: str) -> None:
    """Instantiate job tasks for a job from its workflow definition."""
    sql = text(
        """
        INSERT INTO job_tasks (job_id, task_key, service_name, status, depends_on, params)
        SELECT :job_id, s.key, s.service, 'queued', COALESCE(s.depends_on, '{}'),
               COALESCE(s.default_params, '{}')
        FROM workflows w,
             jsonb_to_recordset(w.steps) AS s(
                 key TEXT,
                 service TEXT,
                 depends_on TEXT[],
                 default_params JSONB
             )
        WHERE w.id = (SELECT workflow_id FROM jobs WHERE id = :job_id)
        """
    )
    session.execute(sql, {"job_id": job_id})


def mark_task_running(session: Session, task_id: str) -> None:
    """Mark a task as running and set start timestamp."""
    sql = text(
        "UPDATE job_tasks SET status='running', started_at=COALESCE(started_at, now()) WHERE id=:task_id"
    )
    session.execute(sql, {"task_id": task_id})


def update_task_progress(session: Session, task_id: str, percent: float) -> None:
    """Update task progress percentage."""
    sql = text("UPDATE job_tasks SET progress=:percent, updated_at=now() WHERE id=:task_id")
    session.execute(sql, {"task_id": task_id, "percent": percent})


def mark_task_done(session: Session, task_id: str, results: Optional[Dict[str, Any]] = None) -> None:
    """Mark a task as done and optionally store results."""
    sql = text(
        "UPDATE job_tasks SET status='done', results=COALESCE(:results, results), finished_at=now() WHERE id=:task_id"
    )
    session.execute(sql, {"task_id": task_id, "results": results})


def mark_task_error(
    session: Session, task_id: str, error_code: str, message: str
) -> None:
    """Mark a task as errored and store error info."""
    sql = text(
        """
        UPDATE job_tasks
        SET status='error', finished_at=now(),
            results=jsonb_set(COALESCE(results, '{}'::jsonb), '{error}', to_jsonb(:error_info))
        WHERE id=:task_id
        """
    )
    session.execute(sql, {"task_id": task_id, "error_info": {"code": error_code, "message": message}})


def append_event(
    session: Session,
    *,
    job_id: str,
    job_task_id: Optional[str] = None,
    level: str = "info",
    type: str = "log",
    message: str = "",
    data: Optional[Dict[str, Any]] = None,
) -> None:
    """Insert a new event row."""
    sql = text(
        "INSERT INTO task_events (job_id, job_task_id, ts, source, level, type, message, data)"
        " VALUES (:job_id, :job_task_id, now(), :source, :level, :type, :message, :data)"
    )
    session.execute(
        sql,
        {
            "job_id": job_id,
            "job_task_id": job_task_id,
            "source": "builder",
            "level": level,
            "type": type,
            "message": message,
            "data": data or {},
        },
    )


def record_artifact(
    session: Session,
    *,
    job_id: str,
    job_task_id: Optional[str] = None,
    kind: str,
    bucket: str,
    key: str,
    size: Optional[int] = None,
    content_type: Optional[str] = None,
    checksum: Optional[str] = None,
) -> None:
    """Insert artifact metadata."""
    sql = text(
        """
        INSERT INTO task_artifacts (job_id, job_task_id, kind, bucket, key, size_bytes, content_type, checksum, created_at)
        VALUES (:job_id, :job_task_id, :kind, :bucket, :key, :size, :content_type, :checksum, now())
        """
    )
    session.execute(
        sql,
        {
            "job_id": job_id,
            "job_task_id": job_task_id,
            "kind": kind,
            "bucket": bucket,
            "key": key,
            "size": size,
            "content_type": content_type,
            "checksum": checksum,
        },
    )


def maybe_finish_job(session: Session, job_id: str) -> None:
    """If all tasks are done or skipped, mark the job as finished."""
    sql = text(
        """
        UPDATE jobs
        SET status='done', finished_at=now()
        WHERE id=:job_id
          AND NOT EXISTS (
            SELECT 1 FROM job_tasks WHERE job_id=:job_id AND status NOT IN ('done','skipped')
          )
        """
    )
    session.execute(sql, {"job_id": job_id})
