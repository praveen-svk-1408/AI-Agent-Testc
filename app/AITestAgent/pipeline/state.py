"""
Pipeline State.

Defines the state container passed between pipeline stages.
Replaces LangGraph's TypedDict WorkflowState with a dataclass.

Ported from: backend/app/agents/workflow.py WorkflowState
"""

from __future__ import annotations

from dataclasses import dataclass, field

from schemas.agent import (
    StructuredTestIntent,
    TestPlan,
    PageSnapshot,
    DOMAnalysis,
    TestDesignOutput,
    TestCaseReviewResult,
    GeneratedTestStep,
    StepReviewResult,
    GeneratedTest,
    IEEE829TestCase,
)


@dataclass
class PipelineState:
    """State container for the 7-agent TDD pipeline."""

    # ── Inputs
    title: str = ""
    description: str = ""
    base_url: str = ""
    app_description: str | None = None
    test_type: str = "functional"

    # ── Authentication (optional)
    login_url: str | None = None
    login_username: str | None = None
    login_password: str | None = None

    # ── Suite context
    suite_id: str | None = None
    suite_name: str | None = None

    # ── After Planner (node 1)
    intent: StructuredTestIntent | None = None
    plan: TestPlan | None = None

    # ── After Snapshot Loader (node 2)
    page_snapshots: list[PageSnapshot] = field(default_factory=list)

    # ── After DOM Analyst (node 3)
    dom_analysis: DOMAnalysis | None = None

    # ── After Test Generator (node 4)
    test_design: TestDesignOutput | None = None

    # ── After Test Case Reviewer — Loop A (node 5)
    test_case_review: TestCaseReviewResult | None = None
    tc_iteration: int = 1
    max_tc_iterations: int = 2

    # ── After Step Generator (node 6)
    steps: list[GeneratedTestStep] = field(default_factory=list)

    # ── After Step Reviewer — Loop B (node 7)
    review: StepReviewResult | None = None
    iteration: int = 1
    max_iterations: int = 3

    # ── Final outputs
    final_steps: list[GeneratedTestStep] = field(default_factory=list)
    generated_code: str | None = None
    code_file_name: str | None = None
    status: str = "running"   # running | success | failed
    error: str | None = None
    progress_messages: list[str] = field(default_factory=list)

    def add_progress(self, message: str) -> None:
        """Append a progress message."""
        self.progress_messages.append(message)

    @property
    def approved_test_cases(self) -> list[IEEE829TestCase]:
        """Get the approved test cases (from reviewer or raw design)."""
        if self.test_case_review and self.test_case_review.approved_cases:
            return self.test_case_review.approved_cases
        if self.test_design:
            return self.test_design.test_cases
        return []

    def to_dict(self) -> dict:
        """Serialize state to a dict for JSON response."""
        return {
            "status": self.status,
            "error": self.error,
            "progress_messages": self.progress_messages,
            "final_steps": [s.model_dump() for s in self.final_steps],
            "generated_code": self.generated_code,
            "code_file_name": self.code_file_name,
            "test_cases_count": len(self.approved_test_cases),
            "steps_count": len(self.final_steps),
        }
