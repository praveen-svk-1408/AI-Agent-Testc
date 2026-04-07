"""
Test Generator Agent (Strands · IEEE 829).

Receives the strategic test plan, DOM analysis, and structured test intent to design
IEEE 829 test cases. Test cases define WHAT to test; the Step Generator later derives
HOW to implement each case against the real DOM.

Ported from: backend/app/agents/test_generator.py
"""

import logging

from strands import Agent

from model.factory import get_model
from schemas.agent import (
    StructuredTestIntent,
    TestPlan,
    DOMAnalysis,
    TestDesignOutput,
)
from tools.output_tools import ResultHolder, create_test_design_tool
from utils.output_parser import parse_from_text

logger = logging.getLogger(__name__)


_TEST_TYPE_GUIDANCE: dict[str, str] = {
    "functional": "Focus on correctness of user-visible behaviour: form submissions, navigation, CRUD operations, and validation messages.",
    "e2e": "Cover complete multi-page user journeys from entry-point to final outcome. Each test case should span the full flow (login → action → assertion).",
    "integration": "Verify interactions between UI and backend: API request/response cycles, data persistence after form submission, and cross-component state synchronisation.",
    "accessibility": "Design test cases that verify WCAG 2.1 AA compliance: keyboard navigation, ARIA roles, colour-contrast ratios, focus management, and screen-reader labels.",
    "visual": "Each test case must capture full-page or component screenshots as expected results. Use visual comparison assertions and note pixel/layout tolerances.",
    "performance": "Test cases should measure load times, time-to-interactive, and resource counts. Flag test cases where wait durations would indicate a performance regression.",
}


SYSTEM_PROMPT = """\
You are a senior QA test-design engineer using the IEEE 829 standard.

Test Type: {test_type}
Test-type guidance: {test_type_guidance}

You receive:
 • A strategic test plan with defined scenarios, risk areas, and coverage goals
 • A DOM analysis identifying semantic UI groups and stable selectors on each page
 • A structured test intent with goals, assertions, and preconditions

Your task: produce IEEE 829 test cases that:
 1. Cover EVERY scenario listed in the test plan (one test case minimum per scenario)
 2. Reference real UI groups from the DOM analysis in the test_steps descriptions
 3. Produce concrete, measurable expected_results

Each test case must include:
  "tc_id"            – unique ID like "TC-001"
  "title"            – short descriptive title
  "category"         – one of: functional, validation, navigation, security, usability
  "priority"         – high / medium / low
  "preconditions"    – list of setup requirements
  "test_steps"       – ordered list of HIGH-LEVEL human-readable step descriptions
  "expected_results" – one expected outcome per step, in the same order

ReAct reasoning – per scenario:
  THOUGHT: Which DOM groups and UI elements does this scenario involve?
  ACTION:  Design test_steps that flow through those groups logically.
  OBSERVE: What observable outcome proves each step succeeded?

Rules:
1. One test case per plan scenario — don't merge multiple scenarios into one TC.
2. Map each assertion from the test intent to at least one expected_result.
3. Use the DOM analysis semantic groups to name UI elements naturally.
4. Apply the test-type guidance to shape category, priority, and expected_results.
5. Number tc_ids sequentially: TC-001, TC-002, …
6. If DOM analysis is empty, rely on the intent and scenarios — write abstract steps.

Test Plan Summary:
{plan_summary}

DOM Analysis:
{dom_summary}

IMPORTANT: You MUST call the submit_test_design tool with your test cases.
Do NOT output raw JSON — call the tool instead.
"""

USER_PROMPT = """\
Test Intent context:
- Goals: {goals}
- Pages: {pages}
- Preconditions: {preconditions}
- Assertions: {assertions}
- Edge Cases: {edge_cases}

Design one IEEE 829 test case per plan scenario above.
Each test case should describe WHAT to test at a human-readable level.
"""


def _format_plan_summary(plan: TestPlan) -> str:
    """Format the test plan into a summary for the LLM."""
    parts = [f"Strategy: {plan.strategy}"]
    parts.append("Scenarios (one TC per scenario):\n" + "\n".join(f"  - {s}" for s in plan.scenarios))
    if plan.risk_areas:
        parts.append("Risk Areas: " + "; ".join(plan.risk_areas))
    if plan.coverage_goals:
        parts.append("Coverage Goals: " + "; ".join(plan.coverage_goals))
    return "\n".join(parts)


def _format_dom_summary(dom: DOMAnalysis) -> str:
    """Format the DOM analysis into a compact summary for the LLM."""
    if not dom.semantic_groups and not dom.critical_selectors:
        return "No DOM analysis available."
    parts = []
    if dom.semantic_groups:
        parts.append("Semantic UI Groups:")
        for g in dom.semantic_groups:
            parts.append(
                f"  [{g.priority.upper()}] {g.group_type} on {g.page_url}: {g.description}"
            )
    if dom.navigation_patterns:
        parts.append("Navigation: " + "; ".join(dom.navigation_patterns))
    if dom.recommended_test_paths:
        parts.append("Recommended paths: " + "; ".join(dom.recommended_test_paths))
    return "\n".join(parts)


async def generate_test_cases(
    plan: TestPlan,
    dom_analysis: DOMAnalysis,
    intent: StructuredTestIntent,
    test_type: str = "functional",
) -> TestDesignOutput:
    """Generate IEEE 829 test cases from the strategic test plan and DOM analysis.

    Returns a TestDesignOutput containing IEEE829TestCase objects.
    """
    holder = ResultHolder()
    tool_fn = create_test_design_tool(holder)

    plan_summary = _format_plan_summary(plan)
    dom_summary = _format_dom_summary(dom_analysis)
    test_type_guidance = _TEST_TYPE_GUIDANCE.get(test_type, _TEST_TYPE_GUIDANCE["functional"])

    system_prompt = SYSTEM_PROMPT.format(
        test_type=test_type,
        test_type_guidance=test_type_guidance,
        plan_summary=plan_summary,
        dom_summary=dom_summary,
    )

    agent = Agent(
        model=get_model(temperature=0.2, max_tokens=4096),
        system_prompt=system_prompt,
        tools=[tool_fn],
    )

    user_message = USER_PROMPT.format(
        goals="\n".join(f"- {g}" for g in intent.goals),
        pages="\n".join(f"- {p}" for p in intent.pages),
        preconditions="\n".join(f"- {p}" for p in intent.preconditions) or "None",
        assertions="\n".join(f"- {a}" for a in intent.assertions) or "None",
        edge_cases="\n".join(f"- {e}" for e in intent.edge_cases) or "None",
    )

    logger.info(
        "TestGenerator: designing IEEE 829 cases for %d scenarios, %d DOM groups (test_type=%s)",
        len(plan.scenarios), len(dom_analysis.semantic_groups), test_type,
    )

    result = agent(user_message)

    if holder.has_result:
        output = holder.result
        logger.info("TestGenerator: produced %d IEEE 829 test cases", len(output.test_cases))
        return output

    logger.warning("TestGenerator: tool not called, attempting text parse fallback")
    return parse_from_text(str(result), TestDesignOutput)
