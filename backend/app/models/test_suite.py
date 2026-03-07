from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database import Base


class TestSuite(Base):
    """ORM model for test suites."""
    __tablename__ = "test_suites"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    base_url = Column(String(512), nullable=False)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationship
    test_cases = relationship("TestCase", back_populates="suite", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<TestSuite(id={self.id}, name='{self.name}', base_url='{self.base_url}')>"
