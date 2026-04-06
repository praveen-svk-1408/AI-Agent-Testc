"""
LangGraph Workflow — 7-Agent TDD Pipeline (AgentCore Version).

Stateless version of the pipeline for deployment on AWS Bedrock AgentCore Runtime.
Key differences from the backend version:
  - No filesystem I/O (no writing .spec.ts files to disk)
  - No database operations
  - No Playwright crawler — accepts pre-crawled page_snapshots as input
  - No MCP enrichment — snapshots must be pre-enriched by the caller
  - Returns all results in-memory via the final WorkflowState

Pipeline:
  1. Planner         — decompose NL requirement into intent + strategic test plan
  2. Validate Snapshots — verify pre-crawled snapshots are provided
  3. DOM Analyst     — identify semantic UI groups, stable selectors, nav patterns
  4. Test Generator  — produce IEEE 829 test cases from plan + DOM (BEFORE steps)
  5. Test Case Reviewer — validate coverage & feasibility (Loop A)
  6. Step Generator  — convert approved test cases + DOM into executable Playwright steps
  7. Step Reviewer   — validate/fix steps against real DOM (Loop B)
  8. QA Code Generator — produce final TypeScript .spec.ts code (in-memory only)
"""

import logging
from typing import TypedDict

from langgraph.graph import StateGraph, END

from config import get_settings
from schemas.agent import (
    StructuredTestIntent,
    PageSnapshot,
    GeneratedTestStep,
    TestDesignOutput,
    StepReviewResult,
    TestPlan,
    DOMAnalysis,
    TestCaseReviewResult,
    IEEE829TestCase,
)
from agents.requirement_analyzer import plan_and_analyze
from agents.dom_analyst import analyze_dom
from agents.test_generator import generate_test_cases
from agents.test_case_reviewer import review_test_cases
from agents.step_generator import generate_steps, StepGeneratorOutput
from agents.reverifier import review_steps
from agents.code_generator import generate_test_suite_code

logger = logging.getLogger(__name__)

settings = get_settings()


# ── Workflow State ────────────────────────────────────────────────────

class WorkflowState(TypedDict):
    """State passed between nodes in the 7-agent TDD workflow."""
    # ── Inputs
    title: str
    description: str
    base_url: str
    app_description: str | None
    test_type: str

    # ── Authentication (optional)
    login_url: str | None
    login_username: str | None
    login_password: str | None

    # ── Suite metadata (for naming output files)
    suite_name: str | None

    # ── After Planner (node 1)
    intent: StructuredTestIntent | None
    plan: TestPlan | None

    # ── After DOM Analyst (node 3)
    dom_analysis: DOMAnalysis | None

    # ── Pre-crawled snapshots (provided as input)
    page_snapshots: list[PageSnapshot]

    # ── After Test Generator (node 4)
    test_design: TestDesignOutput | None

    # ── After Test Case Reviewer — Loop A (node 5)
    test_case_review: TestCaseReviewResult | None
    tc_iteration: int
    max_tc_iterations: int

    # ── After Step Generator (node 6)
    steps: list[GeneratedTestStep]

    # ── After Step Reviewer — Loop B (node 7)
    review: StepReviewResult | None
    iteration: int
    max_iterations: int

    # ── Final outputs
    final_steps: list[GeneratedTestStep]
    generated_code: str | None
    code_file_name: str | None
    status: str
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
    """Decompose the NL requirement into sub-goals + strategic test plan."""
    logger.info("Workflow node: planner")
    try:
        output = await plan_and_analyze(
            title=state["title"],
            description=state["description"],
            base_url=state["base_url"],
            app_description=state.get("app_description"),
            test_type=state.get("test_type", "functional"),
        )
        intent = output.intent
        plan = output.plan
        return {
            "intent": intent,
            "plan": plan,
            "status": "running",
            "progress_messages": _add_progress(
                state,
                f"Planner: {len(intent.goals)} goals, {len(intent.pages)} pages, "
                f"{len(intent.assertions)} assertions | "
                f"{len(plan.scenarios)} test scenarios (strategy: {plan.strategy[:60]})"
            ),
        }
    except Exception as e:
        logger.error("Planner failed: %s", str(e))
        return {
            "status": "failed",
            "error": f"Planner failed: {str(e)}",
            "progress_messages": _add_progress(state, f"Error: Planner failed – {str(e)}"),
        }


