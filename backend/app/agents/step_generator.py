"""
Step Generator Agent  (ReAct with DOM context).

Takes IEEE 829 test cases + page snapshots (real DOM) and converts each
high-level test step into a concrete, executable Playwright action.

Supported actions:
  navigate, click, type, fill, verify_text, verify_element, wait, screenshot
"""

import logging

from langchain_ollama import ChatOllama
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from pydantic import BaseModel, model_validator

from app.config import get_settings
from app.schemas.agent import (
    IEEE829TestCase,
    TestDesignOutput,
    PageSnapshot,
    GeneratedTestStep,
)
from app.utils.output_parser import RobustPydanticOutputParser

logger = logging.getLogger(__name__)

settings = get_settings()


class StepGeneratorOutput(BaseModel):
    """Wrapper for step generator output."""
    steps: list[GeneratedTestStep]
    confidence: float = 1.0
    notes: str | None = None

    @model_validator(mode="after")
    def assign_missing_order(self) -> "StepGeneratorOutput":
        """Auto-assign order to steps if the LLM omitted it."""
        for i, step in enumerate(self.steps):
            if step.order is None:
                step.order = i + 1
        return self


SYSTEM_PROMPT = """\
You are an expert Playwright test-automation engineer.

You receive:
 • One or more IEEE 829 test cases (each with high-level steps and expected results).
 • Live DOM context: real interactive elements, selectors, and forms extracted from the
   target pages.

Your task: convert every high-level test step into one or more CONCRETE Playwright
actions, producing an ordered flat list of executable steps.

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

ReAct reasoning – for each IEEE 829 step, think:
  THOUGHT: What concrete browser interaction does this require?
  ACTION:  Which DOM element (from page context) should I target?
           Use the EXACT selector from the DOM context – do NOT invent selectors.
  OBSERVE: What should the expected_result be so the Step Reviewer can verify it?

Rules:
1. Start every test case with a "navigate" step to the correct page URL.
2. After navigation or page-changing actions add a "wait" step.
3. For form fills use "fill" (faster) unless character-by-character input matters.
4. End each test case's steps with "verify_text" or "verify_element" assertions that
   match the IEEE 829 expected results.
5. Prefer stable selectors: data-testid > role-based > aria-label > id > name > text.
6. Use realistic but safe test data (e.g. "testuser@example.com", "Password123!").
7. Include a "screenshot" step after critical assertions for evidence.
8. Every step MUST have a descriptive "description" field.
{reviewer_feedback}
Available page information:
{page_context}

IMPORTANT: Respond with ONLY a valid JSON object. No markdown code fences.

{format_instructions}
"""

USER_PROMPT = """\
IEEE 829 Test Cases to implement:
{test_cases_text}

Generate the flat list of executable Playwright steps covering ALL test cases above.
Order steps sequentially across all test cases (step 1, 2, 3 … N).
"""


def _format_page_context(snapshots: list[PageSnapshot]) -> str:
    """Format page snapshots into a readable context string for the LLM."""
    parts = []
    for snap in snapshots:
        part = f"\n--- Page: {snap.page_url} (Title: {snap.page_title}) ---\n"
        if snap.elements:
            part += "Interactive elements:\n"
            for el in snap.elements[:80]:
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


def _format_test_cases(test_design: TestDesignOutput) -> str:
    """Format IEEE 829 test cases into a prompt-friendly text block."""
    lines = []
    for tc in test_design.test_cases:
        lines.append(f"\n[{tc.tc_id}] {tc.title}  (category={tc.category}, priority={tc.priority})")
        if tc.preconditions:
            lines.append("  Preconditions: " + "; ".join(tc.preconditions))
        for i, (step, exp) in enumerate(
            zip(tc.test_steps, tc.expected_results), start=1
        ):
            lines.append(f"  Step {i}: {step}")
            lines.append(f"    Expected: {exp}")
        # Handle extra expected_results beyond test_steps length
        for j in range(len(tc.test_steps), len(tc.expected_results)):
            lines.append(f"    Expected ({j+1}): {tc.expected_results[j]}")
    return "\n".join(lines)


def create_step_generator():
    """Create the step generator chain."""
    llm = ChatOllama(
        model=settings.ollama_model,
        temperature=settings.llm_temperature,
        base_url=settings.ollama_base_url,
    )

    parser = RobustPydanticOutputParser(pydantic_model=StepGeneratorOutput)

    prompt = ChatPromptTemplate.from_messages([
        ("system", SYSTEM_PROMPT),
        ("human", USER_PROMPT),
    ])

    chain = prompt | llm | StrOutputParser() | parser
    return chain, parser


async def generate_steps(
    test_design: TestDesignOutput,
    snapshots: list[PageSnapshot],
    feedback: str | None = None,
) -> StepGeneratorOutput:
    """
    Generate executable Playwright steps from IEEE 829 test cases + DOM.

    Args:
        test_design: Output of the Test Generator (IEEE 829 test cases).
        snapshots:   Crawled page snapshots with real DOM selectors.
        feedback:    Optional feedback from the Step Reviewer for re-generation.
    """
    chain, parser = create_step_generator()

    page_context = _format_page_context(snapshots)
    test_cases_text = _format_test_cases(test_design)

    reviewer_feedback = ""
    if feedback:
        reviewer_feedback = (
            f"\n**IMPORTANT – Step Reviewer feedback (you MUST address these issues):**\n"
            f"{feedback}\n"
        )

    logger.info(
        "StepGenerator: converting %d IEEE 829 test cases into Playwright steps (feedback=%s)",
        len(test_design.test_cases), bool(feedback),
    )

    result: StepGeneratorOutput = await chain.ainvoke({
        "page_context": page_context,
        "test_cases_text": test_cases_text,
        "reviewer_feedback": reviewer_feedback,
        "format_instructions": parser.get_format_instructions(),
    })

    logger.info(
        "StepGenerator: produced %d executable steps (confidence: %.2f)",
        len(result.steps), result.confidence,
    )
    return result
