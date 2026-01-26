"""Configuration management for ecommbx Banking Platform."""

import os
from functools import lru_cache
from pathlib import Path
from pydantic import Field
from pydantic_settings import BaseSettings


CONFIG_DIR = Path(__file__).parent.absolute()
ENV_FILE_PATH = CONFIG_DIR / ".env"


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # App
    APP_NAME: str = Field(default="ecommbx")
    APP_ENV: str = Field(default="production")
    DEBUG: bool = Field(default=False)
    
    # Security - Read from environment
    SECRET_KEY: str = Field(default="")
    JWT_ALGORITHM: str = "HS256"
    # Access token set to 1 year (525600 minutes) to prevent session timeout for elderly users
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 525600
    REFRESH_TOKEN_EXPIRE_DAYS: int = 365
    
    # Database - Read from environment
    MONGO_URL: str = Field(default="")
    DATABASE_NAME: str = Field(default="")
    
    # Storage
    S3_PROVIDER: str = "local"
    S3_ENDPOINT: str | None = None
    S3_ACCESS_KEY: str | None = None
    S3_SECRET_KEY: str | None = None
    S3_REGION: str = "us-east-1"
    S3_BUCKET: str = "ecommbx-storage"
    S3_USE_SSL: bool = False
    STORAGE_BASE_PATH: str = "/app/storage"
    
    # Seeding - Read from environment
    SEED_SUPERADMIN_EMAIL: str = Field(default="")
    SEED_SUPERADMIN_PASSWORD: str = Field(default="")
    
    # URLs - Read from environment
    FRONTEND_URL: str = Field(default="")
    
    # Email - Read from environment
    RESEND_API_KEY: str = Field(default="")
    SENDER_EMAIL: str = Field(default="")
    
    class Config:
        env_file = str(ENV_FILE_PATH) if ENV_FILE_PATH.exists() else None
        env_file_encoding = "utf-8"
        case_sensitive = True
        extra = "ignore"


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


settings = get_settings()
