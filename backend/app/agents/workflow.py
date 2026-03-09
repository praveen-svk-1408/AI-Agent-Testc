"""
LangGraph Workflow — Plan-and-Execute Multi-Agent Orchestrator.

Pipeline:
  1. Orchestrator  (Plan)     — decompose NL requirement into sub-goals
  2. Page Crawler  (Execute)  — visit pages, extract DOM
  3. Step Generator (ReAct)   — convert goals into executable Playwright steps
  4. Step Reviewer             — validate / fix steps against real DOM (loop)
  5. Test Generator (IEEE 829) — produce structured test cases from reviewed steps
"""

import logging
from typing import TypedDict

from langgraph.graph import StateGraph, END

from app.config import get_settings
from app.schemas.agent import (
    StructuredTestIntent,
    PageSnapshot,
    GeneratedTestStep,
    TestDesignOutput,
    StepReviewResult,
)
from app.agents.requirement_analyzer import analyze_requirements
from app.agents.test_generator import generate_test_cases
from app.agents.step_generator import generate_steps, StepGeneratorOutput
from app.agents.reverifier import review_steps
from app.services.crawler import crawl_pages

logger = logging.getLogger(__name__)

settings = get_settings()


# ── Workflow State ────────────────────────────────────────────────────

class WorkflowState(TypedDict):
    """State passed between nodes in the workflow graph."""
    # Inputs
    title: str
    description: str
    base_url: str
    app_description: str | None
    test_type: str  # functional, e2e, integration, accessibility, visual, performance

    # After Orchestrator
    intent: StructuredTestIntent | None

    # After Crawler
    page_snapshots: list[PageSnapshot]

    # After Test Generator
    test_design: TestDesignOutput | None

    # After Step Generator
    steps: list[GeneratedTestStep]

    # After Step Reviewer
    review: StepReviewResult | None

    # Loop control
    iteration: int
    max_iterations: int

    # Output
    final_steps: list[GeneratedTestStep]
    status: str  # "running" | "success" | "failed"
    error: str | None
    progress_messages: list[str]


def _add_progress(state: WorkflowState, message: str) -> list[str]:
    """Append a progress message to state."""
    msgs = list(state.get("progress_messages", []))
    msgs.append(message)
    return msgs


def _ensure_step_order(steps: list[GeneratedTestStep]) -> list[GeneratedTestStep]:
    """Ensure every step has a non-null order assigned sequentially."""
    for i, step in enumerate(steps, start=1):
        if step.order is None:
            step.order = i
    return steps


# ── Node: 1 – Orchestrator ───────────────────────────────────────────

async def orchestrator_node(state: WorkflowState) -> dict:
    """Decompose the NL requirement into sub-goals, pages, and assertions."""
    logger.info("Workflow node: orchestrator (Plan)")
    try:
        intent = await analyze_requirements(
            title=state["title"],
            description=state["description"],
            base_url=state["base_url"],
            app_description=state.get("app_description"),
            test_type=state.get("test_type", "functional"),
        )
        return {
            "intent": intent,
            "status": "running",
            "progress_messages": _add_progress(
                state,
                f"Orchestrator: decomposed into {len(intent.goals)} goals, "
                f"{len(intent.pages)} pages, {len(intent.assertions)} assertions"
            ),
        }
    except Exception as e:
        logger.error("Orchestrator failed: %s", str(e))
        return {
            "status": "failed",
            "error": f"Orchestrator failed: {str(e)}",
            "progress_messages": _add_progress(state, f"Error: Orchestrator failed – {str(e)}"),
        }


# ── Node: 2 – Page Crawler ───────────────────────────────────────────

async def crawl_node(state: WorkflowState) -> dict:
    """Crawl target pages to extract DOM context."""
    logger.info("Workflow node: page_crawler")
    intent = state["intent"]
    if not intent:
        return {
            "status": "failed",
            "error": "No intent available for crawling",
            "progress_messages": _add_progress(state, "Error: No intent for crawling"),
        }

    pages_to_crawl = intent.pages if intent.pages else ["/"]

    try:
        snapshots = await crawl_pages(state["base_url"], pages_to_crawl)
        total_elements = sum(len(s.elements) for s in snapshots)
        return {
            "page_snapshots": snapshots,
            "status": "running",
            "progress_messages": _add_progress(
                state,
                f"Crawler: crawled {len(snapshots)} pages, {total_elements} interactive elements"
            ),
        }
    except Exception as e:
        logger.error("Page crawling failed: %s", str(e))
        return {
            "status": "failed",
            "error": f"Page crawling failed: {str(e)}",
            "progress_messages": _add_progress(state, f"Error: Crawling failed – {str(e)}"),
        }


