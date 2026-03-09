"""
Step Executor — runs TestStep objects directly via playwright-python.

Playwright cannot spawn its browser driver subprocess from within Windows
``ProactorEventLoop`` (used by uvicorn/asyncio).  Neither the async API nor
the sync API work inside the same process — the sync API also creates an
internal event loop that hits the same ``NotImplementedError``.

**Solution**: launch a **completely separate Python subprocess** that runs
Playwright from a fresh process with its own event loop.  This is the same
strategy that ``crawler.py`` uses successfully.

The subprocess receives step data as JSON on stdin, executes every step
with the sync Playwright API, and writes a JSON result to stdout.
"""

import asyncio
import functools
import json
import logging
import os
import subprocess
import shutil
import sys
import textwrap
import time
from dataclasses import dataclass, field
from typing import Callable, Awaitable

from app.config import get_settings
from app.services.artifact_manager import get_artifact_dir

logger = logging.getLogger(__name__)
settings = get_settings()


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class StepResult:
    order: int
    action: str
    selector: str | None = None
    value: str | None = None
    description: str | None = None
    status: str = "passed"          # passed | failed | skipped
    error_message: str | None = None
    screenshot_path: str | None = None
    duration_ms: int = 0


@dataclass
class ExecutionResult:
    status: str = "passed"          # passed | failed | error
    total: int = 0
    passed: int = 0
    failed: int = 0
    skipped: int = 0
    duration_ms: int = 0
    error_message: str | None = None
    step_results: list[StepResult] = field(default_factory=list)
    trace_path: str | None = None
    video_path: str | None = None


# ---------------------------------------------------------------------------
# Self-contained subprocess script
# ---------------------------------------------------------------------------
# This script is fed to ``python -c`` in a brand-new process.  It reads JSON
# from stdin, drives sync Playwright, and prints JSON to stdout.  It must NOT
# import any ``app.*`` modules — it is fully standalone.

_EXECUTOR_SCRIPT = textwrap.dedent(r'''
import json, os, sys, time

def main():
    payload = json.loads(sys.stdin.read())
    steps       = payload["steps"]
    browser_name = payload["browser_name"]
    base_url    = payload["base_url"]
    artifact_dir = payload["artifact_dir"]
    headed      = payload.get("headed", False)
    step_timeout = payload.get("step_timeout_ms", 15000)
    nav_timeout  = payload.get("navigation_timeout_ms", 30000)

    os.makedirs(artifact_dir, exist_ok=True)

    from playwright.sync_api import sync_playwright, expect

    results = []
    trace_path = None
    video_path = None
    t0 = time.perf_counter()

    with sync_playwright() as pw:
        bt = getattr(pw, browser_name, pw.chromium)
        browser = bt.launch(headless=not headed)
        context = browser.new_context(
            base_url=base_url,
            viewport={"width": 1280, "height": 720},
            record_video_dir=os.path.join(artifact_dir, "videos"),
            ignore_https_errors=True,
        )
        context.tracing.start(screenshots=True, snapshots=True, sources=True)
        page = context.new_page()
        page.set_default_timeout(step_timeout)

        try:
            for step in steps:
                st0 = time.perf_counter()
                sr = {
                    "order": step["order"],
                    "action": step["action"],
                    "selector": step.get("selector"),
                    "value": step.get("value"),
                    "description": step.get("description"),
                    "status": "passed",
                    "error_message": None,
                    "screenshot_path": None,
                    "duration_ms": 0,
                }
                try:
                    action   = (step.get("action") or "").lower().strip()
                    selector = step.get("selector") or ""
                    value    = step.get("value") or ""

                    if action == "navigate":
                        url = value or selector
                        page.goto(url, wait_until="domcontentloaded", timeout=nav_timeout)
                    elif action == "click":
                        page.locator(selector).click(timeout=step_timeout)
                    elif action == "type":
                        loc = page.locator(selector)
                        loc.click(timeout=step_timeout)
                        loc.press_sequentially(value, delay=50)
                    elif action == "fill":
                        page.locator(selector).fill(value, timeout=step_timeout)
                    elif action == "select":
                        page.locator(selector).select_option(value, timeout=step_timeout)
                    elif action == "hover":
                        page.locator(selector).hover(timeout=step_timeout)
                    elif action == "press":
                        if selector:
                            page.locator(selector).press(value, timeout=step_timeout)
                        else:
                            page.keyboard.press(value)
                    elif action == "clear":
                        page.locator(selector).clear(timeout=step_timeout)
                    elif action == "scroll":
                        if selector:
                            page.locator(selector).scroll_into_view_if_needed(timeout=step_timeout)
                        else:
                            page.evaluate("window.scrollBy(0, 300)")
                    elif action == "verify_text":
                        loc = page.locator(selector) if selector else page.locator("body")
                        expect(loc).to_contain_text(value, timeout=step_timeout)
                    elif action == "verify_element":
                        expect(page.locator(selector)).to_be_visible(timeout=step_timeout)
                    elif action == "wait":
                        if selector:
                            page.wait_for_selector(selector, timeout=step_timeout)
                        else:
                            ms = int(value) if value.isdigit() else 1000
                            page.wait_for_load_state("networkidle", timeout=ms)
                    elif action == "screenshot":
                        ss = os.path.join(artifact_dir, f"step_{step['order']}_screenshot.png")
                        page.screenshot(path=ss, full_page=True)
                        sr["screenshot_path"] = ss
                    else:
                        sr["status"] = "skipped"

                except Exception as exc:
                    sr["status"] = "failed"
                    sr["error_message"] = str(exc)[:1000]
                    try:
                        ss = os.path.join(artifact_dir, f"step_{step['order']}_failure.png")
                        page.screenshot(path=ss, full_page=True)
                        sr["screenshot_path"] = ss
                    except Exception:
                        pass

                sr["duration_ms"] = int((time.perf_counter() - st0) * 1000)
                results.append(sr)

        finally:
            tp = os.path.join(artifact_dir, "trace.zip")
            try:
                context.tracing.stop(path=tp)
                trace_path = tp
            except Exception:
                pass
            try:
                v = page.video
                if v:
                    video_path = v.path()
            except Exception:
                pass
            page.close()
            context.close()
            browser.close()

    total_ms = int((time.perf_counter() - t0) * 1000)
    passed  = sum(1 for r in results if r["status"] == "passed")
    failed  = sum(1 for r in results if r["status"] == "failed")
    skipped = sum(1 for r in results if r["status"] == "skipped")

    out = {
        "status": "passed" if failed == 0 else "failed",
        "total": len(results),
        "passed": passed,
        "failed": failed,
        "skipped": skipped,
        "duration_ms": total_ms,
        "step_results": results,
        "trace_path": trace_path,
        "video_path": video_path,
        "error_message": None,
    }
    if failed:
        msgs = [f"Step {r['order']}: {r['error_message']}" for r in results if r["status"] == "failed"]
        out["error_message"] = "; ".join(msgs[:5])

    print(json.dumps(out))

if __name__ == "__main__":
    main()
''')


