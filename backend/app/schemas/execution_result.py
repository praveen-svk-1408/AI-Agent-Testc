from pydantic import BaseModel, ConfigDict
from typing import Optional, List
from datetime import datetime
from enum import Enum


class ExecutionStatusEnum(str, Enum):
    """Enum for execution status."""
    PASSED = "passed"
    FAILED = "failed"
    ERROR = "error"
    RUNNING = "running"
    SKIPPED = "skipped"


class ExecutionResultBase(BaseModel):
    """Base schema for execution result."""
    status: ExecutionStatusEnum
    output: Optional[str] = None
    screenshots_path: Optional[List[str]] = None
    execution_time: Optional[float] = None
    step_results: Optional[dict] = None


class ExecutionResultCreate(ExecutionResultBase):
    """Schema for creating an execution result."""
    case_id: int


class ExecutionResultResponse(ExecutionResultBase):
    """Schema for execution result response."""
    id: int
    case_id: int
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)
