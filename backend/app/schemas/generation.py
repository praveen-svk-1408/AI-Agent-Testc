from pydantic import BaseModel
from typing import Optional, List
from app.schemas.test_step import TestStepResponse


class GenerateTestsRequest(BaseModel):
    """Schema for test generation request."""
    suite_id: int
    target_url: str
    page_context: str  # Description of what the page does
    expected_behavior: str  # What test cases should verify
    additional_instructions: Optional[str] = None


class GenerateTestsResponse(BaseModel):
    """Schema for test generation response."""
    suite_id: int
    generated_test_cases: int
    test_cases: List[dict]  # List of generated test cases with steps
    message: str
