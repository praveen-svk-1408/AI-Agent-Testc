from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from app.database import get_db
from app.models import TestCase, TestSuite
from app.schemas import TestCaseCreate, TestCaseResponse, TestCaseDetailResponse, TestCaseUpdate

router = APIRouter(prefix="/api/test-cases", tags=["Test Cases"])


@router.post("/", response_model=TestCaseResponse, status_code=status.HTTP_201_CREATED)
def create_test_case(
    case: TestCaseCreate,
    db: Session = Depends(get_db),
):
    """Create a new test case."""
    # Verify suite exists
    suite = db.query(TestSuite).filter(TestSuite.id == case.suite_id).first()
    if not suite:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Test suite with id {case.suite_id} not found",
        )
    
    db_case = TestCase(
        suite_id=case.suite_id,
        path=case.path,
        name=case.name,
        description=case.description,
    )
    db.add(db_case)
    db.commit()
    db.refresh(db_case)
    return db_case


@router.get("/", response_model=List[TestCaseResponse])
def get_test_cases(
    suite_id: int | None = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
):
    """Get test cases, optionally filtered by suite."""
    query = db.query(TestCase)
    if suite_id:
        query = query.filter(TestCase.suite_id == suite_id)
    
    cases = query.offset(skip).limit(limit).all()
    return cases


@router.get("/{case_id}", response_model=TestCaseDetailResponse)
def get_test_case(
    case_id: int,
    db: Session = Depends(get_db),
):
    """Get a specific test case with all its steps and results."""
    case = db.query(TestCase).filter(TestCase.id == case_id).first()
    if not case:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Test case with id {case_id} not found",
        )
    return case


@router.put("/{case_id}", response_model=TestCaseResponse)
def update_test_case(
    case_id: int,
    case_update: TestCaseUpdate,
    db: Session = Depends(get_db),
):
    """Update a test case."""
    case = db.query(TestCase).filter(TestCase.id == case_id).first()
    if not case:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Test case with id {case_id} not found",
        )
    
    update_data = case_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(case, field, value)
    
    db.add(case)
    db.commit()
    db.refresh(case)
    return case


@router.delete("/{case_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_test_case(
    case_id: int,
    db: Session = Depends(get_db),
):
    """Delete a test case and all its steps."""
    case = db.query(TestCase).filter(TestCase.id == case_id).first()
    if not case:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Test case with id {case_id} not found",
        )
    
    db.delete(case)
    db.commit()
    return None
