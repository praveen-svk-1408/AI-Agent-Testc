"""
Test Generation Service.

Orchestrates the LangGraph workflow, persists generated test steps to the database,
and generates Playwright test code files.
"""

import logging
import uuid

from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.models.test_case import TestCase
from app.models.test_step import TestStep
from app.models.test_suite import TestSuite
from app.agents.workflow import run_workflow
from app.schemas.agent import GeneratedTestStep
from app.services.test_output import generate_and_save_test_code
from app.services.playwright_config import save_playwright_config

logger = logging.getLogger(__name__)
settings = get_settings()


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
        # Choose between local workflow and remote AgentCore execution
        if settings.agentcore_enabled:
            workflow_state = await _run_via_agentcore(
                test_case=test_case,
                suite=suite,
                progress_callback=progress_callback,
            )
        else:
            # Run the LangGraph workflow locally
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


async def _run_via_agentcore(
    test_case: TestCase,
    suite: TestSuite,
    progress_callback=None,
) -> dict:
    """
    Run the test generation pipeline via a remote AgentCore agent.

    1. Load pre-crawled page snapshots locally (AgentCore has no browser)
    2. Enrich with MCP accessibility data
    3. POST snapshots + params to the AgentCore endpoint
    4. Return a dict that matches the local run_workflow() return shape
    """
    from app.services.site_crawl import load_crawl_snapshots
    from app.services.crawler import crawl_pages
    from app.services.mcp_browser import enrich_snapshots_with_mcp
    from app.services.agentcore_client import invoke_agentcore_agent
    from app.schemas.agent import GeneratedTestStep as GeneratedTestStepSchema

    suite_id = str(suite.id)

    if progress_callback:
        await progress_callback(["Starting AgentCore remote execution…"])

    # ── Step 1: Get page snapshots (cached or live crawl) ──
    snapshots = await load_crawl_snapshots(suite_id)

    if not snapshots:
        logger.info("No cached snapshots for suite %s — doing live crawl of base_url", suite_id)
        snapshots = await crawl_pages(
            suite.base_url,
            ["/"],
            login_url=suite.login_url,
            login_username=suite.login_username,
            login_password=suite.login_password,
        )

    # ── Step 2: MCP enrichment ──
    if settings.mcp_enrichment_enabled:
        snapshots = await enrich_snapshots_with_mcp(
            snapshots,
            login_url=suite.login_url,
            login_username=suite.login_username,
            login_password=suite.login_password,
        )

    if progress_callback:
        await progress_callback([f"Crawled {len(snapshots)} pages, invoking AgentCore agent…"])

    # ── Step 3: Invoke the remote AgentCore agent ──
    result = await invoke_agentcore_agent(
        title=test_case.title,
        description=test_case.description,
        base_url=suite.base_url,
        page_snapshots=snapshots,
        app_description=suite.app_description,
        test_type=test_case.test_type,
        login_url=suite.login_url,
        login_username=suite.login_username,
        login_password=suite.login_password,
        suite_name=suite.name,
    )

    # ── Step 4: Convert to local workflow state shape ──
    # The remote agent returns serialised dicts; reconstruct Pydantic objects
    final_steps = [
        GeneratedTestStepSchema.model_validate(s) for s in result.get("final_steps", [])
    ]

    return {
        "status": result.get("status", "failed"),
        "error": result.get("error"),
        "final_steps": final_steps,
        "generated_code": result.get("generated_code"),
        "code_file_name": result.get("code_file_name"),
        "progress_messages": result.get("progress_messages", []),
    }
