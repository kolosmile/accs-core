"""Environment configuration using Pydantic."""

from typing import Optional

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables or .env file."""

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=False)

    minio_endpoint: str = Field(
        ..., validation_alias=AliasChoices("ACC_MINIO_ENDPOINT", "MINIO_ENDPOINT")
    )
    minio_access_key: str = Field(
        ..., validation_alias=AliasChoices("ACC_MINIO_ACCESS_KEY", "MINIO_ACCESS_KEY")
    )
    minio_secret_key: str = Field(
        ..., validation_alias=AliasChoices("ACC_MINIO_SECRET_KEY", "MINIO_SECRET_KEY")
    )
    minio_secure: bool = Field(
        False, validation_alias=AliasChoices("ACC_MINIO_SECURE", "MINIO_SECURE")
    )
    postgres_dsn: str = Field(
        ..., validation_alias=AliasChoices("ACC_DB_URL", "POSTGRES_DSN")
    )
    rabbitmq_url: Optional[str] = Field(None, validation_alias="RABBITMQ_URL")
    service_url: Optional[str] = Field(None, validation_alias="SERVICE_URL")
