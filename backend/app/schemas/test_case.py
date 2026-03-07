from __future__ import annotations
from pydantic import BaseModel, ConfigDict
from typing import Optional, List, TYPE_CHECKING
from datetime import datetime

if TYPE_CHECKING:
    from app.schemas.test_step import TestStepResponse
    from app.schemas.execution_result import ExecutionResultResponse


class TestCaseBase(BaseModel):
    """Base schema for test case."""
    path: str
    name: str
    description: Optional[str] = None


class TestCaseCreate(TestCaseBase):
    """Schema for creating a test case."""
    suite_id: int


class TestCaseUpdate(BaseModel):
    """Schema for updating a test case."""
    path: Optional[str] = None
    name: Optional[str] = None
    description: Optional[str] = None


class TestCaseResponse(TestCaseBase):
    """Schema for test case response."""
    id: int
    suite_id: int
    created_at: datetime
    updated_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


class TestCaseDetailResponse(TestCaseResponse):
    """Detailed schema with test steps."""
    test_steps: List[TestStepResponse] = []
    execution_results: List[ExecutionResultResponse] = []


# Rebuild models to resolve forward references
from app.schemas.test_step import TestStepResponse
from app.schemas.execution_result import ExecutionResultResponse

TestCaseDetailResponse.model_rebuild()