# ── Node: 2 – Validate Snapshots (replaces crawler) ─────────────────

async def validate_snapshots_node(state: WorkflowState) -> dict:
    """Validate that pre-crawled page snapshots were provided as input.

    AgentCore Runtime is stateless — no browser binary is available.
    The caller (FastAPI backend) must crawl pages and pass snapshots in the request.
    """
    logger.info("Workflow node: validate_snapshots")
    snapshots = state.get("page_snapshots", [])

    if not snapshots:
        return {
            "status": "failed",
            "error": "No page_snapshots provided. The caller must pre-crawl pages before invoking the agent.",
            "progress_messages": _add_progress(
                state, "Error: No pre-crawled snapshots provided"
            ),
        }

    total_elements = sum(len(s.elements) for s in snapshots)
    logger.info(
        "validate_snapshots_node: %d pre-crawled snapshots, %d elements",
        len(snapshots), total_elements,
    )
    return {
        "status": "running",
        "progress_messages": _add_progress(
            state,
            f"Snapshots: validated {len(snapshots)} pre-crawled pages, "
            f"{total_elements} interactive elements"
        ),
    }


# ── Node: 3 – DOM Analyst ────────────────────────────────────────────

async def dom_analyst_node(state: WorkflowState) -> dict:
    """Analyse page snapshots to identify semantic UI groups and stable selectors."""
    logger.info("Workflow node: dom_analyst")
    snapshots = state.get("page_snapshots", [])
    plan = state.get("plan")

    if not plan:
        plan = TestPlan(
            strategy="General web application testing",
            scenarios=[
                g for g in (state["intent"].goals if state.get("intent") else ["Test the application"])
            ],
        )

    try:
        dom_analysis = await analyze_dom(
            snapshots=snapshots,
            plan=plan,
            test_type=state.get("test_type", "functional"),
        )
        return {
            "dom_analysis": dom_analysis,
            "status": "running",
            "progress_messages": _add_progress(
                state,
                f"DOMAnalyst: {len(dom_analysis.semantic_groups)} semantic groups, "
                f"{len(dom_analysis.critical_selectors)} critical selectors, "
                f"{len(dom_analysis.accessibility_issues)} accessibility issues"
            ),
        }
    except Exception as e:
        logger.warning("DOM analysis failed (%s) — continuing with empty analysis", str(e))
        return {
            "dom_analysis": DOMAnalysis(),
            "status": "running",
            "progress_messages": _add_progress(
                state, f"Warning: DOM analysis skipped – {str(e)}"
            ),
        }


# ── Node: 4 – Test Generator (IEEE 829, TDD order) ───────────────────

async def test_generator_node(state: WorkflowState) -> dict:
    """Design IEEE 829 test cases from plan + DOM (TDD order — before step generation)."""
    logger.info("Workflow node: test_generator (tc_iteration %d)", state.get("tc_iteration", 1))
    intent = state.get("intent")
    plan = state.get("plan")
    dom_analysis = state.get("dom_analysis")

    if not intent or not plan:
        return {
            "status": "failed",
            "error": "No intent/plan available for test-case design",
            "progress_messages": _add_progress(state, "Error: No intent/plan for test design"),
        }

    effective_dom = dom_analysis if dom_analysis is not None else DOMAnalysis()

    try:
        test_design = await generate_test_cases(
            plan=plan,
            dom_analysis=effective_dom,
            intent=intent,
            test_type=state.get("test_type", "functional"),
        )
        tc_ids = [tc.tc_id for tc in test_design.test_cases]
        return {
            "test_design": test_design,
            "status": "running",
            "progress_messages": _add_progress(
                state,
                f"TestGenerator: designed {len(test_design.test_cases)} IEEE 829 test cases "
                f"({', '.join(tc_ids)}) from {len(plan.scenarios)} plan scenarios"
            ),
        }
    except Exception as e:
        logger.error("Test design failed: %s", str(e))
        return {
            "status": "failed",
            "error": f"Test case design failed: {str(e)}",
            "progress_messages": _add_progress(state, f"Error: Test case design failed – {str(e)}"),
        }


# ── Node: 5 – Test Case Reviewer (Loop A) ────────────────────────────