# ── Node: 3 – Step Generator ─────────────────────────────────────────

async def step_generator_node(state: WorkflowState) -> dict:
    """Convert test intent goals into executable Playwright steps."""
    logger.info("Workflow node: step_generator (iteration %d)", state.get("iteration", 1))
    intent = state.get("intent")
    snapshots = state.get("page_snapshots", [])

    if not intent:
        return {
            "status": "failed",
            "error": "No intent available for step generation",
            "progress_messages": _add_progress(state, "Error: No intent for step gen"),
        }

    try:
        # Include feedback from previous Step Reviewer if retrying
        review = state.get("review")
        feedback = None
        if review and not review.approved:
            parts = list(review.issues_found)
            parts.extend(review.selector_fixes)
            feedback = "\n".join(parts) if parts else None

        result: StepGeneratorOutput = await generate_steps(
            intent, snapshots, feedback=feedback,
            test_type=state.get("test_type", "functional"),
        )
        return {
            "steps": result.steps,
            "status": "running",
            "progress_messages": _add_progress(
                state,
                f"StepGenerator: produced {len(result.steps)} Playwright steps "
                f"(confidence: {result.confidence:.0%})"
            ),
        }
    except Exception as e:
        logger.error("Step generation failed: %s", str(e))
        return {
            "status": "failed",
            "error": f"Step generation failed: {str(e)}",
            "progress_messages": _add_progress(state, f"Error: Step generation failed – {str(e)}"),
        }


# ── Node: 4 – Step Reviewer ──────────────────────────────────────────

async def step_reviewer_node(state: WorkflowState) -> dict:
    """Review steps against real DOM, fix hallucinated selectors."""
    logger.info("Workflow node: step_reviewer (iteration %d)", state.get("iteration", 1))
    steps = state.get("steps", [])
    snapshots = state.get("page_snapshots", [])

    if not steps:
        return {
            "status": "failed",
            "error": "No steps available for review",
            "progress_messages": _add_progress(state, "Error: No steps to review"),
        }

    try:
        review = await review_steps(steps, snapshots)
        iteration = state.get("iteration", 1)

        if review.approved:
            final = _ensure_step_order(review.fixed_steps if review.fixed_steps else steps)
            return {
                "review": review,
                "final_steps": final,
                "status": "reviewed",
                "progress_messages": _add_progress(
                    state,
                    f"StepReviewer: APPROVED (confidence: {review.confidence:.0%}, "
                    f"fixes: {len(review.selector_fixes)})"
                ),
            }
        else:
            new_iteration = iteration + 1
            issues_summary = "; ".join(review.issues_found[:3]) if review.issues_found else "needs improvement"
            return {
                "review": review,
                "iteration": new_iteration,
                "status": "running",
                "progress_messages": _add_progress(
                    state,
                    f"StepReviewer: REJECTED (attempt {iteration}): {issues_summary}"
                ),
            }
    except Exception as e:
        logger.error("Step review failed: %s", str(e))
        # On review error, accept the steps with a warning
        return {
            "review": None,
            "final_steps": _ensure_step_order(steps),
            "status": "reviewed",
            "error": f"Review skipped due to error: {str(e)}",
            "progress_messages": _add_progress(
                state,
                f"Warning: Step review skipped – {str(e)}. Accepting generated steps."
            ),
        }


# ── Conditional Edge ──────────────────────────────────────────────────

def should_retry(state: WorkflowState) -> str:
    """Decide whether to re-run the Step Generator, go to test generation, or finish."""
    if state.get("status") == "failed":
        return "end"
    if state.get("status") == "reviewed":
        return "generate_tests"

    iteration = state.get("iteration", 1)
    max_iter = state.get("max_iterations", settings.max_reverification_attempts)

    if iteration > max_iter:
        logger.info("Max iterations reached (%d), accepting current steps", max_iter)
        return "accept"

    return "retry"


async def accept_node(state: WorkflowState) -> dict:
    """Accept current steps after reaching max retry iterations."""
    steps = state.get("steps", [])
    review = state.get("review")

    # Use fixed steps from the last review if available
    if review and review.fixed_steps:
        steps = review.fixed_steps

    confidence = review.confidence if review else 0.5

    return {
        "final_steps": _ensure_step_order(steps),
        "status": "reviewed",
        "progress_messages": _add_progress(
            state,
            f"Accepted steps after max iterations (confidence: {confidence:.0%})"
        ),
    }


# ── Node: 5 – Test Generator (IEEE 829) ─────────────────────────────

