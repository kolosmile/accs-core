from uuid import uuid4

from accscore.schema import (
    Job,
    JobStatus,
    JobTask,
    TaskStatus,
    WorkflowDef,
    WorkflowStep,
)


def test_workflow_model():
    step = WorkflowStep(key="ingest", service="ingest")
    wf = WorkflowDef(name="test", version=1, steps=[step])
    assert wf.steps[0].key == "ingest"


def test_job_model():
    job = Job(
        id=uuid4(),
        workflow_id=uuid4(),
        status=JobStatus.QUEUED,
        order_seq=1,
    )
    assert job.status == JobStatus.QUEUED
    assert job.progress is None


def test_job_task_model():
    jt = JobTask(
        id=uuid4(),
        job_id=uuid4(),
        task_key="ingest",
        service_name="ingest",
        status=TaskStatus.QUEUED,
    )
    assert jt.status == TaskStatus.QUEUED
