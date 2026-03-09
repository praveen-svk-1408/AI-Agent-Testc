import uuid
from datetime import datetime
from pydantic import BaseModel, Field


# --- Request Schemas ---

class CreateTestSuiteRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: str | None = None
    base_url: str = Field(..., min_length=1, max_length=2048)
    app_description: str | None = None


class UpdateTestSuiteRequest(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=255)
    description: str | None = None
    base_url: str | None = Field(None, min_length=1, max_length=2048)
    app_description: str | None = None


# --- Response Schemas ---

class TestSuiteResponse(BaseModel):
    id: uuid.UUID
    name: str
    description: str | None
    base_url: str
    app_description: str | None
    created_at: datetime
    updated_at: datetime
    test_case_count: int = 0

    model_config = {"from_attributes": True}


class TestSuiteDetailResponse(TestSuiteResponse):
    test_cases: list["TestCaseResponse"] = []


# Forward reference resolved below
from app.schemas.test_case import TestCaseResponse  # noqa: E402

TestSuiteDetailResponse.model_rebuild()
