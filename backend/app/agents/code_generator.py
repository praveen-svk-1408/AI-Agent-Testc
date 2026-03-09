"""
Code Generator Agent.

Converts validated Playwright test steps into executable TypeScript .spec.ts code.
This is the final stage of the pipeline – it receives reviewed/fixed steps from the
Step Reviewer and produces a Playwright test file.
"""

import re
import logging

from langchain_ollama import ChatOllama
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from pydantic import BaseModel

from app.config import get_settings
from app.schemas.agent import GeneratedTestStep, GeneratedTest
from app.utils.output_parser import RobustPydanticOutputParser

logger = logging.getLogger(__name__)

settings = get_settings()


class CodeGeneratorOutput(BaseModel):
    """Wrapper for code generator LLM output."""
    code_content: str
    imports: list[str] = []
    notes: str | None = None


SYSTEM_PROMPT = """\
You are an expert Playwright + TypeScript test automation engineer.
Given a list of test steps (each with an action, selector, value, and expected result),
generate a complete, executable Playwright test file in TypeScript.

Rules:
1. Use `import {{ test, expect }} from '@playwright/test';` as the main import.
2. Wrap tests in `test.describe('{suite_name}', () => {{ ... }})`.
3. Each test case becomes a `test('{test_name}', async ({{ page }}) => {{ ... }})`.
4. Map step actions to Playwright API calls:
   - **navigate**: `await page.goto('{value}');`
   - **click**: `await page.locator('{selector}').click();`
   - **type**: `await page.locator('{selector}').pressSequentially('{value}');`
   - **fill**: `await page.locator('{selector}').fill('{value}');`
   - **verify_text**: `await expect(page.locator('{selector}')).toContainText('{expected_result}');`
   - **verify_element**: `await expect(page.locator('{selector}')).toBeVisible();` (or toBeHidden, etc.)
   - **wait**: `await page.waitForSelector('{selector}');` or `await page.waitForURL('{value}');`
   - **screenshot**: `await page.screenshot({{ path: '{value}' }});`
5. Add `await page.waitForLoadState('networkidle');` after navigation steps.
6. Add brief inline comments for each step using the step description.
7. Use role-based locators when available: `page.getByRole(...)`, `page.getByLabel(...)`.
8. Generate clean, well-formatted TypeScript code.
9. Do NOT include any markdown formatting or code fences in your output.

Output ONLY valid JSON with this exact structure:
{{
  "code_content": "<the complete TypeScript test file content as a single string>",
  "imports": ["@playwright/test"],
  "notes": "<any optional notes about the generated code>"
}}
"""

USER_PROMPT = """\
Generate a Playwright TypeScript test file for:

**Suite Name:** {suite_name}
**Test Name:** {test_name}
**Base URL:** {base_url}

**Test Steps:**
{steps_text}

Generate the complete .spec.ts file content as a JSON object with "code_content", "imports", and "notes" fields.
Remember: output ONLY valid JSON, no markdown or code fences.
"""


def _format_steps_for_prompt(steps: list[GeneratedTestStep]) -> str:
    """Format test steps into a readable text block for the LLM prompt."""
    lines = []
    for step in steps:
        parts = [f"Step {step.order}: action={step.action}"]
        if step.selector:
            parts.append(f"selector='{step.selector}'")
        if step.value:
            parts.append(f"value='{step.value}'")
        if step.expected_result:
            parts.append(f"expected='{step.expected_result}'")
        if step.description:
            parts.append(f"description='{step.description}'")
        lines.append(", ".join(parts))
    return "\n".join(lines)


async def generate_test_code(
    steps: list[GeneratedTestStep],
    suite_name: str,
    test_name: str,
    base_url: str,
) -> GeneratedTest:
    """
    Generate Playwright TypeScript test code from reviewed test steps.

    Returns a GeneratedTest with the complete spec file content.
    """
    logger.info("CodeGenerator: generating .spec.ts for '%s' (%d steps)", test_name, len(steps))

    llm = ChatOllama(
        base_url=settings.ollama_base_url,
        model=settings.ollama_model,
        temperature=settings.llm_temperature,
    )

    prompt = ChatPromptTemplate.from_messages([
        ("system", SYSTEM_PROMPT),
        ("human", USER_PROMPT),
    ])

    steps_text = _format_steps_for_prompt(steps)
    parser = RobustPydanticOutputParser(pydantic_model=CodeGeneratorOutput)

    chain = prompt | llm | StrOutputParser() | parser

    try:
        result: CodeGeneratorOutput = await chain.ainvoke({
            "suite_name": suite_name,
            "test_name": test_name,
            "base_url": base_url,
            "steps_text": steps_text,
        })

        safe_suite = _sanitize_filename(suite_name)
        safe_test = _sanitize_filename(test_name)
        file_name = f"{safe_suite}_{safe_test}.spec.ts"

        return GeneratedTest(
            file_name=file_name,
            code_content=result.code_content,
            imports=result.imports,
            test_metadata={
                "suite_name": suite_name,
                "test_name": test_name,
                "base_url": base_url,
                "steps_count": len(steps),
                "notes": result.notes,
            },
        )

    except Exception as e:
        logger.error("CodeGenerator LLM failed: %s", str(e))
        logger.info("Falling back to template-based code generation")
        return _generate_from_template(steps, suite_name, test_name, base_url)


