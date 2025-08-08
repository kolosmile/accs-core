import pytest
from sqlalchemy import create_engine, text


def setup_env(monkeypatch):
    monkeypatch.setenv("MINIO_ENDPOINT", "localhost:9000")
    monkeypatch.setenv("MINIO_ACCESS_KEY", "key")
    monkeypatch.setenv("MINIO_SECRET_KEY", "secret")
    monkeypatch.setenv("POSTGRES_DSN", "sqlite:///:memory:")


# Smoke tests for log_event

def test_log_event_basic(monkeypatch):
    setup_env(monkeypatch)
    from accscore.db.events import log_event

    engine = create_engine("sqlite:///:memory:", future=True)
    with engine.begin() as conn:
        conn.execute(text("CREATE TABLE job_tasks (id TEXT PRIMARY KEY, job_id TEXT NOT NULL)"))
        conn.execute(
            text(
                """
                CREATE TABLE task_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    job_id TEXT NOT NULL,
                    job_task_id TEXT,
                    ts TEXT NOT NULL,
                    source TEXT,
                    level TEXT,
                    type TEXT,
                    message TEXT,
                    data TEXT
                )
                """
            )
        )

        event_id = log_event("info", "log", "hello", job_id="job1", conn=conn)
        row = conn.execute(text("SELECT message FROM task_events WHERE id=:id"), {"id": event_id}).one()
        assert row[0] == "hello"


def test_log_event_with_task(monkeypatch):
    setup_env(monkeypatch)
    from accscore.db.events import log_event

    engine = create_engine("sqlite:///:memory:", future=True)
    with engine.begin() as conn:
        conn.execute(text("CREATE TABLE job_tasks (id TEXT PRIMARY KEY, job_id TEXT NOT NULL)"))
        conn.execute(
            text(
                """
                CREATE TABLE task_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    job_id TEXT NOT NULL,
                    job_task_id TEXT,
                    ts TEXT NOT NULL,
                    source TEXT,
                    level TEXT,
                    type TEXT,
                    message TEXT,
                    data TEXT
                )
                """
            )
        )
        conn.execute(text("INSERT INTO job_tasks (id, job_id) VALUES ('t1','j1')"))

        event_id = log_event("info", "log", "hi", job_task_id="t1", conn=conn)
        row = conn.execute(text("SELECT job_id, job_task_id FROM task_events WHERE id=:id"), {"id": event_id}).one()
        assert row[0] == "j1"
        assert row[1] == "t1"


def test_log_event_mismatched_job(monkeypatch):
    setup_env(monkeypatch)
    from accscore.db.events import log_event

    engine = create_engine("sqlite:///:memory:", future=True)
    with engine.begin() as conn:
        conn.execute(text("CREATE TABLE job_tasks (id TEXT PRIMARY KEY, job_id TEXT NOT NULL)"))
        conn.execute(
            text(
                """
                CREATE TABLE task_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    job_id TEXT NOT NULL,
                    job_task_id TEXT,
                    ts TEXT NOT NULL,
                    source TEXT,
                    level TEXT,
                    type TEXT,
                    message TEXT,
                    data TEXT
                )
                """
            )
        )
        conn.execute(text("INSERT INTO job_tasks (id, job_id) VALUES ('t1','j1')"))

        with pytest.raises(ValueError):
            log_event("info", "log", "bad", job_id="j2", job_task_id="t1", conn=conn)
