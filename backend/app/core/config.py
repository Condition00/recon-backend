import secrets
from enum import Enum
from typing import Any

from pydantic import PostgresDsn, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class ModeEnum(str, Enum):
    development = "development"
    production = "production"
    testing = "testing"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        case_sensitive=True,
        env_file=(".env", "../.env"),   # Resolves regardless of if uvicorn is run from root or backend/
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # ── App ───────────────────────────────────────────────────
    MODE: ModeEnum = ModeEnum.production
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "RECON"

    # ── JWT / Auth ────────────────────────────────────────────
    # Aliasing to SECRET_KEY for common convention, will update security.py
    SECRET_KEY: str = secrets.token_urlsafe(32)
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    BOOTSTRAP_ADMIN_EMAILS: list[str] = ["nrikhil@gmail.com","recon2k26@gmail.com", "abhiram.shivam@gmail.com", "abhiramvsa7@gmail.com"]

    # ── Database ──────────────────────────────────────────────
    DATABASE_USER: str = "postgres"
    DATABASE_PASSWORD: str = "postgres"
    DATABASE_HOST: str = "localhost"
    DATABASE_PORT: int = 5432
    DATABASE_NAME: str = "recon_db"

    ASYNC_DATABASE_URI: PostgresDsn | str = ""

    # ── R2 / Cloudflare ───────────────────────────────────────
    R2_ACCOUNT_ID: str = ""
    R2_ACCESS_KEY_ID: str = ""
    R2_SECRET_ACCESS_KEY: str = ""
    R2_BUCKET_NAME: str = ""

    @field_validator("ASYNC_DATABASE_URI", mode="before")
    @classmethod
    def assemble_db_connection(cls, v: str | None, info) -> Any:
        if isinstance(v, str) and v == "":
            data = info.data
            # Skip SSL for local dev
            mode = data.get("MODE", ModeEnum.development)
            query = "ssl=require" if mode != ModeEnum.development else None
            return PostgresDsn.build(
                scheme="postgresql+asyncpg",
                username=data.get("DATABASE_USER"),
                password=data.get("DATABASE_PASSWORD"),
                host=data.get("DATABASE_HOST"),
                port=data.get("DATABASE_PORT"),
                path=data.get("DATABASE_NAME"),
                query=query,
            )
        return v

    @field_validator("BOOTSTRAP_ADMIN_EMAILS", mode="before")
    @classmethod
    def parse_bootstrap_admin_emails(cls, v: Any) -> list[str]:
        if v in (None, ""):
            return []
        if isinstance(v, str):
            return [email.strip() for email in v.split(",") if email.strip()]
        if isinstance(v, list):
            return [str(email).strip() for email in v if str(email).strip()]
        raise ValueError("BOOTSTRAP_ADMIN_EMAILS must be a comma-separated string or list")

    # ── Google OAuth ──────────────────────────────────────────
    GOOGLE_CLIENT_ID: str = ""
    GOOGLE_CLIENT_SECRET: str = ""
    GOOGLE_REDIRECT_URI: str = ""

    @field_validator("GOOGLE_REDIRECT_URI", mode="before")
    @classmethod
    def assemble_redirect_uri(cls, v: str | None, info) -> Any:
        """Dynamically assemble the redirect URI based on mode if left blank in .env"""
        if isinstance(v, str) and v == "":
            mode = info.data.get("MODE", ModeEnum.development)
            if mode == ModeEnum.development:
                return "http://localhost:8000/api/v1/auth/google/callback"
            else:
                return "https://api.traction-ai.me/api/v1/auth/google/callback"
        return v

    # ── OpenAI ────────────────────────────────────────────────
    OPENAI_API_KEY: str = ""

    LOGFIRE_TOKEN: str = ""
    LOGFIRE_ENVIRONMENT: str = "Staging"

    REDIS_URL: str = ""

settings = Settings()
