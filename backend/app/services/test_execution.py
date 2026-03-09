"""
Test Execution Service.

Orchestrates Playwright test execution:
- Locates generated spec files
- Generates per-run Playwright config
- Executes tests via subprocess
- Parses results and collects artifacts
- Updates DB records and broadcasts WebSocket events
"""

import asyncio
import functools
import json
import logging
import os
import shutil
import subprocess
import traceback
import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.database import async_session
from app.models.artifact import Artifact
from app.models.test_case import TestCase
from app.models.test_run import TestRun
from app.models.test_suite import TestSuite
from app.services.artifact_manager import (
    collect_artifacts,
    get_artifact_dir,
    save_log_artifact,
)
from app.services.ws_manager import manager as ws_manager

logger = logging.getLogger(__name__)

settings = get_settings()


async def _find_spec_file(
    case_id: uuid.UUID, db: AsyncSession
) -> tuple[str, str, str]:
    """
    Find the spec file path for a test case.

    Returns (spec_file_path, suite_id_str, base_url).
    """
    case_result = await db.execute(
        select(TestCase).where(TestCase.id == case_id)
    )
    test_case = case_result.scalar_one_or_none()
    if not test_case:
        raise ValueError(f"Test case not found: {case_id}")

    suite_result = await db.execute(
        select(TestSuite).where(TestSuite.id == test_case.suite_id)
    )
    suite = suite_result.scalar_one_or_none()
    if not suite:
        raise ValueError(f"Test suite not found for case: {case_id}")

    suite_dir = os.path.join(settings.generated_tests_dir, str(suite.id))
    if not os.path.isdir(suite_dir):
        raise FileNotFoundError(f"Suite directory not found: {suite_dir}")

    from app.agents.code_generator import _sanitize_filename

    safe_suite = _sanitize_filename(suite.name)
    safe_test = _sanitize_filename(test_case.title)
    expected_name = f"{safe_suite}_{safe_test}.spec.ts"

    spec_path = os.path.join(suite_dir, expected_name)
    if not os.path.isfile(spec_path):
        # Fallback: find any spec file in the suite directory
        spec_files = [f for f in os.listdir(suite_dir) if f.endswith(".spec.ts")]
        if not spec_files:
            raise FileNotFoundError(f"No spec files found in: {suite_dir}")
        spec_path = os.path.join(suite_dir, spec_files[0])

    return spec_path, str(suite.id), suite.base_url


def _generate_run_config(
    suite_id: str,
    base_url: str,
    run_id: str,
    browser: str,
) -> str:
    """
    Generate a per-run playwright.config.ts file.

    Returns the absolute path of the generated config file.
    """
    gen_dir = os.path.abspath(settings.generated_tests_dir)
    artifact_dir = get_artifact_dir(run_id)
    os.makedirs(artifact_dir, exist_ok=True)

    # Compute relative path from generated-tests dir to artifact dir
    rel_output = os.path.relpath(artifact_dir, gen_dir).replace(os.sep, "/")

    browser_devices = {
        "chromium": "Desktop Chrome",
        "firefox": "Desktop Firefox",
        "webkit": "Desktop Safari",
    }
    device = browser_devices.get(browser, "Desktop Chrome")

    config_content = (
        "import { defineConfig, devices } from '@playwright/test';\n"
        "\n"
        "export default defineConfig({\n"
        f"  testDir: './{suite_id}',\n"
        "  timeout: 60000,\n"
        "  fullyParallel: false,\n"
        "  retries: 0,\n"
        "  workers: 1,\n"
        "  reporter: [\n"
        f"    ['json', {{ outputFile: '{rel_output}/results.json' }}],\n"
        "    ['list'],\n"
        "  ],\n"
        "  use: {\n"
        f"    baseURL: '{base_url}',\n"
        "    trace: 'on',\n"
        "    screenshot: 'on',\n"
        "    video: 'on',\n"
        "    actionTimeout: 15000,\n"
        "    navigationTimeout: 30000,\n"
        "  },\n"
        "  projects: [\n"
        "    {\n"
        f"      name: '{browser}',\n"
        f"      use: {{ ...devices['{device}'] }},\n"
        "    },\n"
        "  ],\n"
        f"  outputDir: '{rel_output}',\n"
        "});\n"
    )

    config_path = os.path.join(
        gen_dir,
        f"playwright.run.{run_id}.config.ts",
    )
    with open(config_path, "w", encoding="utf-8") as f:
        f.write(config_content)

    return config_path


def _get_npx_cmd() -> str:
    """Locate the npx executable, preferring .cmd on Windows."""
    for name in ("npx.cmd", "npx"):
        path = shutil.which(name)
        if path:
            return path
    raise RuntimeError("npx not found in PATH. Ensure Node.js is installed.")


def _get_npm_cmd() -> str:
    """Locate the npm executable, preferring .cmd on Windows."""
    for name in ("npm.cmd", "npm"):
        path = shutil.which(name)
        if path:
            return path
    raise RuntimeError("npm not found in PATH. Ensure Node.js is installed.")


