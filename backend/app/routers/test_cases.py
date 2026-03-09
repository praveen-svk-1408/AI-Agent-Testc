import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models.test_suite import TestSuite
from app.models.test_case import TestCase
from app.schemas.test_case import (
    CreateTestCaseRequest,
    TestCaseResponse,
    TestCaseDetailResponse,
)

router = APIRouter(tags=["Test Cases"])


@router.post(
    "/test-suites/{suite_id}/test-cases",
    response_model=TestCaseResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_test_case(
    suite_id: uuid.UUID,
    request: CreateTestCaseRequest,
    db: AsyncSession = Depends(get_db),
):
    # Verify suite exists
    suite_stmt = select(TestSuite).where(TestSuite.id == suite_id)
    suite_result = await db.execute(suite_stmt)
    if not suite_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Test suite not found")

    case = TestCase(suite_id=suite_id, **request.model_dump())
    db.add(case)
    await db.flush()
    await db.refresh(case)
    return case


@router.get(
    "/test-suites/{suite_id}/test-cases",
    response_model=list[TestCaseResponse],
)
async def list_test_cases(
    suite_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    stmt = (
        select(TestCase)
        .where(TestCase.suite_id == suite_id)
        .order_by(TestCase.created_at.desc())
    )
    result = await db.execute(stmt)
    return result.scalars().all()


@router.get(
    "/test-cases/{case_id}",
    response_model=TestCaseDetailResponse,
)
async def get_test_case(
    case_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    stmt = (
        select(TestCase)
        .where(TestCase.id == case_id)
        .options(selectinload(TestCase.test_steps))
    )
    result = await db.execute(stmt)
    case = result.scalar_one_or_none()
    if not case:
        raise HTTPException(status_code=404, detail="Test case not found")
    return case


@router.delete(
    "/test-cases/{case_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_test_case(
    case_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    stmt = select(TestCase).where(TestCase.id == case_id)
    result = await db.execute(stmt)
    case = result.scalar_one_or_none()
    if not case:
        raise HTTPException(status_code=404, detail="Test case not found")
    await db.delete(case)
