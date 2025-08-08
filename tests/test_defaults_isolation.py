from uuid import uuid4

from accscore.schema import Node, WorkflowStep, JobTask, TaskStatus


def test_workflowstep_depends_on_is_isolated():
    step1 = WorkflowStep(key="step1", service="svc")
    step2 = WorkflowStep(key="step2", service="svc")

    step1.depends_on.append("init")
    assert step1.depends_on == ["init"]
    assert step2.depends_on == []
    assert step1.depends_on is not step2.depends_on


def test_jobtask_params_and_results_isolated():
    task1 = JobTask(
        id=uuid4(),
        job_id=uuid4(),
        task_key="t1",
        service_name="svc",
        status=TaskStatus.QUEUED,
    )
    task2 = JobTask(
        id=uuid4(),
        job_id=uuid4(),
        task_key="t2",
        service_name="svc",
        status=TaskStatus.QUEUED,
    )

    task1.params["a"] = 1
    task1.results["b"] = 2

    assert task2.params == {}
    assert task2.results == {}
    assert task1.params is not task2.params
    assert task1.results is not task2.results

    task2.params["c"] = 3
    task2.results["d"] = 4

    assert "c" not in task1.params
    assert "d" not in task1.results


def test_node_labels_and_max_concurrency_isolated():
    node1 = Node(name="n1")
    node2 = Node(name="n2")

    node1.labels["role"] = "worker"
    node1.max_concurrency["svc"] = 5

    assert node2.labels == {}
    assert node2.max_concurrency == {}
    assert node1.labels is not node2.labels
    assert node1.max_concurrency is not node2.max_concurrency

    node2.labels["arch"] = "x86"
    node2.max_concurrency["svc"] = 1
    
    assert "arch" not in node1.labels
    assert node1.max_concurrency["svc"] == 5
    assert node2.max_concurrency["svc"] == 1