async def test_case_reviewer_node(state: WorkflowState) -> dict:
    """Review test cases for plan coverage and DOM feasibility (Loop A)."""
    logger.info("Workflow node: test_case_reviewer (tc_iteration %d)", state.get("tc_iteration", 1))
    test_design = state.get("test_design")
    plan = state.get("plan")
    dom_analysis = state.get("dom_analysis")

    if not test_design or not plan:
        return {
            "status": "failed",
            "error": "No test design or plan available for review",
            "progress_messages": _add_progress(state, "Error: No test design/plan for review"),
        }

    effective_dom = dom_analysis if dom_analysis is not None else DOMAnalysis()

    try:
        review = await review_test_cases(
            test_design=test_design,
            plan=plan,
            dom_analysis=effective_dom,
            test_type=state.get("test_type", "functional"),
        )
        tc_iteration = state.get("tc_iteration", 1)

        if review.approved:
            return {
                "test_case_review": review,
                "status": "tc_reviewed",
                "progress_messages": _add_progress(
                    state,
                    f"TestCaseReviewer: APPROVED (confidence: {review.confidence:.0%}, "
                    f"{len(review.approved_cases)} cases, 0 coverage gaps)"
                ),
            }
        else:
            gaps = "; ".join(review.coverage_gaps[:3]) if review.coverage_gaps else ""
            issues = "; ".join(review.feedback[:2]) if review.feedback else "needs improvement"
            return {
                "test_case_review": review,
                "tc_iteration": tc_iteration + 1,
                "status": "running",
                "progress_messages": _add_progress(
                    state,
                    f"TestCaseReviewer: REJECTED (attempt {tc_iteration}): "
                    f"gaps=[{gaps}] issues=[{issues}]"
                ),
            }
    except Exception as e:
        logger.error("Test case review failed: %s", str(e))
        fallback_review = TestCaseReviewResult(
            approved=True,
            feedback=[f"Review skipped: {str(e)}"],
            coverage_gaps=[],
            approved_cases=test_design.test_cases,
            confidence=0.5,
        )
        return {
            "test_case_review": fallback_review,
            "status": "tc_reviewed",
            "progress_messages": _add_progress(
                state,
                f"Warning: Test case review skipped – {str(e)}. Accepting generated cases."
            ),
        }


def tc_should_retry(state: WorkflowState) -> str:
    """Decide whether to retry test generation, proceed to step gen, or fail."""
    if state.get("status") == "failed":
        return "tc_failed"
    if state.get("status") == "tc_reviewed":
        return "proceed"

    tc_iteration = state.get("tc_iteration", 1)
    max_tc_iter = state.get("max_tc_iterations", 2)

    if tc_iteration > max_tc_iter:
        logger.info("TC review max iterations reached (%d), accepting test cases", max_tc_iter)
        return "tc_accept"

    return "tc_retry"


async def tc_accept_node(state: WorkflowState) -> dict:
    """Force-accept test cases after reaching max review iterations."""
    test_design = state.get("test_design")
    cases = test_design.test_cases if test_design else []
    tc_review = state.get("test_case_review")
    effective_cases = tc_review.approved_cases if tc_review and tc_review.approved_cases else cases
    confidence = tc_review.confidence if tc_review else 0.5

    final_review = TestCaseReviewResult(
        approved=True,
        feedback=["Accepted after max TC review iterations"],
        coverage_gaps=[],
        approved_cases=effective_cases,
        confidence=confidence,
    )
    return {
        "test_case_review": final_review,
        "status": "tc_reviewed",
        "progress_messages": _add_progress(
            state,
            f"Accepted {len(effective_cases)} test cases after max iterations "
            f"(confidence: {confidence:.0%})"
        ),
    }


# ── Node: 6 – Step Generator ───────────────────────────────────────────

