from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from app.database import get_db
from app.models import TestSuite
from app.schemas import TestSuiteCreate, TestSuiteResponse, TestSuiteDetailResponse, TestSuiteUpdate

router = APIRouter(prefix="/api/test-suites", tags=["Test Suites"])


@router.post("/", response_model=TestSuiteResponse, status_code=status.HTTP_201_CREATED)
def create_test_suite(
    suite: TestSuiteCreate,
    db: Session = Depends(get_db),
):
    """Create a new test suite."""
    db_suite = TestSuite(
        name=suite.name,
        base_url=suite.base_url,
        description=suite.description,
    )
    db.add(db_suite)
    db.commit()
    db.refresh(db_suite)
    return db_suite


@router.get("/", response_model=List[TestSuiteResponse])
def get_test_suites(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
):
    """Get all test suites with pagination."""
    suites = db.query(TestSuite).offset(skip).limit(limit).all()
    return suites


@router.get("/{suite_id}", response_model=TestSuiteDetailResponse)
def get_test_suite(
    suite_id: int,
    db: Session = Depends(get_db),
):
    """Get a specific test suite with all its test cases."""
    suite = db.query(TestSuite).filter(TestSuite.id == suite_id).first()
    if not suite:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Test suite with id {suite_id} not found",
        )
    return suite


@router.put("/{suite_id}", response_model=TestSuiteResponse)
def update_test_suite(
    suite_id: int,
    suite_update: TestSuiteUpdate,
    db: Session = Depends(get_db),
):
    """Update a test suite."""
    suite = db.query(TestSuite).filter(TestSuite.id == suite_id).first()
    if not suite:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Test suite with id {suite_id} not found",
        )
    
    update_data = suite_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(suite, field, value)
    
    db.add(suite)
    db.commit()
    db.refresh(suite)
    return suite


@router.delete("/{suite_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_test_suite(
    suite_id: int,
    db: Session = Depends(get_db),
):
    """Delete a test suite and all its test cases."""
    suite = db.query(TestSuite).filter(TestSuite.id == suite_id).first()
    if not suite:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Test suite with id {suite_id} not found",
        )
    
    db.delete(suite)
    db.commit()
    return None
