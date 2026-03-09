import uuid
from datetime import datetime
from pydantic import BaseModel, Field


# --- Request Schemas ---

class CreateTestCaseRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=500)
    description: str = Field(..., min_length=1)


# --- Response Schemas ---

class TestStepResponse(BaseModel):
    id: uuid.UUID
    order: int
    action: str
    selector: str | None
    value: str | None
    expected_result: str | None
    description: str | None

    model_config = {"from_attributes": True}


class TestCaseResponse(BaseModel):
    id: uuid.UUID
    suite_id: uuid.UUID
    title: str
    description: str
    status: str
    generation_attempts: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class TestCaseDetailResponse(TestCaseResponse):
    test_steps: list[TestStepResponse] = []