async def _ensure_playwright_deps():
    """Ensure @playwright/test is available in the generated-tests directory."""
    gen_dir = os.path.abspath(settings.generated_tests_dir)
    pkg_json_path = os.path.join(gen_dir, "package.json")
    node_modules = os.path.join(gen_dir, "node_modules")

    if not os.path.isfile(pkg_json_path):
        with open(pkg_json_path, "w", encoding="utf-8") as f:
            json.dump(
                {
                    "name": "generated-tests",
                    "private": True,
                    "devDependencies": {"@playwright/test": "^1.49.0"},
                },
                f,
                indent=2,
            )

    if not os.path.isdir(node_modules):
        logger.info("Installing @playwright/test in generated-tests directory...")
        npm_cmd = _get_npm_cmd()

        result = await asyncio.to_thread(
            functools.partial(
                subprocess.run,
                [npm_cmd, "install"],
                cwd=gen_dir,
                capture_output=True,
                text=True,
                timeout=120,
            )
        )
        if result.returncode != 0:
            raise RuntimeError(
                f"npm install failed (exit {result.returncode}): {result.stderr}"
            )
        logger.info("@playwright/test installed successfully")


import re

_ANSI_RE = re.compile(r"\x1b\[[0-9;]*m")


def _extract_errors_from_json(result_json: dict | None) -> str:
    """Extract clean error messages from a Playwright JSON report."""
    if not result_json:
        return ""
    errors: list[str] = []
    try:
        def walk_suites(suite: dict):
            for spec in suite.get("specs", []):
                for test in spec.get("tests", []):
                    for result in test.get("results", []):
                        if result.get("status") == "failed":
                            err = result.get("error", {})
                            msg = err.get("message", "")
                            # Strip ANSI escape codes
                            msg = _ANSI_RE.sub("", msg)
                            loc = err.get("location", {})
                            line = loc.get("line", "")
                            fname = spec.get("title", "")
                            prefix = f"{fname} (line {line}): " if line else ""
                            if msg:
                                errors.append(f"{prefix}{msg.strip()}")
            for child in suite.get("suites", []):
                walk_suites(child)

        for suite in result_json.get("suites", []):
            walk_suites(suite)
    except Exception:
        pass
    return "\n\n".join(errors)


def _extract_summary(result_json: dict | None) -> dict | None:
    """Extract a concise summary from a Playwright JSON report."""
    if not result_json:
        return None
    try:
        total = 0
        passed = 0
        failed = 0
        skipped = 0

        def count_tests(suite: dict):
            nonlocal total, passed, failed, skipped
            for spec in suite.get("specs", []):
                for test in spec.get("tests", []):
                    for result in test.get("results", []):
                        total += 1
                        st = result.get("status", "")
                        if st == "passed":
                            passed += 1
                        elif st == "failed":
                            failed += 1
                        elif st == "skipped":
                            skipped += 1
            for child in suite.get("suites", []):
                count_tests(child)

        for suite in result_json.get("suites", []):
            count_tests(suite)

        return {
            "total": total,
            "passed": passed,
            "failed": failed,
            "skipped": skipped,
            "duration": result_json.get("stats", {}).get("duration", 0),
        }
    except Exception:
        return None


