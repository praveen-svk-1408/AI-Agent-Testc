from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey, Enum, JSON, Float
from sqlalchemy.orm import relationship
from datetime import datetime
from enum import Enum as PyEnum
from app.database import Base


class ExecutionStatus(PyEnum):
    """Enum for test execution status."""
    PASSED = "passed"
    FAILED = "failed"
    ERROR = "error"
    RUNNING = "running"
    SKIPPED = "skipped"


class ExecutionResult(Base):
    """ORM model for test execution results."""
    __tablename__ = "execution_results"
    
    id = Column(Integer, primary_key=True, index=True)
    case_id = Column(Integer, ForeignKey("test_cases.id"), nullable=False)
    status = Column(Enum(ExecutionStatus), nullable=False)
    output = Column(Text, nullable=True)  # Logs and error messages
    screenshots_path = Column(JSON, nullable=True)  # Array of screenshot paths
    execution_time = Column(Float, nullable=True)  # Execution time in seconds
    step_results = Column(JSON, nullable=True)  # Step results and assertions (renamed from metadata)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationship
    test_case = relationship("TestCase", back_populates="execution_results")
    
    def __repr__(self):
        return f"<ExecutionResult(id={self.id}, case_id={self.case_id}, status='{self.status}')>"
