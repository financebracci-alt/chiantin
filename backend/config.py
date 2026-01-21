"""Configuration management for ecommbx Banking Platform."""

import os
import sys
from functools import lru_cache
from pathlib import Path
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings


# Get the directory where this config file lives
CONFIG_DIR = Path(__file__).parent.absolute()
ENV_FILE_PATH = CONFIG_DIR / ".env"


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # App
    APP_NAME: str = "ecommbx"
    APP_ENV: str = Field(default="development")
    DEBUG: bool = Field(default=False)  # Default to False for production safety
    
    # Security
    SECRET_KEY: str = Field(default="dev_secret_key_replace_in_production")
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30
    
    # Database - NO DEFAULTS that could cause silent fallback
    MONGO_URL: str = Field(default="mongodb://localhost:27017")
    DATABASE_NAME: str = Field(default="")  # Empty default - will be validated
    
    # Storage
    S3_PROVIDER: str = "local"  # local, minio, aws
    S3_ENDPOINT: str | None = None
    S3_ACCESS_KEY: str | None = None
    S3_SECRET_KEY: str | None = None
    S3_REGION: str = "us-east-1"
    S3_BUCKET: str = "atlas-banking"
    S3_USE_SSL: bool = False
    STORAGE_BASE_PATH: str = "/app/storage"
    
    # Seeding
    SEED_SUPERADMIN_EMAIL: str = "admin@atlas.local"
    SEED_SUPERADMIN_PASSWORD: str = "Admin@123456"
    
    # CORS
    FRONTEND_URL: str = Field(default="http://localhost:3000")
    
    # Email (Resend)
    RESEND_API_KEY: str = Field(default="")
    SENDER_EMAIL: str = Field(default="noreply@ecommbx.io")
    
    @field_validator('DATABASE_NAME')
    @classmethod
    def validate_database_name(cls, v):
        """CRITICAL: Fail startup if DATABASE_NAME is not set."""
        if not v or v.strip() == "":
            print("=" * 60)
            print("FATAL ERROR: DATABASE_NAME environment variable is NOT SET!")
            print("=" * 60)
            print("The backend CANNOT start without a valid DATABASE_NAME.")
            print("Please set DATABASE_NAME in your environment variables.")
            print("=" * 60)
            sys.exit(1)
        return v
    
    class Config:
        # Only use .env file if it exists (production uses K8s secrets as env vars)
        env_file = str(ENV_FILE_PATH) if ENV_FILE_PATH.exists() else None
        env_file_encoding = "utf-8"
        case_sensitive = True
        # Read from environment variables (higher priority than .env)
        extra = "ignore"


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


settings = get_settings()
