"""
Test Generation Service.

Orchestrates the LangGraph workflow (or AgentCore Runtime invocation),
persists generated test steps to the database, and generates Playwright test code files.
"""

import json
import logging
import uuid

from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.test_case import TestCase
from app.models.test_step import TestStep
from app.models.test_suite import TestSuite
from app.agents.workflow import run_workflow
from app.schemas.agent import GeneratedTestStep
from app.services.test_output import generate_and_save_test_code
from app.services.playwright_config import save_playwright_config
from app.config import get_settings

logger = logging.getLogger(__name__)

settings = get_settings()


async def _invoke_agentcore(
    title: str,
    description: str,
    base_url: str,
    app_description: str | None,
    test_type: str,
    login_url: str | None,
    login_username: str | None,
    login_password: str | None,
    suite_id: str | None,
    suite_name: str | None,
    progress_callback=None,
) -> dict:
    """Invoke the AgentCore Runtime deployed agent via boto3.

    Returns a dict compatible with the LangGraph workflow state.
    """
    import boto3

    client = boto3.client(
        "bedrock-agentcore-runtime",
        region_name=settings.agentcore_region,
        aws_access_key_id=settings.aws_access_key_id or None,
        aws_secret_access_key=settings.aws_secret_access_key or None,
    )

    payload = {
        "title": title,
        "description": description,
        "base_url": base_url,
        "app_description": app_description,
        "test_type": test_type,
        "login_url": login_url,
        "login_username": login_username,
        "login_password": login_password,
        "suite_id": suite_id,
        "suite_name": suite_name,
    }

    response = client.invoke_agent(
        agentArn=settings.agentcore_agent_arn,
        inputText=json.dumps(payload),
    )

    # Process streaming response
    final_result = None
    progress_messages = []

    for event in response.get("completion", []):
        if "chunk" in event:
            chunk_data = json.loads(event["chunk"]["bytes"].decode("utf-8"))
            if chunk_data.get("type") == "progress":
                progress_messages.append(chunk_data["message"])
                if progress_callback:
                    await progress_callback([chunk_data["message"]])
            elif chunk_data.get("type") == "result":
                final_result = chunk_data

    if not final_result:
        return {
            "status": "failed",
            "error": "No result received from AgentCore",
            "progress_messages": progress_messages,
        }

    # Convert AgentCore result to workflow-compatible dict
    final_steps = [
        GeneratedTestStep(**s) for s in final_result.get("final_steps", [])
    ]

    return {
        "status": final_result.get("status", "success"),
        "error": final_result.get("error"),
        "progress_messages": progress_messages,
        "final_steps": final_steps,
        "generated_code": final_result.get("generated_code"),
        "code_file_name": final_result.get("code_file_name"),
    }


async def generate_test_case_steps(
    case_id: uuid.UUID,
    db: AsyncSession,
    progress_callback=None,
) -> dict:
    """
    Run the full generation workflow for a test case:
    1. Fetch the test case and its suite from DB
    2. Run the LangGraph workflow (analyze → crawl → generate → verify)
    3. Store generated TestSteps in DB
    4. Update test case status

    Args:
        progress_callback: Optional async callable(progress_messages) for real-time updates.

    Returns a dict with status info and generated steps.
    """
    # Fetch test case with suite
    stmt = (
        select(TestCase)
        .where(TestCase.id == case_id)
    )
    result = await db.execute(stmt)
    test_case = result.scalar_one_or_none()

    if not test_case:
        raise ValueError(f"Test case not found: {case_id}")

    # Fetch the parent suite
    suite_stmt = select(TestSuite).where(TestSuite.id == test_case.suite_id)
    suite_result = await db.execute(suite_stmt)
    suite = suite_result.scalar_one_or_none()

    if not suite:
        raise ValueError(f"Test suite not found for case: {case_id}")

    logger.info("Starting generation for case '%s' in suite '%s'",
                test_case.title, suite.name)

    try:
        # Choose execution path: AgentCore Runtime or local LangGraph
        if settings.agentcore_enabled and settings.agentcore_agent_arn:
            logger.info("Using AgentCore Runtime for generation")
            workflow_state = await _invoke_agentcore(
                title=test_case.title,
                description=test_case.description,
                base_url=suite.base_url,
                app_description=suite.app_description,
                test_type=test_case.test_type,
                login_url=suite.login_url,
                login_username=suite.login_username,
                login_password=suite.login_password,
                suite_id=str(suite.id),
                suite_name=suite.name,
                progress_callback=progress_callback,
            )
        else:
            # Run the LangGraph workflow (local)
            workflow_state = await run_workflow(
                title=test_case.title,
                description=test_case.description,
                base_url=suite.base_url,
                app_description=suite.app_description,
                test_type=test_case.test_type,
                login_url=suite.login_url,
                login_username=suite.login_username,
                login_password=suite.login_password,
                suite_id=str(suite.id),
                suite_name=suite.name,
                progress_callback=progress_callback,
            )

        if workflow_state["status"] == "failed":
            test_case.status = "failed"
            await db.flush()
            return {
                "status": "failed",
                "error": workflow_state.get("error", "Unknown error"),
                "progress": workflow_state.get("progress_messages", []),
            }

        # Clear existing steps for this case (re-generation)
        await db.execute(
            delete(TestStep).where(TestStep.case_id == case_id)
        )

        # Persist the generated steps
        final_steps: list[GeneratedTestStep] = workflow_state.get("final_steps", [])
        db_steps = []
        for i, step in enumerate(final_steps, start=1):
            db_step = TestStep(
                case_id=case_id,
                order=step.order if step.order is not None else i,
                action=step.action,
                selector=step.selector,
                value=step.value,
                expected_result=step.expected_result,
                description=step.description,
            )
            db.add(db_step)
            db_steps.append(db_step)

        # Update case status
        test_case.status = "generated"
        await db.flush()

        logger.info("Generation complete: %d steps saved for case %s",
                    len(db_steps), case_id)

        # Phase 3: Use inline-generated code from QA Code Generator node, or fall back
        code_result = None
        try:
            inline_code = workflow_state.get("generated_code")
            inline_file = workflow_state.get("code_file_name")

            if inline_code and inline_file:
                # Code was already written to disk by the QA Code Generator node
                logger.info("Test code already generated inline by QACodeGenerator: %s", inline_file)
                code_result = {"file_name": inline_file, "inline": True}
            else:
                # Fallback: generate code from DB steps (legacy path)
                code_result = await generate_and_save_test_code(case_id, db)
                logger.info("Test code generated (fallback): %s", code_result.get("file_name"))

            # Generate/update playwright.config.ts for this suite
            save_playwright_config(
                suite_id=str(suite.id),
                base_url=suite.base_url,
            )
        except Exception as code_err:
            logger.warning(
                "Test code generation failed (steps still saved): %s",
                str(code_err),
            )

        return {
            "status": "success",
            "steps_count": len(db_steps),
            "progress": workflow_state.get("progress_messages", []),
            "error": workflow_state.get("error"),
            "code_generated": code_result is not None,
            "code_file": code_result.get("file_name") if code_result else None,
        }

    except Exception as e:
        logger.error("Generation failed for case %s: %s", case_id, str(e))
        test_case.status = "failed"
        await db.flush()
        return {
            "status": "failed",
            "error": str(e),
            "progress": [f"Generation failed: {str(e)}"],
        }
