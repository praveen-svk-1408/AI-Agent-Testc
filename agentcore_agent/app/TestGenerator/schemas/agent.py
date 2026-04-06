from pydantic import BaseModel


# ── Orchestrator (Plan-and-Execute) ──────────────────────────────────

class StructuredTestIntent(BaseModel):
    """Output of the Orchestrator: decomposed sub-goals and context."""
    goals: list[str]
    pages: list[str]
    preconditions: list[str] = []
    assertions: list[str] = []
    edge_cases: list[str] = []


class TestPlan(BaseModel):
    """Strategic test plan produced by the Planner alongside StructuredTestIntent."""
    strategy: str
    scenarios: list[str]
    risk_areas: list[str] = []
    coverage_goals: list[str] = []
    scope_in: list[str] = []
    scope_out: list[str] = []


class PlannerOutput(BaseModel):
    """Combined output of the Planner: structured test intent + strategic test plan."""
    intent: StructuredTestIntent
    plan: TestPlan


# ── Page Crawler ─────────────────────────────────────────────────────

class PageElement(BaseModel):
    """A single interactive element on a page."""
    tag: str
    role: str | None = None
    text: str | None = None
    selector: str
    element_type: str | None = None
    attributes: dict[str, str] = {}


class PageSnapshot(BaseModel):
    """Output of the Page Crawler."""
    page_url: str
    page_title: str | None = None
    elements: list[PageElement] = []
    forms: list[dict] = []
    raw_html: str | None = None
    accessibility_tree: str | None = None


# ── DOM Analyst ───────────────────────────────────────────────────────

class SemanticGroup(BaseModel):
    """A logical grouping of DOM elements identified by the DOM Analyst."""
    group_type: str
    page_url: str
    description: str
    primary_selectors: list[str] = []
    priority: str = "medium"


class DOMAnalysis(BaseModel):
    """Output of the DOM Analyst agent."""
    semantic_groups: list[SemanticGroup] = []
    navigation_patterns: list[str] = []
    critical_selectors: dict[str, str] = {}
    accessibility_issues: list[str] = []
    recommended_test_paths: list[str] = []


# ── Test Generator (IEEE 829) ───────────────────────────────────────

class IEEE829TestCase(BaseModel):
    """An IEEE 829 format test case produced by the Test Generator."""
    tc_id: str
    title: str
    category: str = "functional"
    priority: str = "medium"
    preconditions: list[str] = []
    test_steps: list[str]
    expected_results: list[str]


class TestDesignOutput(BaseModel):
    """Output of the Test Generator agent (IEEE 829 test design)."""
    test_cases: list[IEEE829TestCase]
    coverage_notes: str | None = None


# ── Step Generator (Playwright actions) ──────────────────────────────

class GeneratedTestStep(BaseModel):
    """A single executable Playwright step from the Step Generator."""
    order: int | None = None
    action: str
    selector: str | None = None
    value: str | None = None
    expected_result: str | None = None
    description: str | None = None
    tc_id: str | None = None


# ── Step Reviewer ────────────────────────────────────────────────────

class StepReviewResult(BaseModel):
    """Output of the Step Reviewer agent."""
    approved: bool
    fixed_steps: list[GeneratedTestStep] = []
    issues_found: list[str] = []
    selector_fixes: list[str] = []
    confidence: float = 1.0


# ── Test Case Reviewer ───────────────────────────────────────────────

class TestCaseReviewResult(BaseModel):
    """Output of the Test Case Reviewer agent (Loop A)."""
    approved: bool
    feedback: list[str] = []
    coverage_gaps: list[str] = []
    approved_cases: list[IEEE829TestCase] = []
    confidence: float = 1.0


# ── Code Generator ───────────────────────────────────────────────────

class GeneratedTest(BaseModel):
    """Output of the Code Generator - executable Playwright .spec.ts code."""
    file_name: str
    code_content: str
    imports: list[str] = []
    test_metadata: dict = {}
