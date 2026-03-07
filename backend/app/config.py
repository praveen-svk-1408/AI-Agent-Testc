from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """Application configuration from environment variables."""
    
    # Database - SQLite by default (no compilation needed)
    # For PostgreSQL production use: postgresql://user:password@localhost:5432/ai_test_db
    DATABASE_URL: str = "sqlite:///./ai_test.db"
    
    # FastAPI
    DEBUG: bool = True
    API_TITLE: str = "AI-Agent Testing Platform"
    API_VERSION: str = "1.0.0"
    
    # Ollama
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "llama2"
    OLLAMA_TIMEOUT: int = 60
    
    # Playwright
    HEADLESS_BROWSER: bool = True
    BROWSER_TIMEOUT: int = 30000
    SCREENSHOT_DIR: str = "screenshots"
    
    # Application
    LOG_LEVEL: str = "INFO"
    MAX_CONCURRENT_TESTS: int = 5
    
    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
