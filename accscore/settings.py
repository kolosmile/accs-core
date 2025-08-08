"""Environment configuration using Pydantic."""

from pydantic import BaseSettings, Field
from typing import Optional


class Settings(BaseSettings):
    """Application settings loaded from environment variables or .env file."""

    minio_endpoint: str = Field(..., env=["ACC_MINIO_ENDPOINT", "MINIO_ENDPOINT"])
    minio_access_key: str = Field(..., env=["ACC_MINIO_ACCESS_KEY", "MINIO_ACCESS_KEY"])
    minio_secret_key: str = Field(..., env=["ACC_MINIO_SECRET_KEY", "MINIO_SECRET_KEY"])
    minio_secure: bool = Field(False, env=["ACC_MINIO_SECURE", "MINIO_SECURE"])
    postgres_dsn: str = Field(..., env=["ACC_DB_URL", "POSTGRES_DSN"])
    rabbitmq_url: Optional[str] = Field(None, env="RABBITMQ_URL")
    service_url: Optional[str] = Field(None, env="SERVICE_URL")

    class Config:
        env_file = ".env"
        case_sensitive = False
