from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    database_url: str
    jwt_secret: str
    jwt_algorithm: str = "HS256"
    jwt_audience: str | None = None
    thpt_provider: Literal["mock"] = "mock"
    dgnl_provider: Literal["mock"] = "mock"


@lru_cache
def get_settings() -> Settings:
    return Settings()
