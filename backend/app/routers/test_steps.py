from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from app.database import get_db
from app.models import TestStep, TestCase
from app.schemas import TestStepCreate, TestStepResponse, TestStepUpdate

router = APIRouter(prefix="/api/test-steps", tags=["Test Steps"])


@router.post("/", response_model=TestStepResponse, status_code=status.HTTP_201_CREATED)
def create_test_step(
    step: TestStepCreate,
    db: Session = Depends(get_db),
):
    """Create a new test step."""
    # Verify case exists
    case = db.query(TestCase).filter(TestCase.id == step.case_id).first()
    if not case:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Test case with id {step.case_id} not found",
        )
    
    # Convert ActionTypeEnum to ActionType enum
    from app.models.test_step import ActionType
    action_type = ActionType(step.action_type.value)
    
    db_step = TestStep(
        case_id=step.case_id,
        action_type=action_type,
        target_selector=step.target_selector,
        value=step.value,
        expected_result=step.expected_result,
        order=step.order,
        description=step.description,
    )
    db.add(db_step)
    db.commit()
    db.refresh(db_step)
    return db_step


@router.get("/", response_model=List[TestStepResponse])
def get_test_steps(
    case_id: int | None = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
):
    """Get test steps, optionally filtered by case."""
    query = db.query(TestStep)
    if case_id:
        query = query.filter(TestStep.case_id == case_id)
    
    steps = query.order_by(TestStep.order).offset(skip).limit(limit).all()
    return steps


@router.get("/{step_id}", response_model=TestStepResponse)
def get_test_step(
    step_id: int,
    db: Session = Depends(get_db),
):
    """Get a specific test step."""
    step = db.query(TestStep).filter(TestStep.id == step_id).first()
    if not step:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Test step with id {step_id} not found",
        )
    return step


@router.put("/{step_id}", response_model=TestStepResponse)
def update_test_step(
    step_id: int,
    step_update: TestStepUpdate,
    db: Session = Depends(get_db),
):
    """Update a test step."""
    step = db.query(TestStep).filter(TestStep.id == step_id).first()
    if not step:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Test step with id {step_id} not found",
        )
    
    update_data = step_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        if field == "action_type" and value:
            from app.models.test_step import ActionType
            value = ActionType(value.value)
        setattr(step, field, value)
    
    db.add(step)
    db.commit()
    db.refresh(step)
    return step


@router.delete("/{step_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_test_step(
    step_id: int,
    db: Session = Depends(get_db),
):
    """Delete a test step."""
    step = db.query(TestStep).filter(TestStep.id == step_id).first()
    if not step:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Test step with id {step_id} not found",
        )
    
    db.delete(step)
    db.commit()
    return None