# ── Helpers ──────────────────────────────────────────────────────────

def _sanitize_filename(name: str) -> str:
    """Convert a name to a safe filename component."""
    sanitized = re.sub(r'[^\w\s-]', '', name.lower())
    sanitized = re.sub(r'[\s-]+', '_', sanitized)
    return sanitized[:50].strip('_')


def _escape_ts_string(s: str) -> str:
    """Escape a string for use in TypeScript single-quoted strings."""
    return s.replace("\\", "\\\\").replace("'", "\\'")


def _generate_from_template(
    steps: list[GeneratedTestStep],
    suite_name: str,
    test_name: str,
    base_url: str,
) -> GeneratedTest:
    """
    Fallback template-based code generation when LLM fails.
    Produces valid Playwright TypeScript code from test steps directly.
    """
    lines = [
        "import { test, expect } from '@playwright/test';",
        "",
        f"test.describe('{_escape_ts_string(suite_name)}', () => {{",
        f"  test('{_escape_ts_string(test_name)}', async ({{ page }}) => {{",
    ]

    for step in steps:
        comment = f"    // {step.description}" if step.description else ""
        if comment:
            lines.append(comment)

        action_code = _step_to_playwright_code(step, base_url)
        lines.append(f"    {action_code}")
        lines.append("")

    lines.append("  });")
    lines.append("});")
    lines.append("")

    code_content = "\n".join(lines)

    safe_suite = _sanitize_filename(suite_name)
    safe_test = _sanitize_filename(test_name)
    file_name = f"{safe_suite}_{safe_test}.spec.ts"

    return GeneratedTest(
        file_name=file_name,
        code_content=code_content,
        imports=["@playwright/test"],
        test_metadata={
            "suite_name": suite_name,
            "test_name": test_name,
            "base_url": base_url,
            "steps_count": len(steps),
            "notes": "Generated using template fallback (LLM unavailable)",
        },
    )


def _step_to_playwright_code(step: GeneratedTestStep, base_url: str) -> str:
    """Convert a single test step to a Playwright TypeScript code line."""
    selector = step.selector or ""
    value = step.value or ""
    expected = step.expected_result or ""

    match step.action:
        case "navigate":
            url = value if value.startswith("http") else f"{base_url.rstrip('/')}/{value.lstrip('/')}"
            return f"await page.goto('{_escape_ts_string(url)}');\n    await page.waitForLoadState('networkidle');"
        case "click":
            return f"await page.locator('{_escape_ts_string(selector)}').click();"
        case "type":
            return f"await page.locator('{_escape_ts_string(selector)}').pressSequentially('{_escape_ts_string(value)}');"
        case "fill":
            return f"await page.locator('{_escape_ts_string(selector)}').fill('{_escape_ts_string(value)}');"
        case "verify_text":
            return f"await expect(page.locator('{_escape_ts_string(selector)}')).toContainText('{_escape_ts_string(expected)}');"
        case "verify_element":
            return _generate_verify_element_code(selector, expected)
        case "wait":
            if value and ("/" in value or "http" in value):
                return f"await page.waitForURL('{_escape_ts_string(value)}');"
            elif selector:
                return f"await page.waitForSelector('{_escape_ts_string(selector)}');"
            else:
                return "await page.waitForLoadState('networkidle');"
        case "screenshot":
            label = value or "screenshot"
            safe_label = re.sub(r'[^\w-]', '_', label)
            return f"await page.screenshot({{ path: '{safe_label}.png', fullPage: true }});"
        case _:
            return f"// Unknown action: {step.action}"


def _generate_verify_element_code(selector: str, expected: str) -> str:
    """Generate Playwright assertion code for element state verification."""
    if not expected:
        return f"await expect(page.locator('{_escape_ts_string(selector)}')).toBeVisible();"

    expected_lower = expected.lower()
    if "hidden" in expected_lower or "not visible" in expected_lower:
        return f"await expect(page.locator('{_escape_ts_string(selector)}')).toBeHidden();"
    elif "enabled" in expected_lower:
        return f"await expect(page.locator('{_escape_ts_string(selector)}')).toBeEnabled();"
    elif "disabled" in expected_lower:
        return f"await expect(page.locator('{_escape_ts_string(selector)}')).toBeDisabled();"
    elif "visible" in expected_lower:
        return f"await expect(page.locator('{_escape_ts_string(selector)}')).toBeVisible();"
    elif "url" in expected_lower:
        return f"await expect(page).toHaveURL(/{_escape_ts_string(expected)}/);"
    else:
        return f"await expect(page.locator('{_escape_ts_string(selector)}')).toBeVisible();"