async def execute_test_run(run_id: uuid.UUID):
    """
    Execute a test run in the background.

    1. Look up the run, test case, and suite
    2. Find the spec file on disk
    3. Generate a per-run Playwright config
    4. Execute via subprocess (thread pool for Windows compatibility)
    5. Parse results and collect artifacts
    6. Update DB record and broadcast final status
    """
    run_id_str = str(run_id)

    async with async_session() as db:
        try:
            # Fetch the run record
            run_result = await db.execute(
                select(TestRun).where(TestRun.id == run_id)
            )
            run = run_result.scalar_one_or_none()
            if not run:
                logger.error("Test run not found: %s", run_id)
                return

            # --- Mark as running ---
            run.status = "running"
            run.started_at = datetime.now(timezone.utc)
            await db.commit()

            await ws_manager.broadcast(run_id_str, {
                "event": "status_change",
                "status": "running",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            })

            # --- Find spec file ---
            spec_path, suite_id, base_url = await _find_spec_file(run.case_id, db)
            spec_filename = os.path.basename(spec_path)

            await ws_manager.broadcast(run_id_str, {
                "event": "test_step",
                "step": f"Found test file: {spec_filename}",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            })

            # --- Ensure dependencies ---
            await _ensure_playwright_deps()

            await ws_manager.broadcast(run_id_str, {
                "event": "test_step",
                "step": "Dependencies verified",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            })

            # --- Generate per-run config ---
            config_path = _generate_run_config(
                suite_id, base_url, run_id_str, run.browser
            )
            config_filename = os.path.basename(config_path)

            # --- Build command ---
            npx_cmd = _get_npx_cmd()

            cmd = [
                npx_cmd,
                "playwright",
                "test",
                spec_filename,
                f"--config={config_filename}",
                f"--project={run.browser}",
            ]
            if run.headed:
                cmd.append("--headed")

            gen_dir = os.path.abspath(settings.generated_tests_dir)

            logger.info("Executing: %s in %s", " ".join(cmd), gen_dir)
            await ws_manager.broadcast(run_id_str, {
                "event": "test_step",
                "step": f"Starting Playwright test ({run.browser})...",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            })

            # --- Run subprocess in thread pool (Windows-compatible) ---
            result = await asyncio.to_thread(
                functools.partial(
                    subprocess.run,
                    cmd,
                    cwd=gen_dir,
                    capture_output=True,
                    text=True,
                    timeout=300,
                )
            )

            stdout_text = result.stdout or ""
            stderr_text = result.stderr or ""

            # Broadcast output lines
            for line in stdout_text.splitlines():
                line = line.strip()
                if line:
                    await ws_manager.broadcast(run_id_str, {
                        "event": "test_step",
                        "step": line,
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    })

            # --- Determine outcome ---
            completed_at = datetime.now(timezone.utc)
            duration_ms = int(
                (completed_at - run.started_at).total_seconds() * 1000
            )

            # Parse JSON results if available
            artifact_dir = get_artifact_dir(run_id_str)
            results_json_path = os.path.join(artifact_dir, "results.json")
            result_summary_raw = None
            if os.path.isfile(results_json_path):
                try:
                    with open(results_json_path, "r", encoding="utf-8") as f:
                        result_summary_raw = json.load(f)
                except json.JSONDecodeError:
                    logger.warning("Failed to parse results.json")

            final_status = "passed" if result.returncode == 0 else "failed"

            # --- Collect artifacts ---
            artifacts = await collect_artifacts(run_id, artifact_dir, db)

            # Also collect from test-results dir (Playwright default output)
            test_results_dir = os.path.join(gen_dir, "test-results")
            if os.path.isdir(test_results_dir):
                artifacts += await collect_artifacts(run_id, test_results_dir, db)

            # Save stdout and stderr as log artifacts
            await save_log_artifact(
                run_id, stdout_text, "stdout.log", db
            )
            if stderr_text:
                await save_log_artifact(run_id, stderr_text, "stderr.log", db)

            # --- Update run record ---
            run_result2 = await db.execute(
                select(TestRun).where(TestRun.id == run_id)
            )
            run = run_result2.scalar_one_or_none()
            if run:
                run.status = final_status
                run.completed_at = completed_at
                run.duration_ms = duration_ms
                run.result_summary = _extract_summary(result_summary_raw)
                if final_status == "failed":
                    # Try to get clean error from JSON results first
                    error_ctx = _extract_errors_from_json(result_summary_raw)
                    if not error_ctx:
                        # Fallback: use stdout tail + stderr
                        error_lines = stdout_text.strip().splitlines()[-20:]
                        error_ctx = _ANSI_RE.sub("", "\n".join(error_lines))
                        if stderr_text:
                            error_ctx += "\n\n--- stderr ---\n" + stderr_text
                    run.error_message = error_ctx[:5000] or "Test failed (no output)"

            await db.commit()

            # --- Broadcast completion ---
            await ws_manager.broadcast(run_id_str, {
                "event": "status_change",
                "status": final_status,
                "timestamp": completed_at.isoformat(),
            })

            # Broadcast artifact-ready events
            for artifact in artifacts:
                await ws_manager.broadcast(run_id_str, {
                    "event": "artifact_ready",
                    "artifact": {
                        "id": str(artifact.id),
                        "artifact_type": artifact.artifact_type,
                        "file_name": artifact.file_name,
                        "mime_type": artifact.mime_type,
                        "file_size": artifact.file_size,
                    },
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                })

            logger.info(
                "Test run %s completed: %s (%dms)",
                run_id,
                final_status,
                duration_ms,
            )

        except Exception as e:
            tb = traceback.format_exc()
            error_msg = f"{str(e) or repr(e)}\n\n{tb}"[:5000]
            logger.error(
                "Test execution failed for run %s: %s\n%s", run_id, e, tb
            )

            # Roll back current session to clear any dirty state
            try:
                await db.rollback()
            except Exception:
                pass

            # Use a fresh session to persist the error status
            try:
                async with async_session() as err_db:
                    err_run_result = await err_db.execute(
                        select(TestRun).where(TestRun.id == run_id)
                    )
                    err_run = err_run_result.scalar_one_or_none()
                    if err_run:
                        err_run.status = "error"
                        err_run.completed_at = datetime.now(timezone.utc)
                        err_run.error_message = error_msg or "Unknown error"
                        if err_run.started_at:
                            err_run.duration_ms = int(
                                (err_run.completed_at - err_run.started_at).total_seconds()
                                * 1000
                            )
                    await err_db.commit()
            except Exception:
                logger.error("Failed to update run status: %s", traceback.format_exc())

            await ws_manager.broadcast(run_id_str, {
                "event": "status_change",
                "status": "error",
                "error_message": error_msg,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            })

        finally:
            # Clean up the run-specific config file
            config_file = os.path.join(
                os.path.abspath(settings.generated_tests_dir),
                f"playwright.run.{run_id_str}.config.ts",
            )
            if os.path.isfile(config_file):
                try:
                    os.remove(config_file)
                except OSError:
                    pass
