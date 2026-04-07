"""
Structured Output Tools for Strands Agents.

Each agent gets a @tool-decorated function that it calls to submit its structured
output. This replaces the LangChain RobustPydanticOutputParser → Pydantic model
pattern. The calling agent function creates a ResultHolder, binds a tool to it,
and reads the result after the agent completes.

Pattern:
    holder = ResultHolder()
    tool_fn = create_planner_output_tool(holder)
    agent = Agent(model=..., tools=[tool_fn])
    agent("prompt text")
    result = holder.result  # PlannerOutput instance
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

from strands import tool

from schemas.agent import (
    PlannerOutput,
    StructuredTestIntent,
    TestPlan,
    DOMAnalysis,
    SemanticGroup,
    TestDesignOutput,
    IEEE829TestCase,
    TestCaseReviewResult,
    GeneratedTestStep,
    StepReviewResult,
    GeneratedTest,
)

logger = logging.getLogger(__name__)


@dataclass
class ResultHolder:
    """Holds the structured result from a tool invocation."""
    result: Any = None

    @property
    def has_result(self) -> bool:
        return self.result is not None


# ── Planner Output Tool ─────────────────────────────────────────────

def create_planner_output_tool(holder: ResultHolder):
    """Create a tool for submitting planner analysis output."""

    @tool
    def submit_planner_output(
        intent: dict,
        plan: dict,
    ) -> str:
        """Submit the final planner analysis output. Call this EXACTLY ONCE with your complete analysis.

        Args:
            intent: Structured test intent. Must contain keys: goals (list[str]), pages (list[str]). Optional: preconditions (list[str]), assertions (list[str]), edge_cases (list[str]).
            plan: Strategic test plan. Must contain keys: strategy (str), scenarios (list[str]). Optional: risk_areas (list[str]), coverage_goals (list[str]), scope_in (list[str]), scope_out (list[str]).
        """
        try:
            holder.result = PlannerOutput(
                intent=StructuredTestIntent(**intent),
                plan=TestPlan(**plan),
            )
            return "Planner output submitted successfully."
        except Exception as e:
            return f"Validation error: {e}. Fix the data and call again."

    return submit_planner_output


# ── DOM Analysis Output Tool ─────────────────────────────────────────

def create_dom_analysis_tool(holder: ResultHolder):
    """Create a tool for submitting DOM analysis output."""

    @tool
    def submit_dom_analysis(
        semantic_groups: list[dict],
        navigation_patterns: list[str],
        critical_selectors: dict,
        accessibility_issues: list[str],
        recommended_test_paths: list[str],
    ) -> str:
        """Submit the DOM analysis output. Call this EXACTLY ONCE with your complete analysis.

        Args:
            semantic_groups: List of semantic UI groups. Each dict must have: group_type (str), page_url (str), description (str). Optional: primary_selectors (list[str]), priority (str: critical/high/medium/low).
            navigation_patterns: List of navigation flow descriptions, e.g. "Main nav: Home → Products → Cart".
            critical_selectors: Dict mapping descriptive names to CSS selectors, e.g. {"loginEmailInput": "#email"}.
            accessibility_issues: List of accessibility issues found.
            recommended_test_paths: List of recommended user flow paths to test.
        """
        try:
            groups = [SemanticGroup(**g) for g in semantic_groups]
            holder.result = DOMAnalysis(
                semantic_groups=groups,
                navigation_patterns=navigation_patterns,
                critical_selectors=critical_selectors,
                accessibility_issues=accessibility_issues,
                recommended_test_paths=recommended_test_paths,
            )
            return "DOM analysis submitted successfully."
        except Exception as e:
            return f"Validation error: {e}. Fix the data and call again."

    return submit_dom_analysis


# ── Test Design Output Tool ──────────────────────────────────────────

def create_test_design_tool(holder: ResultHolder):
    """Create a tool for submitting IEEE 829 test case designs."""

    @tool
    def submit_test_design(
        test_cases: list[dict],
        coverage_notes: str = "",
    ) -> str:
        """Submit the IEEE 829 test case design. Call this EXACTLY ONCE with all test cases.

        Args:
            test_cases: List of IEEE 829 test cases. Each dict must have: tc_id (str), title (str), test_steps (list[str]), expected_results (list[str]). Optional: category (str), priority (str), preconditions (list[str]).
            coverage_notes: Optional notes about test coverage.
        """
        try:
            cases = [IEEE829TestCase(**tc) for tc in test_cases]
            holder.result = TestDesignOutput(
                test_cases=cases,
                coverage_notes=coverage_notes or None,
            )
            return f"Test design submitted: {len(cases)} test cases."
        except Exception as e:
            return f"Validation error: {e}. Fix the data and call again."

    return submit_test_design


# ── Test Case Review Output Tool ─────────────────────────────────────

def create_test_case_review_tool(holder: ResultHolder):
    """Create a tool for submitting test case review results."""

    @tool
    def submit_test_case_review(
        approved: bool,
        feedback: list[str],
        coverage_gaps: list[str],
        approved_cases: list[dict],
        confidence: float,
    ) -> str:
        """Submit the test case review result. Call this EXACTLY ONCE.

        Args:
            approved: True if all plan scenarios are covered and test cases pass review.
            feedback: List of specific, actionable issues found.
            coverage_gaps: List of plan scenarios not covered by any test case. Must be empty for approval.
            approved_cases: Full list of test cases (with fixes applied). Each dict: tc_id, title, test_steps, expected_results, category, priority, preconditions.
            confidence: Confidence score 0.0 to 1.0.
        """
        try:
            cases = [IEEE829TestCase(**tc) for tc in approved_cases]
            holder.result = TestCaseReviewResult(
                approved=approved,
                feedback=feedback,
                coverage_gaps=coverage_gaps,
                approved_cases=cases,
                confidence=confidence,
            )
            return "Test case review submitted."
        except Exception as e:
            return f"Validation error: {e}. Fix the data and call again."

    return submit_test_case_review


# ── Step Generator Output Tool ───────────────────────────────────────

def create_step_generator_tool(holder: ResultHolder):
    """Create a tool for submitting generated Playwright steps."""

    @tool
    def submit_generated_steps(
        steps: list[dict],
        confidence: float = 1.0,
        notes: str = "",
    ) -> str:
        """Submit the generated Playwright test steps. Call this EXACTLY ONCE with all steps.

        Args:
            steps: List of Playwright steps. Each dict must have: action (str: navigate/click/type/fill/verify_text/verify_element/wait/screenshot). Optional: order (int), selector (str), value (str), expected_result (str), description (str), tc_id (str).
            confidence: Confidence score 0.0 to 1.0.
            notes: Optional generation notes.
        """
        try:
            parsed_steps = [GeneratedTestStep(**s) for s in steps]
            # Auto-assign order if missing
            for i, step in enumerate(parsed_steps):
                if step.order is None:
                    step.order = i + 1
            holder.result = parsed_steps
            return f"Steps submitted: {len(parsed_steps)} steps."
        except Exception as e:
            return f"Validation error: {e}. Fix the data and call again."

    return submit_generated_steps


# ── Step Review Output Tool ──────────────────────────────────────────

def create_step_review_tool(holder: ResultHolder):
    """Create a tool for submitting step review results."""

    @tool
    def submit_step_review(
        approved: bool,
        fixed_steps: list[dict],
        issues_found: list[str],
        selector_fixes: list[str],
        confidence: float,
    ) -> str:
        """Submit the step review result. Call this EXACTLY ONCE.

        Args:
            approved: True if all steps pass review (with fixes applied). False if fundamentally broken.
            fixed_steps: Full list of steps with corrected selectors/actions. Include unchanged steps too. Each dict: action, order, selector, value, expected_result, description, tc_id.
            issues_found: List of human-readable issue descriptions.
            selector_fixes: List of fix descriptions, e.g. "Changed '#loginBtn' to '[data-testid=login]'".
            confidence: Confidence score 0.0 to 1.0.
        """
        try:
            steps = [GeneratedTestStep(**s) for s in fixed_steps]
            holder.result = StepReviewResult(
                approved=approved,
                fixed_steps=steps,
                issues_found=issues_found,
                selector_fixes=selector_fixes,
                confidence=confidence,
            )
            return "Step review submitted."
        except Exception as e:
            return f"Validation error: {e}. Fix the data and call again."

    return submit_step_review


# ── Code Generator Output Tool ───────────────────────────────────────

def create_code_generator_tool(holder: ResultHolder):
    """Create a tool for submitting generated Playwright TypeScript code."""

    @tool
    def submit_generated_code(
        code_content: str,
        imports: list[str],
        notes: str = "",
    ) -> str:
        """Submit the generated Playwright TypeScript test code. Call this EXACTLY ONCE.

        Args:
            code_content: Complete TypeScript .spec.ts file content as a single string.
            imports: List of import packages used, e.g. ["@playwright/test"].
            notes: Optional generation notes.
        """
        try:
            holder.result = {
                "code_content": code_content,
                "imports": imports,
                "notes": notes,
            }
            return "Code submitted successfully."
        except Exception as e:
            return f"Validation error: {e}. Fix the data and call again."

    return submit_generated_code