async def test_generator_node(state: WorkflowState) -> dict:
    """Generate IEEE 829 test cases from the reviewed steps."""
    logger.info("Workflow node: test_generator (IEEE 829)")
    intent = state.get("intent")
    final_steps = state.get("final_steps", [])
    snapshots = state.get("page_snapshots", [])

    if not intent:
        return {
            "status": "failed",
            "error": "No intent available for test-case design",
            "progress_messages": _add_progress(state, "Error: No intent for test design"),
        }

    if not final_steps:
        return {
            "status": "failed",
            "error": "No reviewed steps available for test-case design",
            "progress_messages": _add_progress(state, "Error: No steps for test design"),
        }

    try:
        test_design = await generate_test_cases(intent, final_steps, snapshots)
        tc_ids = [tc.tc_id for tc in test_design.test_cases]
        return {
            "test_design": test_design,
            "status": "success",
            "progress_messages": _add_progress(
                state,
                f"TestGenerator: designed {len(test_design.test_cases)} IEEE 829 test cases "
                f"({', '.join(tc_ids)}) from {len(final_steps)} reviewed steps"
            ),
        }
    except Exception as e:
        logger.error("Test design failed: %s", str(e))
        # Even if test case generation fails, the steps are still valid — mark as success
        return {
            "test_design": None,
            "status": "success",
            "error": f"Test design failed (steps still valid): {str(e)}",
            "progress_messages": _add_progress(
                state,
                f"Warning: Test case design failed – {str(e)}. Reviewed steps are still available."
            ),
        }


# ── Graph Assembly ────────────────────────────────────────────────────

def build_workflow() -> StateGraph:
    """Build and compile the LangGraph workflow."""
    workflow = StateGraph(WorkflowState)

    # Add nodes
    workflow.add_node("orchestrator", orchestrator_node)
    workflow.add_node("crawl", crawl_node)
    workflow.add_node("step_generator", step_generator_node)
    workflow.add_node("step_reviewer", step_reviewer_node)
    workflow.add_node("accept", accept_node)
    workflow.add_node("test_generator", test_generator_node)

    # Linear flow: orchestrator → crawl → step_generator → step_reviewer
    workflow.set_entry_point("orchestrator")
    workflow.add_edge("orchestrator", "crawl")
    workflow.add_edge("crawl", "step_generator")
    workflow.add_edge("step_generator", "step_reviewer")

    # Conditional loop: step_reviewer → retry step_generator | accept | generate_tests | end
    workflow.add_conditional_edges(
        "step_reviewer",
        should_retry,
        {
            "retry": "step_generator",
            "accept": "accept",
            "generate_tests": "test_generator",
            "end": END,
        },
    )

    # After accept (max iterations), go to test_generator
    workflow.add_edge("accept", "test_generator")

    # test_generator is the final step
    workflow.add_edge("test_generator", END)

    return workflow.compile()


# Module-level compiled workflow
_compiled_workflow = None


def get_workflow():
    """Get or create the compiled workflow."""
    global _compiled_workflow
    if _compiled_workflow is None:
        _compiled_workflow = build_workflow()
    return _compiled_workflow


async def run_workflow(
    title: str,
    description: str,
    base_url: str,
    app_description: str | None = None,
    test_type: str = "functional",
    progress_callback=None,
) -> WorkflowState:
    """
    Run the complete Plan-and-Execute pipeline with real-time progress streaming.

    Pipeline: Orchestrator → Crawler → StepGenerator → StepReviewer → TestGenerator

    Returns the final workflow state with generated (and reviewed) steps.
    """
    workflow = get_workflow()

    initial_state: WorkflowState = {
        "title": title,
        "description": description,
        "base_url": base_url,
        "app_description": app_description,
        "test_type": test_type,
        "intent": None,
        "page_snapshots": [],
        "test_design": None,
        "steps": [],
        "review": None,
        "iteration": 1,
        "max_iterations": settings.max_reverification_attempts,
        "final_steps": [],
        "status": "running",
        "error": None,
        "progress_messages": ["Starting Plan-and-Execute pipeline…"],
    }

    logger.info("Starting workflow for test case: %s", title)

    if progress_callback:
        await progress_callback(initial_state["progress_messages"])

    # Stream node outputs so we can report progress after each step
    final_state = initial_state
    async for event in workflow.astream(initial_state):
        for node_name, node_output in event.items():
            if isinstance(node_output, dict):
                final_state = {**final_state, **node_output}
                if progress_callback and "progress_messages" in node_output:
                    await progress_callback(node_output["progress_messages"])

    logger.info("Workflow completed with status: %s", final_state.get("status"))
    return final_state