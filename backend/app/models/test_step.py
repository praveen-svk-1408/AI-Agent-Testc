from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey, Enum
from sqlalchemy.orm import relationship
from datetime import datetime
from enum import Enum as PyEnum
from app.database import Base


class ActionType(PyEnum):
    """Enum for test step actions."""
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


class TestStep(Base):
    """ORM model for individual test steps within a test case."""
    __tablename__ = "test_steps"
    
    id = Column(Integer, primary_key=True, index=True)
    case_id = Column(Integer, ForeignKey("test_cases.id"), nullable=False)
    action_type = Column(Enum(ActionType), nullable=False)
    target_selector = Column(String(512), nullable=True)  # CSS selector or XPath
    value = Column(Text, nullable=True)  # For fill, key_press, etc.
    expected_result = Column(Text, nullable=True)  # For assertions
    order = Column(Integer, nullable=False)  # Step sequence
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationship
    case = relationship("TestCase", back_populates="test_steps")
    
    def __repr__(self):
        return f"<TestStep(id={self.id}, case_id={self.case_id}, action='{self.action_type}', order={self.order})>"
