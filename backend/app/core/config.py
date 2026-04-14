import secrets
from enum import Enum
from typing import Any

from pydantic import PostgresDsn, field_validator, model_validator
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
    MODE: ModeEnum = ModeEnum.development
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "RECON"
    APP_BASE_URL: str = "http://localhost:5173"
    API_BASE_URL: str = "http://localhost:8000"
    FRONTEND_REDIRECT_AFTER_LOGIN: str = "http://localhost:5173/auth/callback"
    ALLOWED_ORIGINS: list[str] = [
        "http://localhost:5173",
        "http://localhost:3000",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:3000",
        "http://testserver",
    ]
    TRUSTED_HOSTS: list[str] = [
        "localhost",
        "127.0.0.1",
        "testserver",
        "*.localhost",
    ]
    SESSION_COOKIE_NAME: str = "recon_session"
    SESSION_MAX_AGE_SECONDS: int = 600
    SESSION_SAME_SITE: str = "lax"
    SESSION_HTTPS_ONLY: bool = False

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
        """Build the Google callback URL from the API base URL if not provided."""
        if isinstance(v, str) and v == "":
            api_base_url = str(info.data.get("API_BASE_URL", "")).rstrip("/")
            api_v1 = str(info.data.get("API_V1_STR", "/api/v1"))
            if api_base_url:
                return f"{api_base_url}{api_v1}/auth/google/callback"
        return v

    # ── OpenAI ────────────────────────────────────────────────
    OPENAI_API_KEY: str = ""

    LOGFIRE_TOKEN: str = ""
    LOGFIRE_ENVIRONMENT: str = "Staging"

    FCM_SERVER_KEY: str = ""
    FCM_TOPIC: str = "participants"

    REDIS_URL: str = ""

    @field_validator("ALLOWED_ORIGINS", "TRUSTED_HOSTS", mode="before")
    @classmethod
    def parse_string_list(cls, v: Any) -> list[str]:
        if v in (None, ""):
            return []
        if isinstance(v, str):
            return [item.strip() for item in v.split(",") if item.strip()]
        if isinstance(v, list):
            return [str(item).strip() for item in v if str(item).strip()]
        raise ValueError("Expected a comma-separated string or list")

    @field_validator("APP_BASE_URL", "API_BASE_URL", "FRONTEND_REDIRECT_AFTER_LOGIN", mode="before")
    @classmethod
    def strip_base_urls(cls, v: Any) -> Any:
        if isinstance(v, str):
            return v.strip().rstrip("/")
        return v

    @field_validator("SESSION_SAME_SITE")
    @classmethod
    def validate_same_site(cls, v: str) -> str:
        normalized = v.lower()
        if normalized not in {"lax", "strict", "none"}:
            raise ValueError("SESSION_SAME_SITE must be one of: lax, strict, none")
        return normalized

    @model_validator(mode="after")
    def validate_production_settings(self) -> "Settings":
        if self.MODE != ModeEnum.production:
            return self

        missing_fields = [
            field_name
            for field_name in ("APP_BASE_URL", "API_BASE_URL", "FRONTEND_REDIRECT_AFTER_LOGIN")
            if not getattr(self, field_name)
        ]
        if missing_fields:
            raise ValueError(
                f"Missing required production settings: {', '.join(missing_fields)}"
            )

        if not self.ALLOWED_ORIGINS:
            raise ValueError("ALLOWED_ORIGINS must be configured in production")

        localhost_values = ("localhost", "127.0.0.1", "traction-ai.me")
        for value in (
            self.APP_BASE_URL,
            self.API_BASE_URL,
            self.FRONTEND_REDIRECT_AFTER_LOGIN,
            self.GOOGLE_REDIRECT_URI,
            *self.ALLOWED_ORIGINS,
        ):
            if any(token in value for token in localhost_values):
                raise ValueError("Production URL settings must not reference localhost or copied domains")

        if not self.SESSION_HTTPS_ONLY:
            raise ValueError("SESSION_HTTPS_ONLY must be true in production")

        return self

settings = Settings()
