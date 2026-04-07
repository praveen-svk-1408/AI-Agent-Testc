"""
Planner Agent (Strands).

Decomposes a natural-language test requirement into structured sub-goals
(StructuredTestIntent) and a strategic test plan (TestPlan).

Ported from: backend/app/agents/requirement_analyzer.py
"""

import logging

from strands import Agent

from model.factory import get_model
from schemas.agent import PlannerOutput
from tools.output_tools import ResultHolder, create_planner_output_tool
from utils.output_parser import parse_from_text

logger = logging.getLogger(__name__)


SYSTEM_PROMPT = """\
You are a Plan-and-Execute orchestrator for web-application test automation.

Your role is to produce TWO outputs simultaneously from a natural-language test requirement:
  1. A structured test INTENT (tactical: goals, pages, preconditions, assertions, edge_cases)
  2. A strategic test PLAN (strategic: scenarios, strategy, risk areas, coverage goals)

Application context:
- Name / Description: {app_description}
- Base URL: {base_url}
- Test Type: {test_type}

Test type guidance:
- "functional": Focus on individual feature behavior — form submissions, navigation, CRUD.
- "e2e": Focus on complete user journeys across multiple pages.
- "integration": Focus on component interactions — API calls, data persistence.
- "accessibility": Focus on WCAG compliance — keyboard nav, ARIA, screen reader.
- "visual": Focus on layout and visual appearance — positioning, responsiveness.
- "performance": Focus on load times, responsiveness, resource usage.

For the tactical INTENT:
- "goals": ONLY goals explicitly described or directly implied. Do NOT invent extra scenarios.
- "pages": Relative URL paths the test must visit.
- "preconditions": Setup needed before any test runs.
- "assertions": Concrete, observable outcomes. Only for stated goals.
- "edge_cases": ONLY if the user explicitly mentions negative/boundary testing.

For the strategic PLAN:
- "strategy": One sentence describing the overall testing approach.
- "scenarios": Distinct test scenarios to cover (can be same as goals initially, but
  phrased as user-story-level actions, e.g. 'User logs in with valid credentials').
- "risk_areas": Application areas that are complex or prone to bugs.
- "coverage_goals": What the test suite aims to achieve (e.g. 'Cover login happy path').
- "scope_in": Pages/flows explicitly included.
- "scope_out": Pages/flows explicitly excluded.

IMPORTANT: You MUST call the submit_planner_output tool with your analysis.
Do NOT output raw JSON — call the tool instead.
"""

USER_PROMPT = """\
Test Case Title: {title}

Test Case Description:
{description}
"""


async def plan_and_analyze(
    title: str,
    description: str,
    base_url: str,
    app_description: str | None = None,
    test_type: str = "functional",
) -> PlannerOutput:
    """Decompose a test requirement into a structured intent + strategic test plan.

    Returns a PlannerOutput containing StructuredTestIntent + TestPlan.
    """
    holder = ResultHolder()
    tool_fn = create_planner_output_tool(holder)

    system_prompt = SYSTEM_PROMPT.format(
        app_description=app_description or "Web application",
        base_url=base_url,
        test_type=test_type,
    )

    agent = Agent(
        model=get_model(temperature=0.2, max_tokens=3072),
        system_prompt=system_prompt,
        tools=[tool_fn],
    )

    user_message = USER_PROMPT.format(title=title, description=description)

    logger.info("Planner: decomposing requirement – %s", title)

    result = agent(user_message)

    if holder.has_result:
        output = holder.result
        logger.info(
            "Planner: %d goals, %d pages, %d assertions | %d scenarios (strategy: %s)",
            len(output.intent.goals),
            len(output.intent.pages),
            len(output.intent.assertions),
            len(output.plan.scenarios),
            output.plan.strategy[:60],
        )
        return output

    # Fallback: parse from text response
    logger.warning("Planner: tool was not called, attempting text parse fallback")
    text = str(result)
    output = parse_from_text(text, PlannerOutput)
    logger.info("Planner: fallback parse succeeded")
    return output
