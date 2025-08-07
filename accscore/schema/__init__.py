"""Pydantic models used across ACCS components."""

from enum import Enum
from typing import Optional

from pydantic import BaseModel


class JobStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"


class Job(BaseModel):
    id: str
    status: JobStatus
    result: Optional[str] = None
