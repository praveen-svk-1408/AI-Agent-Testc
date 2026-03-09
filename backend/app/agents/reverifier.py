"""
Step Reviewer Agent.

Validates generated Playwright steps for executability and fixes
hallucinated selectors by cross-referencing against real DOM data.

Replaces the old "reverifier" — the Step Reviewer is DOM-aware.
"""

import logging

from langchain_ollama import ChatOllama
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

from app.config import get_settings
from app.schemas.agent import (
    GeneratedTestStep,
    PageSnapshot,
    StepReviewResult,
)
from app.utils.output_parser import RobustPydanticOutputParser

logger = logging.getLogger(__name__)

settings = get_settings()


SYSTEM_PROMPT = """\
You are a meticulous QA reviewer who validates Playwright test steps against a
LIVE DOM snapshot.  Your job is to catch and FIX problems BEFORE the test runs.

You receive:
 • A list of generated Playwright steps (action, selector, value, expected_result).
 • The real DOM context extracted from the target pages (elements, forms, selectors).

Review process – for EACH step:
1. **Selector check** – Does the selector exist in the DOM context?
   If NOT, find the closest matching real selector and replace it.
2. **Action validity** – Is the action appropriate for the target element?
   (e.g. "fill" on a button is invalid → change to "click")
3. **Value check** – Does the value make sense for the element type?
   (e.g. filling a password field with an email address)
4. **Ordering** – Are waits placed after navigation / page-changing actions?
5. **Assertions** – Do verify_text / verify_element steps target real elements?

Output:
  "approved"        – true if all steps pass review (with fixes applied), false if
                      the steps are fundamentally broken and should be regenerated.
  "fixed_steps"     – the FULL list of steps with corrected selectors / actions.
                      If a step was fine, include it unchanged.
  "issues_found"    – list of human-readable issue descriptions.
  "selector_fixes"  – list of fix descriptions like "Changed selector '#loginBtn'
                       to '[data-testid=\\"login-button\\"]' — original not in DOM".
  "confidence"      – 0.0 to 1.0 — how confident you are the fixed steps will execute.

If more than 50% of selectors are hallucinated, set approved=false and provide
detailed issues so the Step Generator can retry.

Real DOM context:
{page_context}

IMPORTANT: Respond with ONLY a valid JSON object. No markdown code fences.

{format_instructions}
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
            for el in snap.elements[:100]:
                attrs = ", ".join(f"{k}={v}" for k, v in el.attributes.items()) if el.attributes else ""
                part += f"  - [{el.element_type}] selector='{el.selector}' text='{el.text or ''}' {attrs}\n"
        if snap.forms:
            part += "Forms:\n"
            for form in snap.forms:
                part += f"  - Form action={form.get('action')} method={form.get('method')}\n"
                for field in form.get("fields", []):
                    part += f"    - {field.get('tag')} name={field.get('name')} type={field.get('type')} label={field.get('label')}\n"
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


def create_step_reviewer():
    """Create the step reviewer chain."""
    llm = ChatOllama(
        model=settings.ollama_model,
        temperature=0.1,   # Low temp for precise, consistent review
        base_url=settings.ollama_base_url,
    )

    parser = RobustPydanticOutputParser(pydantic_model=StepReviewResult)

    prompt = ChatPromptTemplate.from_messages([
        ("system", SYSTEM_PROMPT),
        ("human", USER_PROMPT),
    ])

    chain = prompt | llm | StrOutputParser() | parser
    return chain, parser


async def review_steps(
    steps: list[GeneratedTestStep],
    snapshots: list[PageSnapshot],
) -> StepReviewResult:
    """
    Review generated steps against real DOM data.

    Returns a StepReviewResult with approval status, fixed steps, and issue details.
    """
    chain, parser = create_step_reviewer()

    page_context = _format_page_context(snapshots)
    steps_text = _format_steps(steps)

    logger.info("StepReviewer: reviewing %d steps against %d page snapshots",
                len(steps), len(snapshots))

    result: StepReviewResult = await chain.ainvoke({
        "page_context": page_context,
        "steps_text": steps_text,
        "format_instructions": parser.get_format_instructions(),
    })

    logger.info(
        "StepReviewer: approved=%s, confidence=%.2f, issues=%d, selector_fixes=%d",
        result.approved, result.confidence,
        len(result.issues_found), len(result.selector_fixes),
    )

    if not result.approved:
        logger.info("StepReviewer issues: %s", "; ".join(result.issues_found))

    return result
