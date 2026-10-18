from functools import lru_cache
from typing import Literal

from pydantic import AliasChoices, Field, model_validator
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
    cors_allowed_origins: list[str] = Field(
        default_factory=lambda: ["http://localhost:3000", "http://127.0.0.1:3000"]
    )

    @model_validator(mode="after")
    def validate_external_services(self) -> "Settings":
        if self.email_provider == "smtp":
            if not self.smtp_host:
                raise ValueError("SMTP_HOST is required when EMAIL_PROVIDER=smtp")
            if not self.smtp_from and not self.smtp_username:
                raise ValueError("SMTP_FROM or SMTP_USERNAME is required when EMAIL_PROVIDER=smtp")
            if bool(self.smtp_username) != bool(self.smtp_password):
                raise ValueError("SMTP_USERNAME and SMTP_PASSWORD must be configured together")
            if not self.smtp_use_tls:
                raise ValueError("SMTP_USE_TLS must be true when EMAIL_PROVIDER=smtp")
        if not self.cors_allowed_origins or "*" in self.cors_allowed_origins:
            raise ValueError("CORS_ALLOWED_ORIGINS must list explicit origins")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
