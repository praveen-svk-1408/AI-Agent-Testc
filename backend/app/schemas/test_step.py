from pydantic import BaseModel, ConfigDict
from typing import Optional
from datetime import datetime
from enum import Enum


class ActionTypeEnum(str, Enum):
    """Enum for test step action types."""
    NAVIGATE = "navigate"
    CLICK = "click"
    FILL = "fill"
    ASSERT = "assert"
    SCREENSHOT = "screenshot"
    WAIT = "wait"
    SELECT = "select"
    HOVER = "hover"
    KEY_PRESS = "key_press"
    SCROLL = "scroll"


class TestStepBase(BaseModel):
    """Base schema for test step."""
    action_type: ActionTypeEnum
    target_selector: Optional[str] = None
    value: Optional[str] = None
    expected_result: Optional[str] = None
    order: int
    description: Optional[str] = None


class TestStepCreate(TestStepBase):
    """Schema for creating a test step."""
    case_id: int


class TestStepUpdate(BaseModel):
    """Schema for updating a test step."""
    action_type: Optional[ActionTypeEnum] = None
    target_selector: Optional[str] = None
    value: Optional[str] = None
    expected_result: Optional[str] = None
    order: Optional[int] = None
    description: Optional[str] = None


class TestStepResponse(TestStepBase):
    """Schema for test step response."""
    id: int
    case_id: int
    created_at: datetime
    updated_at: datetime
    
    model_config = ConfigDict(from_attributes=True)
