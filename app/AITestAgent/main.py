"""
AgentCore Runtime Entrypoint.

This is the main entry point for the BedrockAgentCoreApp. It wraps the
deterministic pipeline orchestrator and exposes it as an AgentCore-compatible
handler that streams progress events back to the caller.
"""

import json
import logging
import asyncio

from bedrock_agentcore import BedrockAgentCoreApp

from pipeline.state import PipelineState
from pipeline.orchestrator import run_pipeline

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = BedrockAgentCoreApp()


@app.entrypoint
async def handler(request):
    """Handle an incoming AgentCore Runtime invocation.

    Expected request payload (JSON):
    {
        "prompt": "...",           // Required: Natural language test description
        "title": "Login Test",    // Required: Test case title
        "description": "...",     // Required: Detailed test description
        "base_url": "http://...", // Required: Target application URL
        "test_type": "functional",// Optional: functional|e2e|integration|accessibility|visual|performance
        "app_description": "...", // Optional: Application description
        "login_url": "/login",    // Optional: Login page URL
        "login_username": "...",  // Optional: Test credentials
        "login_password": "...",  // Optional
        "suite_id": "uuid",       // Optional: Suite ID for cached snapshots
        "suite_name": "My Suite"  // Optional: Suite name for file naming
    }

    Streams progress messages as JSON events and returns the final pipeline state.
    """
    # Parse request payload
    payload = request if isinstance(request, dict) else json.loads(str(request))

    title = payload.get("title", payload.get("prompt", "Unnamed Test"))
    description = payload.get("description", payload.get("prompt", ""))
    base_url = payload.get("base_url", "")

    if not base_url:
        yield json.dumps({"status": "failed", "error": "base_url is required"})
        return

    # Initialize pipeline state
    state = PipelineState(
        title=title,
        description=description,
        base_url=base_url,
        app_description=payload.get("app_description"),
        test_type=payload.get("test_type", "functional"),
        login_url=payload.get("login_url"),
        login_username=payload.get("login_username"),
        login_password=payload.get("login_password"),
        suite_id=payload.get("suite_id"),
        suite_name=payload.get("suite_name"),
        max_tc_iterations=payload.get("max_tc_iterations", 2),
        max_iterations=payload.get("max_step_iterations", 3),
    )

    logger.info("Starting pipeline for: %s (base_url=%s, test_type=%s)",
                title, base_url, state.test_type)

    # Run the pipeline and stream progress
    # Note: AgentCore Browser Tool integration would be injected here
    # For now, browser_tool=None uses cached snapshots or empty fallback
    browser_tool = None

    async for progress_msg in run_pipeline(
        state=state,
        browser_tool=browser_tool,
    ):
        # Stream each progress message as an event
        yield json.dumps({"type": "progress", "message": progress_msg})

    # Return final state
    yield json.dumps({
        "type": "result",
        **state.to_dict(),
    })

    logger.info("Pipeline completed with status: %s", state.status)
