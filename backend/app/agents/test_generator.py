"""
Test Generator Agent  (IEEE 829 · ReAct pattern).

Takes reviewed Playwright steps + the original test intent and produces
structured IEEE 829 test cases that document what the steps cover.

Each test case contains:
  TC-ID, Title, Category, Priority, Preconditions, Steps (NL), Expected Results.

This agent runs AFTER the Step Reviewer so that test cases accurately
reflect the final executable steps.
"""

import logging

from langchain_ollama import ChatOllama
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

from app.config import get_settings
from app.schemas.agent import (
    StructuredTestIntent,
    GeneratedTestStep,
    PageSnapshot,
    IEEE829TestCase,
    TestDesignOutput,
)
from app.utils.output_parser import RobustPydanticOutputParser

logger = logging.getLogger(__name__)

settings = get_settings()


SYSTEM_PROMPT = """\
You are a senior QA test-design engineer using the IEEE 829 standard.

Given:
 • A structured test intent (goals, assertions, edge-cases)
 • Reviewed Playwright steps that have been validated against the real DOM
 • Live DOM context extracted from the target web pages

Your task: produce IEEE 829 test cases that accurately document the reviewed steps.
Group related steps into logical test cases.

Each test case must include:
  "tc_id"            – unique ID like "TC-001"
  "title"            – short descriptive title
  "category"         – one of: functional, validation, navigation, security, usability
  "priority"         – high / medium / low
  "preconditions"    – list of setup requirements
  "test_steps"       – ordered list of HIGH-LEVEL human-readable step descriptions
                        derived from the reviewed Playwright steps
  "expected_results" – one expected outcome per step, in the same order

ReAct reasoning – think step-by-step:
  THOUGHT: Which reviewed steps relate to the same goal or user flow?
  ACTION:  Group them into a logical test case and derive human-readable descriptions.
  OBSERVE: What expected result does each step produce?

Rules:
1. Every goal from the intent MUST map to at least one test case.
2. Assertions from the intent MUST appear as expected_results.
3. Each test case should correspond to a coherent group of reviewed steps.
4. Translate the concrete Playwright steps into human-readable test_steps
   (e.g. a "fill" step on an email input → "Enter email address").
5. Keep steps concrete and unambiguous.
6. Number the tc_id sequentially: TC-001, TC-002, …

Available page information:
{page_context}

IMPORTANT: Respond with ONLY a valid JSON object.  No markdown code fences.

{format_instructions}
"""

USER_PROMPT = """\
Test Intent:
- Goals: {goals}
- Pages: {pages}
- Preconditions: {preconditions}
- Assertions: {assertions}
- Edge Cases: {edge_cases}

Reviewed Playwright Steps:
{steps_text}

Design IEEE 829 test cases that document the reviewed steps above,
grouping related steps into logical test cases that cover every goal and assertion.
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
        parts.append(part)
    return "\n".join(parts) if parts else "No page data available."


def _format_steps(steps: list[GeneratedTestStep]) -> str:
    """Format reviewed Playwright steps into a readable string for the LLM."""
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


def create_test_generator():
    """Create the IEEE 829 test-generator chain."""
    llm = ChatOllama(
        model=settings.ollama_model,
        temperature=settings.llm_temperature,
        base_url=settings.ollama_base_url,
        num_predict=4096,
    )

    parser = RobustPydanticOutputParser(pydantic_model=TestDesignOutput)

    prompt = ChatPromptTemplate.from_messages([
        ("system", SYSTEM_PROMPT),
        ("human", USER_PROMPT),
    ])

    chain = prompt | llm | StrOutputParser() | parser
    return chain, parser


async def generate_test_cases(
    intent: StructuredTestIntent,
    steps: list[GeneratedTestStep],
    snapshots: list[PageSnapshot],
) -> TestDesignOutput:
    """
    Generate IEEE 829 test cases from reviewed Playwright steps.

    Runs after the Step Reviewer so test cases reflect the final executable steps.

    Args:
        intent:    Structured test intent from the Orchestrator.
        steps:     Reviewed/approved Playwright steps.
        snapshots: Crawled page snapshots with real DOM selectors.

    Returns a TestDesignOutput containing one or more IEEE829TestCase objects.
    """
    chain, parser = create_test_generator()
    page_context = _format_page_context(snapshots)
    steps_text = _format_steps(steps)

    logger.info(
        "TestGenerator: designing IEEE 829 cases from %d reviewed steps for %d goals",
        len(steps), len(intent.goals),
    )

    result: TestDesignOutput = await chain.ainvoke({
        "page_context": page_context,
        "steps_text": steps_text,
        "goals": "\n".join(f"- {g}" for g in intent.goals),
        "pages": "\n".join(f"- {p}" for p in intent.pages),
        "preconditions": "\n".join(f"- {p}" for p in intent.preconditions) or "None",
        "assertions": "\n".join(f"- {a}" for a in intent.assertions) or "None",
        "edge_cases": "\n".join(f"- {e}" for e in intent.edge_cases) or "None",
        "format_instructions": parser.get_format_instructions(),
    })

    logger.info(
        "TestGenerator: produced %d IEEE 829 test cases",
        len(result.test_cases),
    )
    return result
