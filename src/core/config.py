from functools import lru_cache
from typing import Literal

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
    thpt_provider: Literal["mock"] = "mock"
    dgnl_provider: Literal["mock"] = "mock"
    email_provider: Literal["mock", "smtp"] = "mock"
    smtp_host: str | None = None
    smtp_port: int = 587
    smtp_username: str | None = None
    smtp_password: str | None = None
    smtp_from: str | None = None
    smtp_use_tls: bool = True


@lru_cache
def get_settings() -> Settings:
    return Settings()