# ---------------------------------------------------------------------------
# Async entry point  (called from FastAPI / test_execution.py)
# ---------------------------------------------------------------------------

async def execute_steps(
    steps,
    browser_name: str,
    base_url: str,
    run_id: str,
    headed: bool = False,
    on_step_complete: Callable[[StepResult], Awaitable[None]] | None = None,
) -> ExecutionResult:
    """
    Execute a sequence of TestStep objects in a Playwright browser.

    Spawns a **separate Python subprocess** so Playwright gets a clean
    event loop — the only reliable approach on Windows.

    Parameters
    ----------
    steps : list[TestStep]
        Ordered test steps to execute.
    browser_name : str
        One of "chromium", "firefox", "webkit".
    base_url : str
        The application base URL (used for relative navigations).
    run_id : str
        UUID of the test run — used for artifact storage.
    headed : bool
        Whether to launch the browser in headed mode.
    on_step_complete : callback
        Optional async callback invoked after each step finishes.

    Returns
    -------
    ExecutionResult with per-step results and aggregate counts.
    """
    artifact_dir = get_artifact_dir(run_id)
    os.makedirs(artifact_dir, exist_ok=True)

    # Serialise steps to plain dicts
    step_data = [
        {
            "order": s.order,
            "action": s.action,
            "selector": s.selector,
            "value": s.value,
            "description": s.description,
        }
        for s in steps
    ]

    payload = json.dumps({
        "steps": step_data,
        "browser_name": browser_name,
        "base_url": base_url,
        "artifact_dir": os.path.abspath(artifact_dir),
        "headed": headed,
        "step_timeout_ms": settings.step_timeout_ms,
        "navigation_timeout_ms": settings.navigation_timeout_ms,
    })

    python_exe = sys.executable  # same interpreter that runs the server

    # Run in a thread so we don't block the event loop
    result = await asyncio.to_thread(
        functools.partial(
            subprocess.run,
            [python_exe, "-c", _EXECUTOR_SCRIPT],
            input=payload,
            capture_output=True,
            text=True,
            timeout=settings.execution_timeout_s,
        )
    )

    # Parse subprocess output
    stdout = (result.stdout or "").strip()
    stderr = (result.stderr or "").strip()

    if stderr:
        logger.debug("Step executor stderr:\n%s", stderr)

    exec_result = ExecutionResult()

    if not stdout:
        exec_result.status = "error"
        exec_result.error_message = (
            f"Subprocess exited {result.returncode} with no output.\n"
            f"stderr: {stderr[:2000]}"
        )
        return exec_result

    try:
        data = json.loads(stdout)
    except json.JSONDecodeError:
        exec_result.status = "error"
        exec_result.error_message = (
            f"Failed to parse subprocess JSON.\nstdout: {stdout[:2000]}\n"
            f"stderr: {stderr[:2000]}"
        )
        return exec_result

    # Populate ExecutionResult from parsed JSON
    exec_result.status = data.get("status", "error")
    exec_result.total = data.get("total", 0)
    exec_result.passed = data.get("passed", 0)
    exec_result.failed = data.get("failed", 0)
    exec_result.skipped = data.get("skipped", 0)
    exec_result.duration_ms = data.get("duration_ms", 0)
    exec_result.error_message = data.get("error_message")
    exec_result.trace_path = data.get("trace_path")
    exec_result.video_path = data.get("video_path")

    for sr_data in data.get("step_results", []):
        exec_result.step_results.append(StepResult(
            order=sr_data["order"],
            action=sr_data["action"],
            selector=sr_data.get("selector"),
            value=sr_data.get("value"),
            description=sr_data.get("description"),
            status=sr_data.get("status", "passed"),
            error_message=sr_data.get("error_message"),
            screenshot_path=sr_data.get("screenshot_path"),
            duration_ms=sr_data.get("duration_ms", 0),
        ))

    # Fire per-step callbacks
    if on_step_complete:
        for sr in exec_result.step_results:
            await on_step_complete(sr)

    return exec_result
