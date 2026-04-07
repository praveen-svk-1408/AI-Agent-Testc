from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # Database
    database_url: str = "postgresql+asyncpg://postgres:password@localhost:5432/ai_agent_test"
    database_url_sync: str = "postgresql+psycopg2://postgres:password@localhost:5432/ai_agent_test"

    # App
    app_env: str = "development"
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    debug: bool = True

    # Artifacts
    artifacts_dir: str = "./artifacts"
    generated_tests_dir: str = "./generated-tests"

    # LLM provider: "bedrock", "groq", or "ollama"
    llm_provider: str = "bedrock"

    # AWS Bedrock
    bedrock_region: str = "us-east-1"
    bedrock_model: str = "anthropic.claude-3-haiku-20240307-v1:0"

    # LLM / Ollama
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "qwen2.5-coder:7b"
    llm_temperature: float = 0.2

    # Groq
    groq_api_key: str = ""
    groq_model: str = "llama-3.3-70b-versatile"

    # AgentCore Runtime (set to invoke deployed agent instead of local LangGraph)
    agentcore_enabled: bool = True
    agentcore_agent_arn: str = ""
    agentcore_region: str = "ap-south-1"
    aws_access_key_id: str = ""
    aws_secret_access_key: str = ""

    # Agent settings
    max_reverification_attempts: int = 3
    crawler_timeout_ms: int = 30000

    # Playwright MCP
    playwright_mcp_command: str = "npx @playwright/mcp"
    mcp_enrichment_enabled: bool = True

    # Step execution
    step_timeout_ms: int = 15000
    navigation_timeout_ms: int = 30000
    execution_timeout_s: int = 300

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


@lru_cache
def get_settings() -> Settings:
    return Settings()
