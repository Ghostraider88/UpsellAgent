"""Application configuration loaded from environment variables.

The app is designed to run fully in *mock mode* when no external API keys are
provided, so local development and tests need no third-party credentials.
"""
from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_env: str = "development"

    # SQLite default keeps the app runnable with zero infra (e.g. in CI/tests).
    database_url: str = "sqlite:///./upsell.db"
    redis_url: str = "redis://localhost:6379/0"

    # Mock people source. None (default) = auto: the deterministic mock roster is
    # used ONLY as a fallback when no real compliant source is configured, so it
    # disappears automatically once you add real keys. Set true to force mock on
    # (dev/demo) or false to never use it.
    enable_mock_data: bool | None = None

    # LLM
    anthropic_api_key: str | None = None
    anthropic_model: str = "claude-sonnet-4-6"

    # Azure OpenAI (for name extraction from news)
    azure_openai_api_key: str | None = None
    azure_openai_endpoint: str = "https://aoai-poc-prod.openai.azure.com/"
    azure_openai_deployment: str = "gpt-4-nano"
    azure_openai_api_version: str = "2024-08-01-preview"

    # Compliant data sources
    serpapi_api_key: str | None = None
    pdl_api_key: str | None = None
    apollo_api_key: str | None = None

    # Shadow / fallback scraping sources (disabled by default)
    enable_shadow_sources: bool = False
    # Provider that backs the shadow adapter (LinkedIn/Xing data is fetched via a
    # licensed provider, not a self-built scraper). "proxycurl" is the default.
    shadow_provider: str = "proxycurl"
    proxycurl_api_key: str | None = None
    brightdata_api_key: str | None = None
    # Hard cap on people fetched per company in shadow mode — keeps provider cost
    # bounded and avoids indiscriminate mass-harvesting of personal data.
    shadow_max_people: int = 25

    # Auth
    jwt_secret: str = "change-me-in-production"

    @property
    def llm_enabled(self) -> bool:
        return bool(self.anthropic_api_key)


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
