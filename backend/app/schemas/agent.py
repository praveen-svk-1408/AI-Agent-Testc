from pydantic import BaseModel


# ── Orchestrator (Plan-and-Execute) ──────────────────────────────────

class StructuredTestIntent(BaseModel):
    """Output of the Orchestrator: decomposed sub-goals and context."""
    goals: list[str]
    pages: list[str]
    preconditions: list[str] = []
    assertions: list[str] = []
    edge_cases: list[str] = []


# ── Page Crawler ─────────────────────────────────────────────────────

class PageElement(BaseModel):
    """A single interactive element on a page."""
    tag: str
    role: str | None = None
    text: str | None = None
    selector: str
    element_type: str | None = None  # button, input, link, select, etc.
    attributes: dict[str, str] = {}


class PageSnapshot(BaseModel):
    """Output of the Page Crawler."""
    page_url: str
    page_title: str | None = None
    elements: list[PageElement] = []
    forms: list[dict] = []
    raw_html: str | None = None


# ── Test Generator (IEEE 829) ───────────────────────────────────────

class IEEE829TestCase(BaseModel):
    """An IEEE 829 format test case produced by the Test Generator."""
    tc_id: str                          # e.g. "TC-001"
    title: str
    category: str = "functional"        # functional, validation, navigation, security, usability
    priority: str = "medium"            # high, medium, low
    preconditions: list[str] = []
    test_steps: list[str]               # High-level NL step descriptions
    expected_results: list[str]         # Expected outcome per step


class TestDesignOutput(BaseModel):
    """Output of the Test Generator agent (IEEE 829 test design)."""
    test_cases: list[IEEE829TestCase]
    coverage_notes: str | None = None


# ── Step Generator (Playwright actions) ──────────────────────────────

class GeneratedTestStep(BaseModel):
    """A single executable Playwright step from the Step Generator."""
    order: int | None = None
    action: str   # navigate, click, type, fill, verify_text, verify_element, wait, screenshot
    selector: str | None = None
    value: str | None = None
    expected_result: str | None = None
    description: str | None = None


# ── Step Reviewer ────────────────────────────────────────────────────

class StepReviewResult(BaseModel):
    """Output of the Step Reviewer agent."""
    approved: bool
    fixed_steps: list[GeneratedTestStep]    # Steps with corrected selectors
    issues_found: list[str] = []
    selector_fixes: list[str] = []          # Human-readable fix descriptions
    confidence: float = 1.0


# ── Code Generator ───────────────────────────────────────────────────

class GeneratedTest(BaseModel):
    """Output of the Code Generator - executable Playwright .spec.ts code."""
    file_name: str
    code_content: str
    imports: list[str] = []
    test_metadata: dict = {}
