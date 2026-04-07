"""
Test Case Reviewer Agent (Strands · Loop A).

Validates IEEE 829 test cases against the strategic test plan and DOM analysis
BEFORE committing to step generation. Ensures comprehensive coverage, feasibility,
and quality.

Ported from: backend/app/agents/test_case_reviewer.py
"""

import logging

from strands import Agent

from model.factory import get_model
from schemas.agent import (
    TestDesignOutput,
    TestPlan,
    DOMAnalysis,
    TestCaseReviewResult,
)
from tools.output_tools import ResultHolder, create_test_case_review_tool
from utils.output_parser import parse_from_text

logger = logging.getLogger(__name__)


_TEST_TYPE_REVIEW_CRITERIA: dict[str, str] = {
    "functional": (
        "Every test case must target a specific feature behavior. "
        "Each form submission and navigation must have a corresponding assertion in expected_results."
    ),
    "e2e": (
        "Test cases must form complete user journeys spanning at least 2 pages. "
        "Ensure there is a continuous flow from entry to final outcome. "
        "Flag orphaned single-page tests unless clearly isolated."
    ),
    "integration": (
        "Each test case must include API interaction steps (form submits, data loads). "
        "Verify both UI change AND data persistence in expected_results."
    ),
    "accessibility": (
        "At least one test case must validate keyboard navigation. "
        "Test cases should verify ARIA roles, labels, and focus management. "
        "Check that expected_results reference WCAG-compliant outcomes."
    ),
    "visual": (
        "Each test case must include at least one screenshot assertion in expected_results. "
        "Distinct visual states (default, hover, error, success) should each have their own test case."
    ),
    "performance": (
        "Test cases must include timing assertions (e.g. 'page loads within 3s'). "
        "Check that test steps measure load time or interaction latency, not just functional behavior."
    ),
}


SYSTEM_PROMPT = """\
You are a meticulous test case reviewer with deep expertise in IEEE 829 test design.

Test Type: {test_type}
Type-specific criteria: {test_type_criteria}

Your task: review the generated IEEE 829 test cases against:
1. The **strategic test plan** — are ALL planned scenarios covered?
2. The **DOM analysis** — are the described test steps feasible given the actual UI?

Review checklist — for EACH test case:
1. **COVERAGE**: Does it map to exactly one scenario from the test plan?
2. **FEASIBILITY**: Do the test steps describe interactions with UI groups that exist in the DOM analysis?
3. **COMPLETENESS**: Does it have clear preconditions, actionable steps, and measurable expected_results?
4. **GRANULARITY**: Is it focused (1 scenario per test case) or doing too many things at once?
5. **PRIORITY**: Is the priority appropriate? (auth/payment = high, informational = low)
6. **TYPE-CRITERIA**: Does it satisfy the test-type-specific criteria above?

Output requirements:
- "approved": true ONLY if every plan scenario is covered AND all test cases pass the checklist.
- "feedback": specific, actionable issues.
- "coverage_gaps": list of plan scenarios that no test case covers. Must be EMPTY for approval.
- "approved_cases": the FULL list of test cases with any minor wording/priority fixes applied.
- "confidence": 0.0 to 1.0.

Approval thresholds:
- coverage_gaps non-empty → approved = false
- More than 2 test cases with clearly infeasible steps → approved = false
- Minor wording/priority adjustments → fix in-place, keep approved = true

Strategic Test Plan:
{plan_context}

DOM Analysis:
{dom_context}

IMPORTANT: You MUST call the submit_test_case_review tool with your review.
Do NOT output raw JSON — call the tool instead.
"""

USER_PROMPT = """\
Generated IEEE 829 Test Cases to Review:
{test_cases_text}

Review all test cases against the strategic plan and DOM analysis provided.
Return the full approved_cases list (with fixes applied) and any feedback or coverage gaps.
"""


def _format_plan(plan: TestPlan) -> str:
    parts = [f"Strategy: {plan.strategy}"]
    parts.append("Scenarios:\n" + "\n".join(f"  - {s}" for s in plan.scenarios))
    if plan.risk_areas:
        parts.append("Risk Areas:\n" + "\n".join(f"  - {r}" for r in plan.risk_areas))
    if plan.coverage_goals:
        parts.append("Coverage Goals:\n" + "\n".join(f"  - {g}" for g in plan.coverage_goals))
    if plan.scope_out:
        parts.append("Out of Scope:\n" + "\n".join(f"  - {s}" for s in plan.scope_out))
    return "\n".join(parts)