async def step_generator_node(state: WorkflowState) -> dict:
    """Convert approved test cases + DOM into executable Playwright steps."""
    logger.info("Workflow node: step_generator (iteration %d)", state.get("iteration", 1))
    intent = state.get("intent")
    snapshots = state.get("page_snapshots", [])

    if not intent:
        return {
            "status": "failed",
            "error": "No intent available for step generation",
            "progress_messages": _add_progress(state, "Error: No intent for step gen"),
        }

    tc_review = state.get("test_case_review")
    test_design = state.get("test_design")
    approved_cases: list[IEEE829TestCase] | None = None
    if tc_review and tc_review.approved_cases:
        approved_cases = tc_review.approved_cases
    elif test_design:
        approved_cases = test_design.test_cases

    review = state.get("review")
    feedback = None
    if review and not review.approved:
        parts = list(review.issues_found)
        parts.extend(review.selector_fixes)
        feedback = "\n".join(parts) if parts else None

    try:
        result: StepGeneratorOutput = await generate_steps(
            intent=intent,
            snapshots=snapshots,
            feedback=feedback,
            test_type=state.get("test_type", "functional"),
            approved_test_cases=approved_cases,
            login_username=state.get("login_username"),
            login_password=state.get("login_password"),
        )
        return {
            "steps": result.steps,
            "status": "running",
            "progress_messages": _add_progress(
                state,
                f"StepGenerator: produced {len(result.steps)} Playwright steps "
                f"({len(approved_cases or [])} test cases, confidence: {result.confidence:.0%})"
            ),
        }
    except Exception as e:
        logger.error("Step generation failed: %s", str(e))
        return {
            "status": "failed",
            "error": f"Step generation failed: {str(e)}",
            "progress_messages": _add_progress(state, f"Error: Step generation failed – {str(e)}"),
        }


# ── Node: 7 – Step Reviewer (Loop B) ───────────────────────────────────

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
        review = await review_steps(steps, snapshots, test_type=state.get("test_type", "functional"))
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
            issues_summary = "; ".join(review.issues_found[:3]) if review.issues_found else "needs improvement"
            return {
                "review": review,
                "iteration": iteration + 1,
                "status": "running",
                "progress_messages": _add_progress(
                    state,
                    f"StepReviewer: REJECTED (attempt {iteration}): {issues_summary}"
                ),
            }
    except Exception as e:
        logger.error("Step review failed: %s", str(e))
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


def should_retry(state: WorkflowState) -> str:
    """Decide whether to retry Step Generator, proceed to code gen, or end."""
    if state.get("status") == "failed":
        return "end"
    if state.get("status") == "reviewed":
        return "generate_code"

    iteration = state.get("iteration", 1)
    max_iter = state.get("max_iterations", settings.max_reverification_attempts)

    if iteration > max_iter:
        logger.info("Max step iterations reached (%d), accepting steps", max_iter)
        return "accept"

    return "retry"


async def step_accept_node(state: WorkflowState) -> dict:
    """Force-accept steps after reaching max Step Reviewer iterations."""
    steps = state.get("steps", [])
    review = state.get("review")
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


# ── Node: 8 – QA Code Generator (in-memory only) ───────────────────────

async def qa_code_generator_node(state: WorkflowState) -> dict:
    """Generate executable Playwright TypeScript code — returns in-memory, no file I/O."""
    logger.info("Workflow node: qa_code_generator")
    final_steps = state.get("final_steps", [])
    test_design = state.get("test_design")
    tc_review = state.get("test_case_review")

    test_cases: list[IEEE829TestCase] = []
    if tc_review and tc_review.approved_cases:
        test_cases = tc_review.approved_cases
    elif test_design:
        test_cases = test_design.test_cases

    try:
        generated = await generate_test_suite_code(
            test_cases=test_cases,
            steps=final_steps,
            suite_name=state.get("suite_name") or state["title"],
            base_url=state["base_url"],
            test_type=state.get("test_type", "functional"),
        )

        # No file I/O in AgentCore — code returned in-memory
        return {
            "generated_code": generated.code_content,
            "code_file_name": generated.file_name,
            "status": "success",
            "progress_messages": _add_progress(
                state,
                f"QACodeGenerator: generated '{generated.file_name}' "
                f"({len(test_cases)} test cases, {len(final_steps)} steps)"
            ),
        }
    except Exception as e:
        logger.error("QA code generation failed: %s", str(e))
        return {
            "status": "success",
            "error": f"Code generation failed (steps still valid): {str(e)}",
            "progress_messages": _add_progress(
                state,
                f"Warning: QA code generation failed – {str(e)}. Steps available."
            ),
        }


