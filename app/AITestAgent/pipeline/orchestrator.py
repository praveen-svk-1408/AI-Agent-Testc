"""
Pipeline Orchestrator.

Deterministic async Python orchestrator that replaces the LangGraph StateGraph.
Runs the 8-node TDD pipeline sequentially with retry loops for test case review
(Loop A) and step review (Loop B).

Ported from: backend/app/agents/workflow.py (build_workflow + all node functions)
"""

import logging
import os
from typing import AsyncGenerator

from schemas.agent import (
    DOMAnalysis,
    TestPlan,
    TestCaseReviewResult,
    StepReviewResult,
    GeneratedTestStep,
    IEEE829TestCase,
)
from pipeline.state import PipelineState

# Agent imports
from agents.planner import plan_and_analyze
from agents.dom_analyst import analyze_dom
from agents.test_generator import generate_test_cases
from agents.test_case_reviewer import review_test_cases
from agents.step_generator import generate_steps
from agents.reverifier import review_steps
from agents.code_generator import generate_test_suite_code

# Browser crawl
from tools.browser_crawl import crawl_pages, load_crawl_snapshots

logger = logging.getLogger(__name__)


def _ensure_step_order(steps: list[GeneratedTestStep]) -> list[GeneratedTestStep]:
    """Ensure every step has a non-null order assigned sequentially."""
    for i, step in enumerate(steps, start=1):
        if step.order is None:
            step.order = i
    return steps


