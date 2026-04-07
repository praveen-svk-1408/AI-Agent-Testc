"""
Step Reviewer Agent (Strands · Loop B).

Validates generated Playwright steps for executability and fixes
hallucinated selectors by cross-referencing against real DOM data.

Ported from: backend/app/agents/reverifier.py
"""

import logging

from strands import Agent

from model.factory import get_model
from schemas.agent import (
    GeneratedTestStep,
    PageSnapshot,
    StepReviewResult,
)
from tools.output_tools import ResultHolder, create_step_review_tool
from utils.output_parser import parse_from_text

logger = logging.getLogger(__name__)


_TEST_TYPE_REVIEW_RULES: dict[str, str] = {
    "functional": "Verify that every user-visible action has a corresponding assertion step. Ensure form-submit steps are followed by a verify_text or verify_element check.",
    "e2e": "Confirm the steps form a continuous multi-page journey. Flag any missing navigate steps between distinct pages and ensure each page transition has a waitForLoadState step.",
    "integration": "Check that API-triggering actions (form submits, button clicks) are followed by a wait step (waitForResponse or waitForSelector) and an assertion confirming the server response is reflected in the UI.",
    "accessibility": "Ensure selectors use role-based or label-based locators (getByRole, getByLabel, getByText) rather than CSS class or XPath selectors wherever possible. Flag any click steps missing keyboard-navigation alternatives.",
    "visual": "Confirm at least one screenshot step is present per logical test section. Verify screenshot file paths are unique and descriptive. Flag any step sequences that change layout without a following screenshot.",
    "performance": "Flag any fixed wait/sleep steps as performance risks — replace with event-driven waits. Ensure navigation steps measure time-to-interactive rather than using arbitrary timeouts.",
}


SYSTEM_PROMPT = """\
You are a meticulous QA reviewer who validates Playwright test steps against a
LIVE DOM snapshot. Your job is to catch and FIX problems BEFORE the test runs.

Test Type: {test_type}
Additional review rules for this test type: {test_type_rules}

You receive:
 • A list of generated Playwright steps (action, selector, value, expected_result).
 • The real DOM context extracted from the target pages (elements, forms, selectors).

Review process – for EACH step:
1. **Selector check** – Does the selector exist in the DOM context?
   If NOT, find the closest matching real selector and replace it.
2. **Action validity** – Is the action appropriate for the target element?
3. **Value check** – Does the value make sense for the element type?
4. **Ordering** – Are waits placed after navigation / page-changing actions?
5. **Assertions** – Do verify_text / verify_element steps target real elements?
6. **Test-type rules** – Apply the additional rules above.

Output requirements:
  "approved"        – true if all steps pass review (with fixes applied), false if fundamentally broken.
  "fixed_steps"     – the FULL list of steps with corrected selectors / actions.
  "issues_found"    – list of human-readable issue descriptions.
  "selector_fixes"  – list of fix descriptions.
  "confidence"      – 0.0 to 1.0.

If more than 50% of selectors are hallucinated, set approved=false.

Real DOM context:
{page_context}

IMPORTANT: You MUST call the submit_step_review tool with your review.
Do NOT output raw JSON — call the tool instead.
"""

USER_PROMPT = """\
Generated steps to review:
{steps_text}

Review every step against the real DOM context above.
Fix any hallucinated selectors, invalid actions, or missing waits.
"""


def _format_page_context(snapshots: list[PageSnapshot]) -> str:
    """Format page snapshots into a readable context string."""
    parts = []
    for snap in snapshots:
        part = f"\n--- Page: {snap.page_url} (Title: {snap.page_title}) ---\n"
        if snap.elements:
            part += "Interactive elements:\n"
            for el in snap.elements[:50]:
                attrs = ", ".join(f"{k}={v}" for k, v in el.attributes.items()) if el.attributes else ""
                part += f"  - [{el.element_type}] selector='{el.selector}' text='{el.text or ''}' {attrs}\n"
        if snap.forms:
            part += "Forms:\n"
            for form in snap.forms:
                part += f"  - Form action={form.get('action')} method={form.get('method')}\n"
                for field in form.get("fields", []):
                    part += f"    - {field.get('tag')} name={field.get('name')} type={field.get('type')} label={field.get('label')}\n"
        if snap.accessibility_tree:
            part += f"Accessibility Tree:\n{snap.accessibility_tree}\n"
        parts.append(part)
    return "\n".join(parts) if parts else "No page data available."


def _format_steps(steps: list[GeneratedTestStep]) -> str:
    """Format steps into a readable string for review."""
    lines = []
    for step in steps:
        line = f"  {step.order}. [{step.action}]"
        if step.selector:
            line += f" selector='{step.selector}'"
        if step.value:
            line += f" value='{step.value}'"
        if step.expected_result:
            line += f" expected='{step.expected_result}'"
        if step.description:
            line += f" — {step.description}"
        lines.append(line)
    return "\n".join(lines)


async def review_steps(
    steps: list[GeneratedTestStep],
    snapshots: list[PageSnapshot],
    test_type: str = "functional",
) -> StepReviewResult:
    """Review generated steps against real DOM data.

    Returns a StepReviewResult with approval status, fixed steps, and issue details.
    """
    holder = ResultHolder()
    tool_fn = create_step_review_tool(holder)

    page_context = _format_page_context(snapshots)
    steps_text = _format_steps(steps)
    test_type_rules = _TEST_TYPE_REVIEW_RULES.get(
        test_type, _TEST_TYPE_REVIEW_RULES["functional"]
    )

    system_prompt = SYSTEM_PROMPT.format(
        test_type=test_type,
        test_type_rules=test_type_rules,
        page_context=page_context,
    )

    agent = Agent(
        model=get_model(temperature=0.1, max_tokens=4096),
        system_prompt=system_prompt,
        tools=[tool_fn],
    )

    user_message = USER_PROMPT.format(steps_text=steps_text)

    logger.info(
        "StepReviewer: reviewing %d steps against %d page snapshots (test_type=%s)",
        len(steps), len(snapshots), test_type,
    )

    result = agent(user_message)

    if holder.has_result:
        review = holder.result
        logger.info(
            "StepReviewer: approved=%s, confidence=%.2f, issues=%d, selector_fixes=%d",
            review.approved, review.confidence,
            len(review.issues_found), len(review.selector_fixes),
        )
        return review

    logger.warning("StepReviewer: tool not called, attempting text parse fallback")
    return parse_from_text(str(result), StepReviewResult)