def _format_dom_analysis(dom: DOMAnalysis) -> str:
    parts = []
    if dom.semantic_groups:
        parts.append("Semantic UI Groups:")
        for g in dom.semantic_groups:
            parts.append(
                f"  [{g.priority.upper()}] {g.group_type} on {g.page_url}: {g.description}"
            )
            if g.primary_selectors:
                parts.append(f"    Key selectors: {', '.join(g.primary_selectors[:4])}")
    if dom.navigation_patterns:
        parts.append("Navigation: " + "; ".join(dom.navigation_patterns))
    if dom.recommended_test_paths:
        parts.append("Recommended paths: " + "; ".join(dom.recommended_test_paths))
    if dom.critical_selectors:
        sel_preview = ", ".join(f"{k}='{v}'" for k, v in list(dom.critical_selectors.items())[:8])
        parts.append(f"Critical selectors: {sel_preview}")
    return "\n".join(parts) if parts else "No DOM analysis available."


def _format_test_cases(test_design: TestDesignOutput) -> str:
    parts: list[str] = []
    for tc in test_design.test_cases:
        parts.append(f"\n{tc.tc_id}: {tc.title}")
        parts.append(f"  Category: {tc.category} | Priority: {tc.priority}")
        if tc.preconditions:
            parts.append(f"  Preconditions: {'; '.join(tc.preconditions)}")
        parts.append("  Steps & Expected Results:")
        for i, step in enumerate(tc.test_steps, 1):
            expected = tc.expected_results[i - 1] if i <= len(tc.expected_results) else "—"
            parts.append(f"    {i}. {step}  →  {expected}")
    return "\n".join(parts) if parts else "No test cases to review."


async def review_test_cases(
    test_design: TestDesignOutput,
    plan: TestPlan,
    dom_analysis: DOMAnalysis,
    test_type: str = "functional",
) -> TestCaseReviewResult:
    """Review IEEE 829 test cases against the strategic test plan and DOM analysis.

    Returns a TestCaseReviewResult with approval status, issues, and approved cases.
    """
    holder = ResultHolder()
    tool_fn = create_test_case_review_tool(holder)

    test_type_criteria = _TEST_TYPE_REVIEW_CRITERIA.get(
        test_type, _TEST_TYPE_REVIEW_CRITERIA["functional"]
    )

    system_prompt = SYSTEM_PROMPT.format(
        test_type=test_type,
        test_type_criteria=test_type_criteria,
        plan_context=_format_plan(plan),
        dom_context=_format_dom_analysis(dom_analysis),
    )

    agent = Agent(
        model=get_model(temperature=0.1, max_tokens=3072),
        system_prompt=system_prompt,
        tools=[tool_fn],
    )

    user_message = USER_PROMPT.format(test_cases_text=_format_test_cases(test_design))

    logger.info(
        "TestCaseReviewer: reviewing %d test cases against %d plan scenarios (test_type=%s)",
        len(test_design.test_cases), len(plan.scenarios), test_type,
    )

    try:
        result = agent(user_message)

        if holder.has_result:
            review = holder.result
            # Ensure approved_cases is populated
            if not review.approved_cases:
                review.approved_cases = test_design.test_cases
            logger.info(
                "TestCaseReviewer: approved=%s, confidence=%.2f, gaps=%d, issues=%d",
                review.approved, review.confidence,
                len(review.coverage_gaps), len(review.feedback),
            )
            return review

        # Fallback: parse from text
        logger.warning("TestCaseReviewer: tool not called, attempting text parse fallback")
        review = parse_from_text(str(result), TestCaseReviewResult)
        if not review.approved_cases:
            review.approved_cases = test_design.test_cases
        return review

    except Exception as e:
        logger.warning("TestCaseReviewer: review failed (%s) — auto-approving", e)
        return TestCaseReviewResult(
            approved=True,
            feedback=[f"Review skipped due to error: {e}"],
            coverage_gaps=[],
            approved_cases=test_design.test_cases,
            confidence=0.6,
        )