async def run_pipeline(
    state: PipelineState,
    browser_tool=None,
    generated_tests_dir: str = "generated-tests",
) -> AsyncGenerator[str, None]:
    """Run the complete 7-agent TDD pipeline with progress streaming.

    Yields progress messages as strings. Modifies state in-place.

    Pipeline: Planner → LoadSnapshots → DOMAnalyst → TestGenerator → TestCaseReviewer
              → StepGenerator → StepReviewer → QACodeGenerator
    """
    state.add_progress("Starting 7-agent TDD pipeline…")
    yield state.progress_messages[-1]

    # ── Node 1: Planner ───────────────────────────────────────────────
    try:
        state.add_progress("Running planner…")
        yield state.progress_messages[-1]

        output = await plan_and_analyze(
            title=state.title,
            description=state.description,
            base_url=state.base_url,
            app_description=state.app_description,
            test_type=state.test_type,
        )
        state.intent = output.intent
        state.plan = output.plan

        msg = (
            f"Planner: {len(state.intent.goals)} goals, {len(state.intent.pages)} pages, "
            f"{len(state.intent.assertions)} assertions | "
            f"{len(state.plan.scenarios)} test scenarios (strategy: {state.plan.strategy[:60]})"
        )
        state.add_progress(msg)
        yield msg

    except Exception as e:
        logger.error("Planner failed: %s", e)
        state.status = "failed"
        state.error = f"Planner failed: {e}"
        state.add_progress(f"Error: Planner failed – {e}")
        yield state.progress_messages[-1]
        return

    # ── Node 2: Load Snapshots ────────────────────────────────────────
    try:
        state.add_progress("Loading page snapshots…")
        yield state.progress_messages[-1]

        # Try cached snapshots first
        cached = None
        if state.suite_id:
            cached = await load_crawl_snapshots(state.suite_id)

        if cached:
            state.page_snapshots = cached
            total_elements = sum(len(s.elements) for s in cached)
            msg = f"Snapshots: loaded {len(cached)} pre-crawled pages, {total_elements} interactive elements"
        else:
            # Live crawl
            pages_to_crawl = state.intent.pages if state.intent and state.intent.pages else ["/"]
            state.page_snapshots = await crawl_pages(
                base_url=state.base_url,
                pages=pages_to_crawl,
                browser_tool=browser_tool,
                login_url=state.login_url,
                login_username=state.login_username,
                login_password=state.login_password,
            )
            total_elements = sum(len(s.elements) for s in state.page_snapshots)
            msg = f"Crawler: crawled {len(state.page_snapshots)} pages, {total_elements} interactive elements"

        state.add_progress(msg)
        yield msg

    except Exception as e:
        logger.error("Snapshot loading failed: %s", e)
        state.status = "failed"
        state.error = f"Snapshot loading failed: {e}"
        state.add_progress(f"Error: Snapshot loading failed – {e}")
        yield state.progress_messages[-1]
        return

    # ── Node 3: DOM Analyst ───────────────────────────────────────────
    try:
        state.add_progress("Analyzing DOM…")
        yield state.progress_messages[-1]

        effective_plan = state.plan or TestPlan(
            strategy="General web application testing",
            scenarios=state.intent.goals if state.intent else ["Test the application"],
        )

        state.dom_analysis = await analyze_dom(
            snapshots=state.page_snapshots,
            plan=effective_plan,
            test_type=state.test_type,
        )

        msg = (
            f"DOMAnalyst: {len(state.dom_analysis.semantic_groups)} semantic groups, "
            f"{len(state.dom_analysis.critical_selectors)} critical selectors, "
            f"{len(state.dom_analysis.accessibility_issues)} accessibility issues"
        )
        state.add_progress(msg)
        yield msg

    except Exception as e:
        logger.warning("DOM analysis failed (%s) — continuing with empty analysis", e)
        state.dom_analysis = DOMAnalysis()
        state.add_progress(f"Warning: DOM analysis skipped – {e}")
        yield state.progress_messages[-1]

    # ── Nodes 4-5: Test Generator + Reviewer (Loop A) ─────────────────
    effective_dom = state.dom_analysis or DOMAnalysis()

    for tc_iter in range(state.max_tc_iterations):
        # Node 4: Test Generator
        try:
            state.add_progress(f"Designing test cases (attempt {tc_iter + 1})…")
            yield state.progress_messages[-1]

            state.test_design = await generate_test_cases(
                plan=state.plan,
                dom_analysis=effective_dom,
                intent=state.intent,
                test_type=state.test_type,
            )

            tc_ids = [tc.tc_id for tc in state.test_design.test_cases]
            msg = (
                f"TestGenerator: designed {len(state.test_design.test_cases)} IEEE 829 test cases "
                f"({', '.join(tc_ids)})"
            )
            state.add_progress(msg)
            yield msg

        except Exception as e:
            logger.error("Test design failed: %s", e)
            state.status = "failed"
            state.error = f"Test case design failed: {e}"
            state.add_progress(f"Error: Test case design failed – {e}")
            yield state.progress_messages[-1]
            return

        # Node 5: Test Case Reviewer
        try:
            state.add_progress("Reviewing test cases…")
            yield state.progress_messages[-1]

            state.test_case_review = await review_test_cases(
                test_design=state.test_design,
                plan=state.plan,
                dom_analysis=effective_dom,
                test_type=state.test_type,
            )

            if not state.test_case_review.approved_cases:
                state.test_case_review.approved_cases = state.test_design.test_cases

            if state.test_case_review.approved:
                msg = (
                    f"TestCaseReviewer: APPROVED (confidence: {state.test_case_review.confidence:.0%}, "
                    f"{len(state.test_case_review.approved_cases)} cases)"
                )
                state.add_progress(msg)
                yield msg
                break
            else:
                gaps = "; ".join(state.test_case_review.coverage_gaps[:3])
                issues = "; ".join(state.test_case_review.feedback[:2]) or "needs improvement"
                msg = f"TestCaseReviewer: REJECTED (attempt {tc_iter + 1}): gaps=[{gaps}] issues=[{issues}]"
                state.add_progress(msg)
                yield msg

        except Exception as e:
            logger.warning("Test case review failed (%s) — auto-approving", e)
            state.test_case_review = TestCaseReviewResult(
                approved=True,
                feedback=[f"Review skipped: {e}"],
                coverage_gaps=[],
                approved_cases=state.test_design.test_cases,
                confidence=0.5,
            )
            state.add_progress(f"Warning: Test case review skipped – {e}. Accepting generated cases.")
            yield state.progress_messages[-1]
            break
    else:
        # Max iterations reached — force accept
        effective_cases = state.approved_test_cases
        confidence = state.test_case_review.confidence if state.test_case_review else 0.5
        state.test_case_review = TestCaseReviewResult(
            approved=True,
            feedback=["Accepted after max TC review iterations"],
            coverage_gaps=[],
            approved_cases=effective_cases,
            confidence=confidence,
        )
        msg = f"Accepted {len(effective_cases)} test cases after max iterations (confidence: {confidence:.0%})"
        state.add_progress(msg)
        yield msg

    # ── Nodes 6-7: Step Generator + Reviewer (Loop B) ─────────────────
    for step_iter in range(state.max_iterations):
        # Node 6: Step Generator
        try:
            feedback_text = None
            if state.review and not state.review.approved:
                parts = list(state.review.issues_found) + list(state.review.selector_fixes)
                feedback_text = "\n".join(parts) if parts else None

            state.add_progress(f"Generating Playwright steps (attempt {step_iter + 1})…")
            yield state.progress_messages[-1]

            state.steps = await generate_steps(
                intent=state.intent,
                snapshots=state.page_snapshots,
                feedback=feedback_text,
                test_type=state.test_type,
                approved_test_cases=state.approved_test_cases,
                login_username=state.login_username,
                login_password=state.login_password,
            )

            msg = (
                f"StepGenerator: produced {len(state.steps)} Playwright steps "
                f"({len(state.approved_test_cases)} test cases)"
            )
            state.add_progress(msg)
            yield msg

        except Exception as e:
            logger.error("Step generation failed: %s", e)
            state.status = "failed"
            state.error = f"Step generation failed: {e}"
            state.add_progress(f"Error: Step generation failed – {e}")
            yield state.progress_messages[-1]
            return

        # Node 7: Step Reviewer
        try:
            state.add_progress("Reviewing steps against DOM…")
            yield state.progress_messages[-1]

            state.review = await review_steps(
                steps=state.steps,
                snapshots=state.page_snapshots,
                test_type=state.test_type,
            )

            if state.review.approved:
                state.final_steps = _ensure_step_order(
                    state.review.fixed_steps if state.review.fixed_steps else state.steps
                )
                msg = (
                    f"StepReviewer: APPROVED (confidence: {state.review.confidence:.0%}, "
                    f"fixes: {len(state.review.selector_fixes)})"
                )
                state.add_progress(msg)
                yield msg
                break
            else:
                issues_summary = "; ".join(state.review.issues_found[:3]) or "needs improvement"
                msg = f"StepReviewer: REJECTED (attempt {step_iter + 1}): {issues_summary}"
                state.add_progress(msg)
                yield msg

        except Exception as e:
            logger.warning("Step review failed (%s) — accepting steps", e)
            state.final_steps = _ensure_step_order(state.steps)
            state.add_progress(f"Warning: Step review skipped – {e}. Accepting generated steps.")
            yield state.progress_messages[-1]
            break
    else:
        # Max iterations reached — force accept
        steps = state.steps
        if state.review and state.review.fixed_steps:
            steps = state.review.fixed_steps
        state.final_steps = _ensure_step_order(steps)
        confidence = state.review.confidence if state.review else 0.5
        msg = f"Accepted steps after max iterations (confidence: {confidence:.0%})"
        state.add_progress(msg)
        yield msg

    # ── Node 8: QA Code Generator ─────────────────────────────────────
    try:
        state.add_progress("Generating Playwright TypeScript code…")
        yield state.progress_messages[-1]

        generated = await generate_test_suite_code(
            test_cases=state.approved_test_cases,
            steps=state.final_steps,
            suite_name=state.suite_name or state.title,
            base_url=state.base_url,
            test_type=state.test_type,
        )

        state.generated_code = generated.code_content
        state.code_file_name = generated.file_name

        # Write the spec file to disk if suite_id is available
        if state.suite_id:
            suite_dir = os.path.join(generated_tests_dir, state.suite_id)
            os.makedirs(suite_dir, exist_ok=True)
            code_file_path = os.path.join(suite_dir, generated.file_name)
            with open(code_file_path, "w", encoding="utf-8") as f:
                f.write(generated.code_content)
            logger.info("QACodeGenerator: wrote %s", code_file_path)

        state.status = "success"
        msg = (
            f"QACodeGenerator: generated '{generated.file_name}' "
            f"({len(state.approved_test_cases)} test cases, {len(state.final_steps)} steps)"
        )
        state.add_progress(msg)
        yield msg

    except Exception as e:
        logger.error("QA code generation failed: %s", e)
        state.status = "success"  # Steps + test cases are still valid
        state.error = f"Code generation failed (steps still valid): {e}"
        state.add_progress(f"Warning: QA code generation failed – {e}. Steps available.")
        yield state.progress_messages[-1]

    state.add_progress("Pipeline complete.")
    yield state.progress_messages[-1]
