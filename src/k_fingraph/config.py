"""Environment-driven settings loader (single source of truth for config)."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    neo4j_uri: str
    neo4j_user: str = "neo4j"
    neo4j_password: str

    dart_api_key: str
    openai_api_key: str

    log_level: str = "INFO"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]
