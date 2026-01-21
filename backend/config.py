"""Configuration management for ecommbx Banking Platform."""

import os
from functools import lru_cache
from pathlib import Path
from pydantic import Field
from pydantic_settings import BaseSettings


# Get the directory where this config file lives
CONFIG_DIR = Path(__file__).parent.absolute()
ENV_FILE_PATH = CONFIG_DIR / ".env"


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # App
    APP_NAME: str = "ecommbx"
    APP_ENV: str = Field(default="production")
    DEBUG: bool = Field(default=False)
    
    # Security - No hardcoded defaults for sensitive values
    SECRET_KEY: str = Field(default="")
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30
    
    # Database - Read from environment
    MONGO_URL: str = Field(default="mongodb://localhost:27017")
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
    
    # Seeding - Configurable via environment
    SEED_SUPERADMIN_EMAIL: str = Field(default="admin@ecommbx.io")
    SEED_SUPERADMIN_PASSWORD: str = Field(default="Admin@123456")
    
    # URLs - Read from environment
    FRONTEND_URL: str = Field(default="")
    
    # Email (Resend) - No hardcoded API keys
    RESEND_API_KEY: str = Field(default="")
    SENDER_EMAIL: str = Field(default="noreply@ecommbx.io")
    
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
