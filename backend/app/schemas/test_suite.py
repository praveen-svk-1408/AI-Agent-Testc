from __future__ import annotations
from pydantic import BaseModel, ConfigDict
from typing import Optional, List, TYPE_CHECKING
from datetime import datetime

if TYPE_CHECKING:
    from app.schemas.test_case import TestCaseResponse


class TestSuiteBase(BaseModel):
    """Base schema for test suite."""
    name: str
    base_url: str
    description: Optional[str] = None


class TestSuiteCreate(TestSuiteBase):
    """Schema for creating a test suite."""
    pass


class TestSuiteUpdate(BaseModel):
    """Schema for updating a test suite."""
    name: Optional[str] = None
    base_url: Optional[str] = None
    description: Optional[str] = None


class TestSuiteResponse(TestSuiteBase):
    """Schema for test suite response."""
    id: int
    created_at: datetime
    updated_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


class TestSuiteDetailResponse(TestSuiteResponse):
    """Detailed schema with test cases."""
    test_cases: List[TestCaseResponse] = []


# Rebuild models to resolve forward references
from app.schemas.test_case import TestCaseResponse

TestSuiteDetailResponse.model_rebuild()
