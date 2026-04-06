"""
AgentCore Client — HTTP adapter for invoking the remote AgentCore agent.

When ``settings.agentcore_enabled`` is True, the backend delegates the
LLM-heavy part of the pipeline (planner → DOM analyst → test generator →
reviewer → step generator → reviewer → code generator) to an AWS Bedrock
AgentCore Runtime endpoint, while keeping crawling, MCP enrichment and
database persistence local.
"""

import logging

import httpx

from app.config import get_settings
from app.schemas.agent import PageSnapshot

logger = logging.getLogger(__name__)
settings = get_settings()

# Generous timeout: the 7-agent pipeline can take several minutes
_TIMEOUT = httpx.Timeout(connect=30.0, read=600.0, write=30.0, pool=30.0)


async def invoke_agentcore_agent(
    *,
    title: str,
    description: str,
    base_url: str,
    page_snapshots: list[PageSnapshot],
    app_description: str | None = None,
    test_type: str = "functional",
    login_url: str | None = None,
    login_username: str | None = None,
    login_password: str | None = None,
    suite_name: str | None = None,
) -> dict:
    """
    POST the test generation request to the deployed AgentCore agent.

    The caller is responsible for crawling pages and passing pre-enriched
    ``page_snapshots``. This function serialises them, invokes the remote
    agent, and returns a dict matching the structure of the local
    ``run_workflow()`` return value.

    Returns:
        dict with keys: status, final_steps, test_cases, generated_code,
        code_file_name, progress_messages, error
    """
    endpoint = settings.agentcore_endpoint.rstrip("/")
    if not endpoint:
        raise ValueError("AGENTCORE_ENDPOINT is not configured")

    payload = {
        "title": title,
        "description": description,
        "base_url": base_url,
        "page_snapshots": [s.model_dump() for s in page_snapshots],
        "app_description": app_description,
        "test_type": test_type,
        "login_url": login_url,
        "login_username": login_username,
        "login_password": login_password,
        "suite_name": suite_name,
    }

    logger.info(
        "Invoking AgentCore agent at %s (title=%r, %d snapshots)",
        endpoint, title, len(page_snapshots),
    )

    async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
        response = await client.post(endpoint, json=payload)
        response.raise_for_status()
        result = response.json()

    logger.info(
        "AgentCore agent returned status=%s (%d test cases, %d steps)",
        result.get("status"),
        len(result.get("test_cases", [])),
        len(result.get("final_steps", [])),
    )

    return result
