"""
AgentCore Agent Configuration.

Simplified settings for the standalone AgentCore agent. Only LLM and agent
parameters are needed — no database, no filesystem paths, no web server config.
"""

from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # LLM provider: "bedrock" (primary for AgentCore), "groq", or "ollama"
    llm_provider: str = "bedrock"

    # LLM temperature
    llm_temperature: float = 0.2

    # Ollama (if testing locally)
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "qwen2.5-coder:7b"

    # Groq (if using as fallback)
    groq_api_key: str = ""
    groq_model: str = "llama-3.3-70b-versatile"

    # AWS Bedrock (primary for AgentCore deployment)
    aws_region: str = "us-east-1"
    bedrock_model_id: str = "us.meta.llama3-3-70b-instruct-v1:0"

    # Agent settings
    max_reverification_attempts: int = 3

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


@lru_cache()
def get_settings() -> Settings:
    return Settings()
