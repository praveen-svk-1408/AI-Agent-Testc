"""
LLM Factory.

Returns a ChatBedrock, ChatGroq, or ChatOllama instance based on the LLM_PROVIDER
setting. All agents should use get_llm() instead of instantiating providers directly.
"""

from app.config import get_settings

settings = get_settings()


def get_llm(temperature: float | None = None, num_predict: int | None = None):
    """
    Returns a configured LLM instance.

    Args:
        temperature: Override the default llm_temperature from settings.
        num_predict: Max tokens hint (only honoured by Ollama; ignored for Groq/Bedrock).
    """
    temp = temperature if temperature is not None else settings.llm_temperature

    if settings.llm_provider == "bedrock":
        import boto3
        from langchain_aws import ChatBedrock
        bedrock_client = boto3.client(
            "bedrock-runtime",
            region_name=settings.bedrock_region,
            aws_access_key_id=settings.aws_access_key_id or None,
            aws_secret_access_key=settings.aws_secret_access_key or None,
        )
        return ChatBedrock(
            client=bedrock_client,
            model_id=settings.bedrock_model,
            model_kwargs={"temperature": temp},
        )
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
