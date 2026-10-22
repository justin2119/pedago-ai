"""Application settings loaded from environment variables and .env."""

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Typed application settings."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "pedago-ai"
    app_env: str = "development"
    cors_origins: list[str] = Field(default_factory=lambda: ["http://localhost:3000"])

    supabase_url: str = ""
    supabase_key: str = ""
    supabase_vector_table: str = "document_chunks"
    supabase_match_function: str = "match_document_chunks"
    embedding_dimensions: int = 1536

    model_base_url: str = ""
    model_api_key: str = ""
    model_name: str = "openai/gpt-6.1-sol"
    embedding_model_name: str = "text-embedding-3-small"


@lru_cache
def get_settings() -> Settings:
    """Return a cached Settings instance."""
    return Settings()
