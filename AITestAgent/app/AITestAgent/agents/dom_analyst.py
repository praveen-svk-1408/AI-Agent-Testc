"""
DOM Analyst Agent (Strands).

Analyzes raw page snapshots and identifies semantic UI patterns — groups DOM elements
into logical components, extracts stable selectors, navigation patterns,
accessibility issues, and recommended test paths.

Ported from: backend/app/agents/dom_analyst.py
"""

import logging

from strands import Agent

from model.factory import get_model
from schemas.agent import PageSnapshot, DOMAnalysis, TestPlan
from tools.output_tools import ResultHolder, create_dom_analysis_tool
from utils.output_parser import parse_from_text

logger = logging.getLogger(__name__)


SYSTEM_PROMPT = """\
You are an expert DOM analyst specialising in web UI pattern recognition for test automation.

Test Type: {test_type}

Given raw page snapshots (elements, forms, selectors) and a strategic test plan, your task is to:

1. **SEMANTIC GROUPS**: Identify logical UI component groups across all pages.
   Group related elements together — e.g. email field + password field + submit button → "loginForm".
   Common group types: loginForm, registrationForm, navMenu, primaryNav, productCard, productGrid,
   checkoutForm, shippingForm, paymentForm, cartSummary, searchBar, modal, alertMessage,
   userProfile, dataTable, filterPanel, paginationControl, footer, header.

2. **NAVIGATION PATTERNS**: Describe the navigational flow of the application.

3. **CRITICAL SELECTORS**: Extract the most stable selectors for key UI elements.
   Preference order: data-testid > role-based > aria-label > id > name > text-content.
   Include 5-15 critical selectors covering the most important interactive elements.

4. **ACCESSIBILITY ISSUES**: Flag anything visible in element attributes or the
   accessibility tree: inputs without labels, buttons without accessible text,
   images without alt text, missing ARIA roles, non-descriptive link text.

5. **RECOMMENDED TEST PATHS**: Based on the navigation and forms, suggest 2-4 user
   flow paths to test.

Rules:
- Only report elements that actually exist in the provided snapshots.
- For primary_selectors, include 2-5 key selectors for each group's most important elements.
- Set priority: "critical" for auth/payment flows, "high" for core features,
  "medium" for secondary features, "low" for informational/static content.
- If a page has no meaningful interactive groups, skip it.

IMPORTANT: You MUST call the submit_dom_analysis tool with your analysis.
Do NOT output raw JSON — call the tool instead.
"""

USER_PROMPT = """\
Strategic Test Plan Scenarios:
{scenarios}

Page Snapshots:
{page_context}

Analyze the DOM and identify all semantic groups, navigation patterns, critical selectors,
accessibility issues, and recommended test paths based on the scenarios above.
"""


def _format_page_context(snapshots: list[PageSnapshot]) -> str:
    """Format page snapshots into a readable context string for the LLM."""
    parts = []
    for snap in snapshots:
        part = f"\n=== Page: {snap.page_url} (Title: {snap.page_title}) ===\n"
        if snap.elements:
            part += f"Interactive Elements ({len(snap.elements)} total, showing first 60):\n"
            for el in snap.elements[:60]:
                attrs = ""
                if el.attributes:
                    key_attrs = {k: v for k, v in el.attributes.items()
                                 if k in ("data-testid", "aria-label", "id", "name", "type",
                                          "placeholder", "href", "role", "class")}
                    attrs = " ".join(f'{k}="{v}"' for k, v in list(key_attrs.items())[:5])
                part += (
                    f"  [{el.element_type or el.tag}] selector='{el.selector}' "
                    f"text='{(el.text or '')[:60]}' role='{el.role or ''}' {attrs}\n"
                )
        if snap.forms:
            part += f"Forms ({len(snap.forms)}):\n"
            for form in snap.forms:
                part += f"  Form: action={form.get('action')} method={form.get('method')}\n"
                for field in form.get("fields", []):
                    part += (
                        f"    - {field.get('tag')} name={field.get('name')} "
                        f"type={field.get('type')} label='{field.get('label', '')}' "
                        f"id={field.get('id')}\n"
                    )
        if snap.accessibility_tree:
            part += f"Accessibility Tree:\n{snap.accessibility_tree}\n"
        parts.append(part)
    return "\n".join(parts) if parts else "No page data available."


async def analyze_dom(
    snapshots: list[PageSnapshot],
    plan: TestPlan,
    test_type: str = "functional",
) -> DOMAnalysis:
    """Analyze DOM snapshots to identify semantic UI patterns and stable selectors.

    Returns a DOMAnalysis with semantic groups, navigation patterns, and critical selectors.
    """
    holder = ResultHolder()
    tool_fn = create_dom_analysis_tool(holder)

    system_prompt = SYSTEM_PROMPT.format(test_type=test_type)

    agent = Agent(
        model=get_model(temperature=0.1, max_tokens=3072),
        system_prompt=system_prompt,
        tools=[tool_fn],
    )

    page_context = _format_page_context(snapshots)
    scenarios_text = (
        "\n".join(f"- {s}" for s in plan.scenarios)
        if plan.scenarios
        else "- No specific scenarios defined"
    )

    user_message = USER_PROMPT.format(
        scenarios=scenarios_text,
        page_context=page_context,
    )

    logger.info(
        "DOMAnalyst: analysing %d pages for %d scenarios (test_type=%s)",
        len(snapshots), len(plan.scenarios), test_type,
    )

    try:
        result = agent(user_message)

        if holder.has_result:
            analysis = holder.result
            logger.info(
                "DOMAnalyst: %d semantic groups, %d critical selectors, "
                "%d accessibility issues, %d recommended paths",
                len(analysis.semantic_groups),
                len(analysis.critical_selectors),
                len(analysis.accessibility_issues),
                len(analysis.recommended_test_paths),
            )
            return analysis

        # Fallback: parse from text
        logger.warning("DOMAnalyst: tool not called, attempting text parse fallback")
        return parse_from_text(str(result), DOMAnalysis)

    except Exception as e:
        logger.warning("DOMAnalyst: analysis failed (%s) — returning minimal fallback", e)
        return DOMAnalysis(
            semantic_groups=[],
            navigation_patterns=[
                f"Pages available: {', '.join(s.page_url for s in snapshots)}"
            ],
            critical_selectors={},
            accessibility_issues=[],
            recommended_test_paths=[plan.scenarios[0]] if plan.scenarios else [],
        )
