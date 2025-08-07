"""Database utilities using SQLAlchemy."""

from contextlib import contextmanager
from typing import Iterator

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
