"""Pydantic models and enums reflecting the ACCScore DB-driven workflow."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


class JobStatus(str, Enum):
    """Possible states for a job."""

    QUEUED = "queued"
    RUNNING = "running"
    DONE = "done"
    ERROR = "error"


class TaskStatus(str, Enum):
    """States for individual job tasks."""

    QUEUED = "queued"
    STARTING = "starting"
    RUNNING = "running"
    DONE = "done"
    ERROR = "error"
    SKIPPED = "skipped"


class EventLevel(str, Enum):
    """Log levels for task events."""

    DEBUG = "debug"
    INFO = "info"
    WARN = "warn"
    ERROR = "error"


class EventType(str, Enum):
    """Types of task events."""

    STATUS = "status"
    PROGRESS = "progress"
    LOG = "log"
    ARTIFACT = "artifact"
    HEARTBEAT = "heartbeat"
    RETRY = "retry"


class ArtifactKind(str, Enum):
    """Kinds of artifacts a task can produce."""

    INPUT = "input"
    OUTPUT = "output"
    LOG = "log"


class AwakeState(str, Enum):
    """Node awake state used by the node agent."""

    UNKNOWN = "unknown"
    AWAKE = "awake"
    SLEEP = "sleep"


class WakeMethod(str, Enum):
    """How a node can be woken up."""

    WOL = "wol"
    PROVIDER = "provider"
    SCRIPT = "script"


class WorkflowStep(BaseModel):
    """A single step definition inside a workflow."""

    key: str
    service: str
    depends_on: list[str] = Field(default_factory=list)
    default_params: dict[str, object] = Field(default_factory=dict)


class WorkflowDef(BaseModel):
    """Workflow definition as stored in the database."""

    id: Optional[UUID] = None
    name: str
    version: int
    steps: list[WorkflowStep]
    is_active: bool = True
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class Job(BaseModel):
    """Job record representing a workflow execution."""

    id: UUID
    workflow_id: UUID
    status: JobStatus
    progress: Optional[float] = None
    current_task_key: Optional[str] = None
    priority: int = 0
    order_seq: int
    options: dict[str, object] = Field(default_factory=dict)
    scheduled_at: Optional[datetime] = None
    error_code: Optional[str] = None
    error_message: Optional[str] = None
    created_at: Optional[datetime] = None
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class JobTask(BaseModel):
    """Task belonging to a job."""

    id: UUID
    job_id: UUID
    task_key: str
    service_name: str
    status: TaskStatus
    depends_on: list[str] = Field(default_factory=list)
    attempt: int = 0
    max_attempts: int = 3
    next_attempt_at: Optional[datetime] = None
    priority: int = 0
    progress: Optional[float] = None
    params: dict[str, object] = Field(default_factory=dict)
    results: dict[str, object] = Field(default_factory=dict)
    assigned_node: Optional[str] = None
    claimed_by: Optional[str] = None
    claimed_at: Optional[datetime] = None
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class TaskEvent(BaseModel):
    """Append-only event for jobs or tasks."""

    id: Optional[int] = None
    job_id: UUID
    job_task_id: Optional[UUID] = None
    ts: datetime
    source: str
    level: EventLevel
    type: EventType
    message: str
    data: dict[str, object] = Field(default_factory=dict)


class TaskArtifact(BaseModel):
    """References to artifacts produced by tasks."""

    id: Optional[int] = None
    job_id: UUID
    job_task_id: Optional[UUID] = None
    kind: ArtifactKind
    bucket: str
    key: str
    size_bytes: Optional[int] = None
    content_type: Optional[str] = None
    checksum: Optional[str] = None
    created_at: Optional[datetime] = None


class Node(BaseModel):
    """Service node participating in the workflow."""

    name: str
    labels: dict[str, object] = Field(default_factory=dict)
    last_seen: Optional[datetime] = None
    awake_state: AwakeState = AwakeState.UNKNOWN
    wake_method: Optional[WakeMethod] = None
    mac: Optional[str] = None
    provider_ref: Optional[str] = None
    script: Optional[str] = None
    max_concurrency: dict[str, int] = Field(default_factory=dict)


__all__ = [
    "WorkflowStep",
    "WorkflowDef",
    "JobStatus",
    "Job",
    "TaskStatus",
    "JobTask",
    "EventLevel",
    "EventType",
    "TaskEvent",
    "ArtifactKind",
    "TaskArtifact",
    "AwakeState",
    "WakeMethod",
    "Node",
]
