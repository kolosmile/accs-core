"""MinIO storage helpers."""

import io
from datetime import timedelta
from typing import Optional

from minio import Minio

from .settings import Settings


settings = Settings()
client = Minio(
    settings.minio_endpoint,
    access_key=settings.minio_access_key,
    secret_key=settings.minio_secret_key,
    secure=False,
)


def ensure_bucket(bucket: str) -> None:
    """Create bucket if it does not exist."""
    if not client.bucket_exists(bucket):
        client.make_bucket(bucket)


def put_object(bucket: str, name: str, data: bytes, content_type: Optional[str] = None) -> None:
    """Upload bytes to object storage."""
    client.put_object(bucket, name, io.BytesIO(data), len(data), content_type=content_type)


def get_object(bucket: str, name: str) -> bytes:
    """Download object as bytes."""
    response = client.get_object(bucket, name)
    try:
        return response.read()
    finally:
        response.close()
        response.release_conn()


def presign(bucket: str, name: str, expires: timedelta = timedelta(hours=1)) -> str:
    """Generate presigned download URL."""
    return client.presigned_get_object(bucket, name, expires=expires)
