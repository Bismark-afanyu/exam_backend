from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional

class Settings(BaseSettings):
    PROJECT_NAME: str = "FastAPI Firestore Backend"
    API_V1_STR: str = "/api/v1"
    
    # Firebase / Firestore Settings
    FIREBASE_PROJECT_ID: Optional[str] = None
    FIREBASE_PRIVATE_KEY: Optional[str] = None
    FIREBASE_CLIENT_EMAIL: Optional[str] = None
    
    # Optional: Path to service account json if preferred over env vars
    FIREBASE_SERVICE_ACCOUNT_PATH: Optional[str] = None
    
    # AI Config
    GEMINI_API_KEY: Optional[str] = None

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True
    )

settings = Settings()
