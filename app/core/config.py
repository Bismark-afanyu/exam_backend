from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "FastAPI Firestore Backend"
    API_V1_STR: str = "/api/v1"

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
    SECRET_KEY: str = "dev-secret-key-change-me-in-production"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", case_sensitive=True, extra="ignore"
    )


settings = Settings()
