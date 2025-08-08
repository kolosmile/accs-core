import json
import os
from uuid import uuid4

os.environ.setdefault("MINIO_ENDPOINT", "example")
os.environ.setdefault("MINIO_ACCESS_KEY", "key")
os.environ.setdefault("MINIO_SECRET_KEY", "secret")
os.environ.setdefault("POSTGRES_DSN", "sqlite:///:memory:")

from sqlalchemy import create_engine, text

from accscore.db.jobs import instantiate_job_tasks


def test_instantiate_job_tasks_idempotent():
    engine = create_engine("sqlite:///:memory:")
    # setup schema and seed data
    with engine.begin() as conn:
        conn.execute(text("CREATE TABLE workflows (id TEXT PRIMARY KEY, steps TEXT)"))
        conn.execute(
            text(
                """
            CREATE TABLE jobs (
                id TEXT PRIMARY KEY,
                workflow_id TEXT,
                status TEXT
            )
            """
            )
        )
        conn.execute(
            text(
                """
            CREATE TABLE job_tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                job_id TEXT,
                task_key TEXT,
                service_name TEXT,
                status TEXT,
                depends_on TEXT,
                params TEXT,
                attempt INTEGER,
                max_attempts INTEGER
            )
            """
            )
        )

        wf_id = uuid4()
        job_id = uuid4()

        steps = [
            {"key": "s1", "service": "svc1", "default_params": {"a": 1}},
            {"key": "s2", "service": "svc2", "depends_on": ["s1"], "default_params": {"b": 2}},
        ]
        conn.execute(
            text("INSERT INTO workflows (id, steps) VALUES (:id, :steps)"),
            {"id": str(wf_id), "steps": json.dumps(steps)},
        )
        conn.execute(
            text("INSERT INTO jobs (id, workflow_id, status) VALUES (:id, :wf, 'queued')"),
            {"id": str(job_id), "wf": str(wf_id)},
        )

    with engine.connect() as conn:
        instantiate_job_tasks(job_id, conn=conn)

        rows = conn.execute(
            text(
                "SELECT task_key, service_name, status, depends_on, params, attempt, max_attempts FROM job_tasks ORDER BY id"
            )
        ).fetchall()
        assert len(rows) == 2
        assert rows[0][0] == "s1"
        assert rows[0][2] == "queued"
        assert rows[1][0] == "s2"
        assert json.loads(rows[1][3]) == ["s1"]
        assert json.loads(rows[0][4]) == {"a": 1}
        assert rows[0][5] == 0 and rows[0][6] == 3

        status = conn.execute(text("SELECT status FROM jobs WHERE id=:id"), {"id": str(job_id)}).scalar_one()
        assert status == "running"

        conn.commit()

    with engine.connect() as conn:
        # idempotency
        instantiate_job_tasks(job_id, conn=conn)
        count = conn.execute(text("SELECT COUNT(*) FROM job_tasks")).scalar_one()
        assert count == 2
