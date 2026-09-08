from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(extra="ignore")

    database_url: str


@lru_cache
def get_settings() -> Settings:
    # pydantic-settings populates fields from the environment; the type checker
    # cannot see that and reports the field as a missing argument.
    return Settings()  # pyright: ignore[reportCallIssue]
