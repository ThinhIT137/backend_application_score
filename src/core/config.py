from functools import lru_cache

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        populate_by_name=True,
    )

    database_url: str
    jwt_secret: str = Field(
        ...,
        validation_alias=AliasChoices("JWT_ACCESSTOKEN", "jwt_secret", "JWT_SECRET"),
    )
    jwt_algorithm: str = "HS256"
    jwt_audience: str | None = None
    thpt_provider: str = "mock"
    dgnl_provider: str = "mock"


@lru_cache
def get_settings() -> Settings:
    return Settings()
