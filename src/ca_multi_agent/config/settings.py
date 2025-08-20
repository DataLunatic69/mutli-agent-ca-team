# src/ca_multi_agent/config/settings.py
from pydantic_settings import BaseSettings
from pydantic import AnyUrl, Field
from functools import lru_cache
import secrets


class Settings(BaseSettings):
    # Project
    PROJECT_NAME: str = "CA Multi-Agent System"
    ENVIRONMENT: str = "development"  # development, staging, production
    DEBUG: bool = False

    # Database - Now just one URL
    DATABASE_URL: AnyUrl

    # File Storage - Local filesystem
    UPLOAD_DIR: str = "./uploads"

    # Security
    SECRET_KEY: str = Field(default_factory=lambda: secrets.token_urlsafe(32))
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    class Config:
        env_file = ".env"
        case_sensitive = True


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()