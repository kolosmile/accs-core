"""Environment configuration using Pydantic."""

from pydantic import BaseSettings, Field
from typing import Optional


class Settings(BaseSettings):
    """Application settings loaded from environment variables or .env file."""

    minio_endpoint: str = Field(..., env="MINIO_ENDPOINT")
    minio_access_key: str = Field(..., env="MINIO_ACCESS_KEY")
    minio_secret_key: str = Field(..., env="MINIO_SECRET_KEY")
    postgres_dsn: str = Field(..., env="POSTGRES_DSN")
    rabbitmq_url: Optional[str] = Field(None, env="RABBITMQ_URL")
    service_url: Optional[str] = Field(None, env="SERVICE_URL")

    class Config:
        env_file = ".env"
        case_sensitive = False
