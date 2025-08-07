from accscore.schema import Job, JobStatus


def test_job_model():
    job = Job(id="1", status=JobStatus.PENDING)
    assert job.status == JobStatus.PENDING
    assert job.result is None
