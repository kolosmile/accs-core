from __future__ import annotations

import json
from uuid import UUID

from sqlalchemy import text



def instantiate_job_tasks(job_id: UUID, *, conn) -> None:
    """Instantiate job tasks for a job based on its workflow definition.

    Parameters
    ----------
    job_id:
        Identifier of the job to instantiate tasks for.
    conn:
        SQLAlchemy connection to use. The function manages its own transaction.
    """

    with conn.begin():
        workflow_id_row = conn.execute(
            text("SELECT workflow_id FROM jobs WHERE id=:job_id"),
            {"job_id": str(job_id)},
        ).one_or_none()
        if workflow_id_row is None:
            return
        workflow_id = workflow_id_row[0]

        steps_row = conn.execute(
            text("SELECT steps FROM workflows WHERE id=:wf_id"),
            {"wf_id": workflow_id},
        ).one_or_none()
        if steps_row is None:
            return

        steps = steps_row[0] or []
        if isinstance(steps, str):
            steps = json.loads(steps)

        inserted = 0
        for step in steps:
            task_key = step.get("key")
            service_name = step.get("service")
            depends_on = step.get("depends_on") or []
            params = step.get("default_params") or {}

            if conn.dialect.name == "sqlite":
                depends_on_param = json.dumps(depends_on)
                params_param = json.dumps(params)
            else:
                depends_on_param = depends_on
                params_param = params

            exists = conn.execute(
                text(
                    "SELECT 1 FROM job_tasks WHERE job_id=:job_id AND task_key=:task_key"
                ),
                {"job_id": str(job_id), "task_key": task_key},
            ).fetchone()
            if exists:
                continue

            conn.execute(
                text(
                    """
                    INSERT INTO job_tasks
                        (job_id, task_key, service_name, status, depends_on, params, attempt, max_attempts)
                    VALUES (:job_id, :task_key, :service_name, 'queued', :depends_on, :params, 0, 3)
                    """
                ),
                {
                    "job_id": str(job_id),
                    "task_key": task_key,
                    "service_name": service_name,
                    "depends_on": depends_on_param,
                    "params": params_param,
                },
            )
            inserted += 1

        if inserted:
            conn.execute(
                text("UPDATE jobs SET status='running' WHERE id=:job_id"),
                {"job_id": str(job_id)},
            )
