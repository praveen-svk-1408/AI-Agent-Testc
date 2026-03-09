"""
Plan-and-Execute Orchestrator.

Decomposes a natural-language test requirement into structured sub-goals,
target pages, preconditions, assertions, and edge cases.
Acts as the *Planner* in a Plan-and-Execute loop: downstream agents
(Test Generator, Step Generator, Step Reviewer) execute the plan.
"""

import logging

from langchain_ollama import ChatOllama
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

from app.config import get_settings
from app.schemas.agent import StructuredTestIntent
from app.utils.output_parser import RobustPydanticOutputParser

logger = logging.getLogger(__name__)

settings = get_settings()

SYSTEM_PROMPT = """\
You are a Plan-and-Execute orchestrator for web-application test automation.

Your role is to DECOMPOSE a natural-language test requirement into a detailed,
actionable plan that downstream agents will execute.

Application context:
- Name / Description: {app_description}
- Base URL: {base_url}

Given the test description below, produce a structured plan with:
1. **goals** – Atomic, verifiable testing goals (each small enough to map to one
   test case).  Be specific: "Verify the login form shows 'Email is required'
   when submitted empty" is better than "Test login validation."
2. **pages** – Relative URL paths the test must visit (e.g. "/login", "/dashboard").
3. **preconditions** – Setup needed before any test runs (e.g. "user account exists").
4. **assertions** – Concrete, observable outcomes to verify (visible text, URL
   changes, element states, toast messages, etc.).
5. **edge_cases** – Boundary or negative scenarios to cover (empty fields, long
   input, special characters, etc.).

Think step-by-step:
- First, identify WHAT the user wants tested.
- Then, break it into the smallest independent goals.
- For each goal, note which page and which assertions apply.
- Finally, consider edge cases that a good QA engineer would add.

IMPORTANT: Respond with ONLY a valid JSON object. No markdown code fences.

{format_instructions}
"""

USER_PROMPT = """\
Test Case Title: {title}

Test Case Description:
{description}
"""


def create_orchestrator():
    """Create the Plan-and-Execute orchestrator chain."""
    llm = ChatOllama(
        model=settings.ollama_model,
        temperature=settings.llm_temperature,
        base_url=settings.ollama_base_url,
    )

    parser = RobustPydanticOutputParser(pydantic_model=StructuredTestIntent)

    prompt = ChatPromptTemplate.from_messages([
        ("system", SYSTEM_PROMPT),
        ("human", USER_PROMPT),
    ])

    chain = prompt | llm | StrOutputParser() | parser
    return chain, parser


async def analyze_requirements(
    title: str,
    description: str,
    base_url: str,
    app_description: str | None = None,
) -> StructuredTestIntent:
    """
    Decompose a test requirement into a structured plan (sub-goals, pages,
    assertions, edge-cases) that downstream agents will execute.
    """
    chain, parser = create_orchestrator()

    logger.info("Orchestrator: decomposing requirement – %s", title)

    result = await chain.ainvoke({
        "title": title,
        "description": description,
        "base_url": base_url,
        "app_description": app_description or "Web application",
        "format_instructions": parser.get_format_instructions(),
    })

    logger.info(
        "Orchestrator plan ready: %d goals, %d pages, %d assertions, %d edge-cases",
        len(result.goals), len(result.pages),
        len(result.assertions), len(result.edge_cases),
    )
    return result
