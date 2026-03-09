"""
Test Generator Agent  (IEEE 829 · ReAct pattern).

Takes a natural-language requirement + DOM context (page snapshots) and
produces structured IEEE 829 test cases.

Each test case contains:
  TC-ID, Title, Category, Priority, Preconditions, Steps (NL), Expected Results.

These high-level test cases are later handed to the Step Generator which
converts them into concrete executable Playwright steps.
"""

import logging

from langchain_ollama import ChatOllama
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

from app.config import get_settings
from app.schemas.agent import (
    StructuredTestIntent,
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
 • Live DOM context extracted from the target web pages

Produce one or more IEEE 829 test cases.

Each test case must include:
  "tc_id"            – unique ID like "TC-001"
  "title"            – short descriptive title
  "category"         – one of: functional, validation, navigation, security, usability
  "priority"         – high / medium / low
  "preconditions"    – list of setup requirements
  "test_steps"       – ordered list of HIGH-LEVEL human-readable steps
                        (e.g. "Enter valid email into the Email field")
  "expected_results" – one expected outcome per step, in the same order

ReAct reasoning – think step-by-step:
  THOUGHT: What functionality or user flow does this goal exercise?
  ACTION:  Which real DOM elements (from the page context) are involved?
  OBSERVE: What text, URL change, or element state should be visible after each step?

Rules:
1. Every goal from the intent MUST map to at least one test case.
2. Assertions from the intent MUST appear as expected_results.
3. Include edge-case test cases where the intent lists them.
4. Reference REAL selectors / element text from the DOM context so downstream
   agents can locate the elements.  Do NOT hallucinate selectors.
5. Keep steps concrete and unambiguous – avoid "the user should see something."
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

Design IEEE 829 test cases that fully cover every goal, assertion, and edge case.
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


def create_test_generator():
    """Create the IEEE 829 test-generator chain."""
    llm = ChatOllama(
        model=settings.ollama_model,
        temperature=settings.llm_temperature,
        base_url=settings.ollama_base_url,
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
    snapshots: list[PageSnapshot],
) -> TestDesignOutput:
    """
    Generate IEEE 829 test cases from the orchestrator plan and crawled DOM.

    Returns a TestDesignOutput containing one or more IEEE829TestCase objects.
    """
    chain, parser = create_test_generator()
    page_context = _format_page_context(snapshots)

    logger.info(
        "TestGenerator: designing IEEE 829 cases for %d goals across %d pages",
        len(intent.goals), len(snapshots),
    )

    result: TestDesignOutput = await chain.ainvoke({
        "page_context": page_context,
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
