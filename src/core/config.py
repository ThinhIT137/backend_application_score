from functools import lru_cache
from typing import Literal

from pydantic import AliasChoices, Field, field_validator
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
    # Production must explicitly configure a real provider; do not fabricate exam scores.
    thpt_provider: Literal["mock", "http", "disabled"] = "disabled"
    dgnl_provider: Literal["mock", "http", "disabled"] = "disabled"
    thpt_api_url: str | None = None
    thpt_api_token: str | None = None
    dgnl_api_url: str | None = None
    dgnl_api_token: str | None = None
    email_provider: Literal["mock", "smtp"] = "mock"
    smtp_host: str | None = None
    smtp_port: int = 587
    smtp_username: str | None = None
    smtp_password: str | None = None
    smtp_from: str | None = None
    smtp_use_tls: bool = True
    # Optional SMS gateway accepting JSON {to, message}; server-side bearer credential.
    sms_gateway_url: str | None = None
    sms_gateway_token: str | None = None


@lru_cache
def get_settings() -> Settings:
    return Settings()


class ApiSecuritySettings(BaseSettings):
    # Explicit process environment only; no DB credentials required at app import.
    model_config = SettingsConfigDict(env_prefix="API_", extra="ignore")
    cors_origins: str = ""
    json_max_bytes: int = Field(default=1_048_576, ge=1024, le=10_485_760)
    auth_max_bytes: int = Field(default=16_384, ge=1024, le=65_536)
    auth_rate_limit: int = Field(default=60, ge=1, le=100_000)
    lookup_rate_limit: int = Field(default=120, ge=1, le=100_000)
    rate_window_seconds: int = Field(default=60, ge=1, le=3600)
    rate_max_buckets: int = Field(default=10_000, ge=1, le=100_000)

    @field_validator("cors_origins")
    @classmethod
    def explicit_origins(cls, value):
        from urllib.parse import urlsplit
        for origin in (part.strip() for part in value.split(",") if part.strip()):
            parsed = urlsplit(origin)
            if (parsed.scheme not in {"http", "https"} or not parsed.hostname or parsed.username
                    or parsed.password or parsed.query or parsed.fragment or parsed.path not in {"", "/"}
                    or "*" in origin):
                raise ValueError("CORS requires explicit HTTP(S) origins")
        return value

    def allowed_origins(self):
        return [origin.strip().rstrip("/") for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_api_security_settings() -> ApiSecuritySettings:
    return ApiSecuritySettings()
