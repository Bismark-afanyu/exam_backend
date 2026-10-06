import warnings

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

DEFAULT_SECRET_KEY = "dev-secret-key-change-me-in-production"


class Settings(BaseSettings):
    PROJECT_NAME: str = "FastAPI Firestore Backend"
    API_V1_STR: str = "/api/v1"

    # "development" (default, permissive) or "production" (strict startup checks)
    ENVIRONMENT: str = "development"

    # Firebase / Firestore Settings
    FIREBASE_PROJECT_ID: str | None = None
    FIREBASE_PRIVATE_KEY: str | None = None
    FIREBASE_CLIENT_EMAIL: str | None = None
    FIREBASE_STORAGE_BUCKET: str | None = None

    # Optional: Path to service account json if preferred over env vars
    FIREBASE_SERVICE_ACCOUNT_PATH: str | None = None

    # CORS origins (comma-separated, e.g. "http://localhost:3000,https://example.com")
    BACKEND_CORS_ORIGINS: str | None = None

    # AI Config
    GEMINI_API_KEY: str | None = None

    # Auth Config
    SECRET_KEY: str = DEFAULT_SECRET_KEY
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7
    RESET_TOKEN_EXPIRE_MINUTES: int = 60

    # Email (Resend)
    RESEND_API_KEY: str | None = None
    RESEND_FROM_EMAIL: str | None = None
    FRONTEND_URL: str = "http://localhost:3000"

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", case_sensitive=True, extra="ignore"
    )

    @model_validator(mode="after")
    def _guard_production_secrets(self):
        """A forgeable secret means forgeable admin tokens — refuse to boot."""
        if self.ENVIRONMENT == "production":
            if self.SECRET_KEY in ("", DEFAULT_SECRET_KEY):
                raise ValueError(
                    "SECRET_KEY must be set to a strong random value in production. "
                    "Refusing to start with the development default."
                )
            if len(self.SECRET_KEY) < 32:
                warnings.warn(
                    "SECRET_KEY is shorter than 32 characters; use a long random secret.",
                    stacklevel=1,
                )
        return self


settings = Settings()
