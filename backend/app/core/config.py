"""Application configuration loaded from environment variables via pydantic-settings."""

from enum import Enum
from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Environment(str, Enum):
    LOCAL = "local"
    STAGING = "staging"
    PRODUCTION = "production"


class Settings(BaseSettings):
    """All application settings, loaded from environment variables.

    Free-tier limit defaults are provider-stated as of mid-2025.
    Re-verify at signup — providers change these without notice.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # --- Environment ---
    ENVIRONMENT: Environment = Environment.LOCAL

    # --- Database ---
    DATABASE_URL: str = "postgresql+asyncpg://jobapp:localdev@localhost:5432/jobapp"

    # --- Redis ---
    REDIS_URL: str = "redis://localhost:6379/0"

    # --- JWT ---
    JWT_SECRET_KEY: str = "CHANGE-ME-IN-PRODUCTION-use-a-long-random-string"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # --- CSRF ---
    CSRF_MAX_TOKEN_AGE_HOURS: int = 48

    # --- Encryption ---
    ENCRYPTION_MASTER_KEY: str = "KpdEvPzHiAqHupF2OjMut_SEFdtreqRWQdqb0D7nHzo="  # local dev only — NOT production-safe

    # --- Email (Resend) ---
    # Free tier: 100 emails/day — re-verify at https://resend.com/pricing
    RESEND_API_KEY: str = ""
    RESEND_DAILY_LIMIT: int = 100
    RESEND_FROM_EMAIL: str = "Job App Assistant <onboarding@resend.dev>"

    # --- JSearch API ---
    # Free tier: 200 req/month — re-verify at https://rapidapi.com
    JSEARCH_API_KEY: str = ""
    JSEARCH_MONTHLY_LIMIT: int = 200
    JSEARCH_PER_CYCLE_CAP: int = 6
    JSEARCH_FETCH_CRON: str = "0 6 * * *"

    # --- Groq LLM ---
    # Free tier: 1000 req/day, 12K tokens/min — re-verify at https://console.groq.com/docs/rate-limits
    GROQ_API_KEY: str = ""
    GROQ_DAILY_LIMIT: int = 1000
    LLM_PROVIDER: str = "groq"  # "groq" | "ollama"
    LLM_MODEL: str = "llama-3.3-70b-versatile"
    LLM_BATCH_SIZE: int = 5  # Jobs scored per LLM call

    # --- Object Storage (S3-compatible) ---
    STORAGE_PROVIDER: str = "local"  # "s3" | "local"
    STORAGE_ENDPOINT: str = ""
    STORAGE_BUCKET: str = "resumes"
    STORAGE_ACCESS_KEY: str = ""
    STORAGE_SECRET_KEY: str = ""
    STORAGE_LOCAL_PATH: str = "./data/uploads"

    # --- Frontend ---
    FRONTEND_URL: str = "http://localhost:5173"

    # --- Matching ---
    MATCH_SCORE_THRESHOLD: int = 60

    # --- OTP ---
    OTP_EXPIRE_MINUTES: int = 10
    OTP_MAX_ATTEMPTS: int = 5

    # --- Rate Limiting ---
    RATE_LIMIT_OTP_REQUEST: int = 5  # per minute per email
    RATE_LIMIT_OTP_VERIFY: int = 10  # per minute per IP
    RATE_LIMIT_GENERAL: int = 60  # per minute per IP
    RATE_LIMIT_LINKEDIN_INGEST: int = 30  # per minute per user_id

    # --- Admin ---
    ADMIN_TRIGGER_SECRET: str = ""  # generate with: openssl rand -hex 32

    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT == Environment.PRODUCTION

    @property
    def is_local(self) -> bool:
        return self.ENVIRONMENT == Environment.LOCAL


@lru_cache
def get_settings() -> Settings:
    """Cached settings singleton."""
    return Settings()
