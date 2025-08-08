from datetime import datetime, timezone
from uuid import uuid4

import os

from sqlalchemy import create_engine, text

import pytest
from testcontainers.postgres import PostgresContainer

import docker
from docker.errors import DockerException


def _docker_available() -> bool:
    try:
        docker.from_env().ping()
        return True
    except Exception:
        return False

os.environ.setdefault("MINIO_ENDPOINT", "dummy")
os.environ.setdefault("MINIO_ACCESS_KEY", "key")
os.environ.setdefault("MINIO_SECRET_KEY", "secret")
os.environ.setdefault("POSTGRES_DSN", "sqlite://")

from accscore.db.tasks import claim_tasks, select_runnable


def _setup_schema(conn):
    conn.execute(
        text(
            """
            CREATE TABLE jobs (
                id uuid PRIMARY KEY,
                order_seq bigint NOT NULL
            );
            CREATE TABLE job_tasks (
                id uuid PRIMARY KEY,
                job_id uuid REFERENCES jobs(id),
                task_key text NOT NULL,
                service_name text NOT NULL,
                status text NOT NULL,
                depends_on text[] NOT NULL DEFAULT '{}',
                next_attempt_at timestamptz,
                created_at timestamptz NOT NULL DEFAULT now(),
                assigned_node text,
                claimed_by text,
                claimed_at timestamptz
            );
            CREATE TABLE nodes (
                name text PRIMARY KEY,
                max_concurrency jsonb
            );
            """
        )
    )


def _insert_sample_data(conn):
    now = datetime.now(timezone.utc)
    conn.execute(
        text("INSERT INTO nodes (name, max_concurrency) VALUES ('n1', :mc::jsonb)"),
        {"mc": '{"svc":2}'},
    )

    j1, j2 = uuid4(), uuid4()
    conn.execute(
        text("INSERT INTO jobs (id, order_seq) VALUES (:j1, 1), (:j2, 2)"),
        {"j1": j1, "j2": j2},
    )

    tasks = []
    for job_id, prefix in [(j1, "a"), (j2, "b")]:
        t1 = uuid4()
        t2 = uuid4()
        t3 = uuid4()
        tasks.append((t1, job_id, f"{prefix}1", []))
        tasks.append((t2, job_id, f"{prefix}2", [f"{prefix}1"]))
        tasks.append((t3, job_id, f"{prefix}3", [f"{prefix}2"]))

    for tid, job_id, key, deps in tasks:
        conn.execute(
            text(
                """
                INSERT INTO job_tasks (id, job_id, task_key, service_name, status, depends_on, created_at)
                VALUES (:id, :job_id, :key, 'svc', 'queued', :deps, :now)
                """
            ),
            {"id": tid, "job_id": job_id, "key": key, "deps": deps, "now": now},
        )


@pytest.mark.skipif(not _docker_available(), reason="Docker not available")
def test_select_and_claim_runnable_tasks():
    with PostgresContainer("postgres:15-alpine") as pg:
        engine = create_engine(pg.get_connection_url(), future=True)
        with engine.begin() as conn:
            _setup_schema(conn)
            _insert_sample_data(conn)

        with engine.begin() as conn:
            tasks = select_runnable("svc", 10, conn=conn)
            assert [t["task_key"] for t in tasks] == ["a1", "b1"]
            count = claim_tasks([t["id"] for t in tasks], "nodeA", conn=conn)
            assert count == 2

        with engine.begin() as conn:
            remaining = select_runnable("svc", 10, conn=conn)
            assert remaining == []

        # Mark first tasks done and ensure next tasks become runnable
        with engine.begin() as conn:
            conn.execute(
                text(
                    "UPDATE job_tasks SET status='done' WHERE task_key IN ('a1', 'b1')"
                )
            )

        with engine.begin() as conn:
            tasks = select_runnable("svc", 10, conn=conn)
            assert [t["task_key"] for t in tasks] == ["a2", "b2"]

