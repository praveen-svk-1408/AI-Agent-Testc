from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database import Base


class TestCase(Base):
    """ORM model for individual test cases."""
    __tablename__ = "test_cases"
    
    id = Column(Integer, primary_key=True, index=True)
    suite_id = Column(Integer, ForeignKey("test_suites.id"), nullable=False)
    path = Column(String(512), nullable=False)  # e.g., /login, /products, /register
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    suite = relationship("TestSuite", back_populates="test_cases")
    test_steps = relationship("TestStep", back_populates="case", cascade="all, delete-orphan")
    execution_results = relationship("ExecutionResult", back_populates="test_case", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<TestCase(id={self.id}, path='{self.path}', name='{self.name}')>"
