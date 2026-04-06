"""
LLM Factory for AgentCore Agent.

Returns a ChatBedrockConverse, ChatGroq, or ChatOllama instance based on the
LLM_PROVIDER setting. All agents use get_llm() instead of instantiating
providers directly.
"""

from config import get_settings

settings = get_settings()


def get_llm(temperature: float | None = None, num_predict: int | None = None):
    """
    Returns a configured LLM instance.

    Args:
        temperature: Override the default llm_temperature from settings.
        num_predict: Max tokens hint (mapped to max_tokens for Bedrock).
    """
    temp = temperature if temperature is not None else settings.llm_temperature

    if settings.llm_provider == "bedrock":
        from langchain_aws import ChatBedrockConverse
        kwargs = dict(
            model_id=settings.bedrock_model_id,
            region_name=settings.aws_region,
            temperature=temp,
        )
        if num_predict is not None:
            kwargs["max_tokens"] = num_predict
        return ChatBedrockConverse(**kwargs)
    elif settings.llm_provider == "groq":
        from langchain_groq import ChatGroq
        return ChatGroq(
            api_key=settings.groq_api_key,
            model=settings.groq_model,
            temperature=temp,
        )
    else:
        from langchain_ollama import ChatOllama
        kwargs = dict(
            model=settings.ollama_model,
            temperature=temp,
            base_url=settings.ollama_base_url,
        )
        if num_predict is not None:
            kwargs["num_predict"] = num_predict
        return ChatOllama(**kwargs)
