"""Configuration management for Project Atlas."""

import os
from functools import lru_cache
from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # App
    APP_NAME: str = "Project Atlas"
    APP_ENV: str = Field(default="development")
    DEBUG: bool = Field(default=True)
    
    # Security
    SECRET_KEY: str = Field(default="dev_secret_key_replace_in_production")
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30
    
    # Database
    MONGO_URL: str = Field(default="mongodb://localhost:27017")
    DATABASE_NAME: str = "atlas_banking"
    
    # Storage
    S3_PROVIDER: str = "local"  # local, minio, aws
    S3_ENDPOINT: str | None = None
    S3_ACCESS_KEY: str | None = None
    S3_SECRET_KEY: str | None = None
    S3_REGION: str = "us-east-1"
    S3_BUCKET: str = "atlas-banking"
    S3_USE_SSL: bool = False
    STORAGE_BASE_PATH: str = "/tmp/atlas_storage"
    
    # Seeding
    SEED_SUPERADMIN_EMAIL: str = "admin@atlas.local"
    SEED_SUPERADMIN_PASSWORD: str = "Admin@123456"
    
    # CORS
    FRONTEND_URL: str = Field(default="http://localhost:3000")
    
    class Config:
        env_file = ".env"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()