from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "ai-article-arranger"
    app_env: str = "development"
    database_url: str = "sqlite:///./app.db"
    openai_api_key: str | None = None
    openai_model: str = "gpt-4.1-mini"
    search_provider: str = "mock"
    google_search_api_key: str | None = None
    google_search_engine_id: str | None = None
    serpapi_api_key: str | None = None
    request_timeout_seconds: int = Field(default=20, ge=5, le=120)
    competitor_result_limit: int = Field(default=3, ge=1, le=10)
    polling_interval_seconds: int = Field(default=3, ge=1, le=30)
    user_agent: str = "ai-article-arranger/1.0 (+https://github.com/Kumet/article-arrange-app)"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def normalized_search_provider(self) -> str:
        return self.search_provider.strip().lower()

    @property
    def requires_openai_key(self) -> bool:
        return self.openai_model.strip().lower() != "mock"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
