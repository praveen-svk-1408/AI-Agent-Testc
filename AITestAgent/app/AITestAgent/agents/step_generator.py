"""
Step Generator Agent (Strands · ReAct with DOM context).

Takes approved IEEE 829 test cases + page snapshots (real DOM) and converts them
into concrete, executable Playwright actions.

Ported from: backend/app/agents/step_generator.py
"""

import logging

from strands import Agent

from model.factory import get_model
from schemas.agent import (
    StructuredTestIntent,
    PageSnapshot,
    GeneratedTestStep,
    IEEE829TestCase,
)
from tools.output_tools import ResultHolder, create_step_generator_tool
from utils.output_parser import parse_from_text

logger = logging.getLogger(__name__)


SYSTEM_PROMPT = """\
You are an expert Playwright test-automation engineer.

Test Type: {test_type}

You receive:
 • A structured test intent with goals, assertions, preconditions, and edge cases.
 • Live DOM context: real interactive elements, selectors, and forms extracted from the
   target pages.

Your task: convert every goal and assertion into CONCRETE Playwright actions,
producing an ordered flat list of executable steps.

Allowed actions (use ONLY these):
  navigate       – go to a URL                         (value = URL)
  click          – click an element                    (selector required)
  type           – type into an input char-by-char     (selector + value)
  fill           – fill an input instantly              (selector + value)
  verify_text    – assert visible text on the page     (selector + expected_result)
  verify_element – assert element state (visible, hidden, enabled, disabled)
                                                       (selector + expected_result)
  wait           – wait for element / URL / networkidle (selector or value)
  screenshot     – capture a screenshot                (value = optional label)

ReAct reasoning – for each goal, think:
  THOUGHT: What concrete browser interactions does this goal require?
  ACTION:  Which DOM element (from page context) should I target?
           Use the EXACT selector from the DOM context – do NOT invent selectors.
  OBSERVE: What should the expected_result be so the Step Reviewer can verify it?

Rules:
1. Start with a "navigate" step to the correct page URL.
2. Add a "wait" step ONLY after navigate actions — do NOT add waits between
   every action (Playwright auto-waits for elements).
3. For form fills use "fill" (faster) unless character-by-character input matters.
4. Include "verify_text" or "verify_element" assertions that match each assertion
   from the test intent.
5. Prefer stable selectors: data-testid > role-based > aria-label > id > name > text.
6. If test credentials are provided below, use them EXACTLY for login/authentication
   form fields. Otherwise, use realistic but safe test data.
7. Include ONE "screenshot" step at the end of each goal for evidence.
8. Every step MUST have a descriptive "description" field.
9. ONLY generate steps for the goals and assertions listed.
10. Be CONCISE — aim for 3-8 steps per goal, typically under 25 steps total.
11. This is ONE test case — produce a SINGLE sequential flow.
12. IMPORTANT: Each step MUST have its "tc_id" field set to the test-case ID it
    implements (e.g. "TC-001"). Group all steps for TC-001 first, then TC-002, etc.
{reviewer_feedback}
{test_credentials}
Available page information:
{page_context}

IMPORTANT: You MUST call the submit_generated_steps tool with your steps.
Do NOT output raw JSON — call the tool instead.
"""

USER_PROMPT = """\
{test_cases_slot}
Test Intent:
- Goals: {goals}
- Pages: {pages}
- Preconditions: {preconditions}
- Assertions: {assertions}
- Edge Cases: {edge_cases}

Generate the flat list of executable Playwright steps (with tc_id set on each step).
Order steps sequentially (step 1, 2, 3 … N) across all test cases.
"""


def _format_page_context(snapshots: list[PageSnapshot]) -> str:
    """Format page snapshots into a readable context string for the LLM."""
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


async def generate_steps(
    intent: StructuredTestIntent,
    snapshots: list[PageSnapshot],
    feedback: str | None = None,
    test_type: str = "functional",
    approved_test_cases: list[IEEE829TestCase] | None = None,
    login_username: str | None = None,
    login_password: str | None = None,
) -> list[GeneratedTestStep]:
    """Generate executable Playwright steps from structured test intent + DOM.

    Returns a list of GeneratedTestStep objects.
    """
    holder = ResultHolder()
    tool_fn = create_step_generator_tool(holder)

    page_context = _format_page_context(snapshots)

    reviewer_feedback = ""
    if feedback:
        reviewer_feedback = (
            f"\n**IMPORTANT – Step Reviewer feedback (you MUST address these issues):**\n"
            f"{feedback}\n"
        )

    test_cases_slot = ""
    if approved_test_cases:
        lines = ["Approved IEEE 829 Test Cases (generate steps for EACH, set tc_id on every step):"]
        for tc in approved_test_cases:
            lines.append(f"\n{tc.tc_id}: {tc.title} [{tc.category}/{tc.priority}]")
            if tc.preconditions:
                lines.append(f"  Preconditions: {'; '.join(tc.preconditions)}")
            lines.append("  Expected steps (high-level):")
            for i, step in enumerate(tc.test_steps, 1):
                expected = tc.expected_results[i - 1] if i <= len(tc.expected_results) else ""
                lines.append(f"    {i}. {step}  →  {expected}")
        test_cases_slot = "\n".join(lines) + "\n"

    if login_username or login_password:
        cred_lines = ["Test Credentials (use these EXACTLY for login/authentication form fields):"]
        if login_username:
            cred_lines.append(f"  - Username/Email: {login_username}")
        if login_password:
            cred_lines.append(f"  - Password: {login_password}")
        test_credentials = "\n".join(cred_lines)
    else:
        test_credentials = ""

    system_prompt = SYSTEM_PROMPT.format(
        test_type=test_type,
        reviewer_feedback=reviewer_feedback,
        test_credentials=test_credentials,
        page_context=page_context,
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
        test_cases_slot=test_cases_slot,
    )

    logger.info(
        "StepGenerator: converting %d goals into Playwright steps "
        "(%d test cases, feedback=%s, credentials=%s)",
        len(intent.goals), len(approved_test_cases or []), bool(feedback),
        bool(login_username),
    )

    result = agent(user_message)

    if holder.has_result:
        steps = holder.result
        logger.info("StepGenerator: produced %d executable steps", len(steps))
        return steps

    logger.warning("StepGenerator: tool not called, attempting text parse fallback")
    from pydantic import BaseModel

    class _StepWrapper(BaseModel):
        steps: list[GeneratedTestStep]

    wrapper = parse_from_text(str(result), _StepWrapper)
    for i, step in enumerate(wrapper.steps):
        if step.order is None:
            step.order = i + 1
    return wrapper.steps
