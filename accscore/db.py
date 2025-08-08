"""Database utilities using SQLAlchemy."""

from contextlib import contextmanager
from typing import Iterator, List, Dict, Any

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker, Session

from .settings import Settings


settings = Settings()
engine: Engine = create_engine(settings.postgres_dsn, future=True)
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