def build_workflow() -> StateGraph:
    """Build and compile the 7-agent TDD workflow graph (AgentCore version)."""
    workflow = StateGraph(WorkflowState)

    # ── Register nodes
    workflow.add_node("orchestrator", orchestrator_node)
    workflow.add_node("validate_snapshots", validate_snapshots_node)
    workflow.add_node("dom_analyst", dom_analyst_node)
    workflow.add_node("test_generator", test_generator_node)
    workflow.add_node("test_case_reviewer", test_case_reviewer_node)
    workflow.add_node("tc_accept", tc_accept_node)
    workflow.add_node("step_generator", step_generator_node)
    workflow.add_node("step_reviewer", step_reviewer_node)
    workflow.add_node("step_accept", step_accept_node)
    workflow.add_node("qa_code_generator", qa_code_generator_node)

    # ── Linear spine
    workflow.set_entry_point("orchestrator")
    workflow.add_edge("orchestrator", "validate_snapshots")
    workflow.add_edge("validate_snapshots", "dom_analyst")
    workflow.add_edge("dom_analyst", "test_generator")
    workflow.add_edge("test_generator", "test_case_reviewer")

    # ── Loop A: test_case_reviewer → retry | accept | proceed | fail
    workflow.add_conditional_edges(
        "test_case_reviewer",
        tc_should_retry,
        {
            "tc_retry":  "test_generator",
            "tc_accept": "tc_accept",
            "proceed":   "step_generator",
            "tc_failed": END,
        },
    )
    workflow.add_edge("tc_accept", "step_generator")

    # ── Step generator → step reviewer
    workflow.add_edge("step_generator", "step_reviewer")

    # ── Loop B: step_reviewer → retry | accept | generate code | fail
    workflow.add_conditional_edges(
        "step_reviewer",
        should_retry,
        {
            "retry":         "step_generator",
            "accept":        "step_accept",
            "generate_code": "qa_code_generator",
            "end":           END,
        },
    )
    workflow.add_edge("step_accept", "qa_code_generator")

    # ── Final node
    workflow.add_edge("qa_code_generator", END)

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
    page_snapshots: list[dict],
    app_description: str | None = None,
    test_type: str = "functional",
    login_url: str | None = None,
    login_username: str | None = None,
    login_password: str | None = None,
    suite_name: str | None = None,
) -> dict:
    """
    Run the complete 7-agent TDD pipeline (AgentCore version).

    Key difference: page_snapshots MUST be provided — no live crawling.

    Returns a dict with:
      - status: "success" | "failed"
      - final_steps: list of GeneratedTestStep dicts
      - test_cases: list of IEEE829TestCase dicts
      - generated_code: str (TypeScript .spec.ts content)
      - code_file_name: str
      - progress_messages: list of str
      - error: str | None
    """
    workflow = get_workflow()

    # Convert raw snapshot dicts to PageSnapshot objects
    snapshots = [PageSnapshot.model_validate(s) for s in page_snapshots]

    initial_state: WorkflowState = {
        "title": title,
        "description": description,
        "base_url": base_url,
        "app_description": app_description,
        "test_type": test_type,
        "login_url": login_url,
        "login_username": login_username,
        "login_password": login_password,
        "suite_name": suite_name,
        "intent": None,
        "plan": None,
        "dom_analysis": None,
        "page_snapshots": snapshots,
        "test_design": None,
        "test_case_review": None,
        "tc_iteration": 1,
        "max_tc_iterations": 2,
        "steps": [],
        "review": None,
        "iteration": 1,
        "max_iterations": settings.max_reverification_attempts,
        "final_steps": [],
        "generated_code": None,
        "code_file_name": None,
        "status": "running",
        "error": None,
        "progress_messages": ["Starting AgentCore 7-agent TDD pipeline…"],
    }

    logger.info("Starting AgentCore workflow for: %s", title)

    final_state = initial_state
    async for event in workflow.astream(initial_state):
        for node_name, node_output in event.items():
            if isinstance(node_output, dict):
                final_state = {**final_state, **node_output}

    logger.info("AgentCore workflow completed with status: %s", final_state.get("status"))

    # Serialize Pydantic objects for JSON response
    tc_review = final_state.get("test_case_review")
    test_design = final_state.get("test_design")

    test_cases_data = []
    if tc_review and tc_review.approved_cases:
        test_cases_data = [tc.model_dump() for tc in tc_review.approved_cases]
    elif test_design:
        test_cases_data = [tc.model_dump() for tc in test_design.test_cases]

    steps_data = [s.model_dump() for s in final_state.get("final_steps", [])]

    return {
        "status": final_state.get("status", "failed"),
        "final_steps": steps_data,
        "test_cases": test_cases_data,
        "generated_code": final_state.get("generated_code"),
        "code_file_name": final_state.get("code_file_name"),
        "progress_messages": final_state.get("progress_messages", []),
        "error": final_state.get("error"),
    }
