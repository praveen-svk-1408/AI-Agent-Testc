"""
Bedrock Model Factory.

Provides a configured BedrockModel instance for all Strands Agent invocations.
Replaces the LangChain get_llm() factory from the original codebase.
"""

import os

from strands.models.bedrock import BedrockModel

_DEFAULT_MODEL_ID = os.environ.get(
    "BEDROCK_MODEL_ID",
    "us.anthropic.claude-3-haiku-20240307-v1:0",
)
_DEFAULT_REGION = os.environ.get("AWS_REGION", "us-east-1")


def get_model(
    temperature: float = 0.2,
    max_tokens: int = 4096,
    model_id: str | None = None,
) -> BedrockModel:
    """Create a BedrockModel configured for Claude Haiku.

    Args:
        temperature: Sampling temperature (0.0–1.0). Default 0.2 for deterministic output.
        max_tokens: Maximum tokens in the response.
        model_id:   Override the default model ID if needed (e.g. Sonnet for code gen).
    """
    return BedrockModel(
        model_id=model_id or _DEFAULT_MODEL_ID,
        region_name=_DEFAULT_REGION,
        temperature=temperature,
        max_tokens=max_tokens,
    )
