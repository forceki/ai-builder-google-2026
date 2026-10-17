from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration, read from HEATMARK_* environment variables (or .env)."""

    model_config = SettingsConfigDict(env_prefix="HEATMARK_", env_file=".env", extra="ignore")

    database_url: str = "postgresql+asyncpg://heatmark:heatmark@localhost:5433/heatmark"
    redis_url: str = "redis://localhost:6380/0"
    # Create tables on API startup instead of running migrations (`alembic upgrade head`). Throwaway databases only.
    auto_create_tables: bool = False

    # Uploaded documents. "gcs" = Google Cloud Storage (Application Default Credentials);
    # "local" = storage_dir/<bucket>/<key>, for tests and offline work.
    storage_backend: Literal["gcs", "local"] = "gcs"
    gcp_project: str | None = None  # defaults to the project of the credentials
    # Service-account JSON key. If unset, Application Default Credentials are used.
    gcs_credentials_file: Path | None = None
    documents_bucket: str = "heatmark-documents"
    storage_dir: Path = Path("./var/storage")
    max_upload_mb: int = 50
    signed_url_minutes: int = 15

    cors_origins: list[str] = ["http://localhost:5173"]

    jwt_secret: SecretStr
    jwt_ttl_hours: int = 12
    demo_email: str = "demo@heatmark.app"
    demo_password: SecretStr = SecretStr("heatmark-demo")
    google_client_id: str | None = None
    google_client_secret: SecretStr | None = None
    google_allowed_domains: list[str] = []

    # Gemini (google-genai). Key from GEMINI_API_KEY in the environment or .env.
    gemini_api_key: SecretStr | None = Field(default=None, validation_alias="GEMINI_API_KEY")
    # Development: Flash for everything (cheap, has a free tier). For production accuracy,
    # set HEATMARK_EXTRACT_MODEL=gemini-4-argon and HEATMARK_EXTRACT_THINKING=HIGH.
    extract_model: str = "gemini-3.8-flash"
    fast_model: str = "gemini-3.8-flash"
    classify_thinking: str = "LOW"
    extract_thinking: str = "MEDIUM"
    explain_thinking: str = "LOW"
    max_output_tokens: int = 32768

    rule_set: str = "RS-2.1"
    checks_debounce_seconds: int = 15

    @field_validator("jwt_secret")
    @classmethod
    def _long_enough(cls, v: SecretStr) -> SecretStr:
        if len(v.get_secret_value()) < 32:
            raise ValueError("HEATMARK_JWT_SECRET must be at least 32 characters")
        return v

    @field_validator(
        "gcp_project", "gcs_credentials_file", "gemini_api_key", "google_client_id", "google_client_secret",
        mode="before",
    )
    @classmethod
    def _blank_is_unset(cls, v):
        return None if isinstance(v, str) and not v.strip() else v


@lru_cache
def get_settings() -> Settings:
    return Settings()
