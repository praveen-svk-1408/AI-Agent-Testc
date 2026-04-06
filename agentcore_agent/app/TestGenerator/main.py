"""
AWS Bedrock AgentCore Runtime entrypoint for the AI Test Generator agent.

This module defines the BedrockAgentCoreApp that wraps the 7-agent LangGraph
workflow. It receives pre-crawled page snapshots + test parameters via JSON
and returns generated test cases, steps, and Playwright code.

Entrypoint: handler(input_event) -> dict
"""

import json
import logging

from bedrock_agentcore.runtime import BedrockAgentCoreApp

from workflow import run_workflow

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = BedrockAgentCoreApp()


@app.entrypoint
async def handler(input_event: dict) -> dict:
    """
    Entrypoint invoked by AgentCore Runtime.

    Expected input_event schema:
    {
        "title": str,               # Test suite title
        "description": str,         # Natural-language test requirement
        "base_url": str,            # Target application URL
        "page_snapshots": [         # Pre-crawled page snapshots (required)
            {
                "url": str,
                "title": str,
                "elements": [
                    {
                        "tag": str,
                        "type": str | null,
                        "role": str | null,
                        "text": str,
                        "selector": str,
                        "attributes": dict,
                        "is_visible": bool,
                        "is_interactive": bool
                    }
                ]
            }
        ],
        "app_description": str | null,   # Optional app context
        "test_type": str,                # "functional" | "e2e" | "accessibility" | ...
        "login_url": str | null,         # Optional login URL
        "login_username": str | null,    # Optional login username
        "login_password": str | null,    # Optional login password
        "suite_name": str | null         # Optional suite name for output naming
    }

    Returns:
    {
        "status": "success" | "failed",
        "test_cases": [...],            # IEEE 829 test case dicts
        "final_steps": [...],           # GeneratedTestStep dicts
        "generated_code": str | null,   # TypeScript .spec.ts file content
        "code_file_name": str | null,   # Suggested output filename
        "progress_messages": [...],     # Pipeline progress log
        "error": str | null             # Error message if failed
    }
    """
    logger.info("AgentCore handler invoked")

    # Parse input — handle both dict and JSON string
    if isinstance(input_event, str):
        try:
            input_event = json.loads(input_event)
        except json.JSONDecodeError as e:
            return {
                "status": "failed",
                "error": f"Invalid JSON input: {str(e)}",
                "test_cases": [],
                "final_steps": [],
                "generated_code": None,
                "code_file_name": None,
                "progress_messages": [],
            }

    # Validate required fields
    required = ["title", "description", "base_url", "page_snapshots"]
    missing = [f for f in required if not input_event.get(f)]
    if missing:
        return {
            "status": "failed",
            "error": f"Missing required fields: {', '.join(missing)}",
            "test_cases": [],
            "final_steps": [],
            "generated_code": None,
            "code_file_name": None,
            "progress_messages": [],
        }

    try:
        result = await run_workflow(
            title=input_event["title"],
            description=input_event["description"],
            base_url=input_event["base_url"],
            page_snapshots=input_event["page_snapshots"],
            app_description=input_event.get("app_description"),
            test_type=input_event.get("test_type", "functional"),
            login_url=input_event.get("login_url"),
            login_username=input_event.get("login_username"),
            login_password=input_event.get("login_password"),
            suite_name=input_event.get("suite_name"),
        )
        logger.info("AgentCore handler completed: status=%s", result.get("status"))
        return result

    except Exception as e:
        logger.exception("AgentCore handler failed")
        return {
            "status": "failed",
            "error": str(e),
            "test_cases": [],
            "final_steps": [],
            "generated_code": None,
            "code_file_name": None,
            "progress_messages": [f"Fatal error: {str(e)}"],
        }
