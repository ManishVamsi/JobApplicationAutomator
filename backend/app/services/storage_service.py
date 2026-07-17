"""Object storage abstraction — S3-compatible (Supabase/AWS/MinIO) and local filesystem.

The StorageService interface decouples resume file storage from Postgres,
keeping the DB lean (only metadata + parsed output).
"""

import os
import shutil
import uuid
from abc import ABC, abstractmethod
from pathlib import Path
from typing import BinaryIO

import boto3
from botocore.config import Config as BotoConfig

from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class StorageService(ABC):
    """Abstract interface for object storage."""

    @abstractmethod
    async def upload(
        self, key: str, data: bytes | BinaryIO, content_type: str
    ) -> str:
        """Upload a file and return the storage key."""
        ...

    @abstractmethod
    async def download(self, key: str) -> bytes:
        """Download a file by key."""
        ...

    @abstractmethod
    async def delete(self, key: str) -> None:
        """Delete a file by key."""
        ...

    @abstractmethod
    async def generate_presigned_url(self, key: str, expires_in: int = 3600) -> str:
        """Generate a short-lived download URL."""
        ...

    @staticmethod
    def make_key(user_id: str, filename: str) -> str:
        """Generate a namespaced storage key: resumes/{user_id}/{uuid}.{ext}"""
        ext = Path(filename).suffix
        return f"resumes/{user_id}/{uuid.uuid4()}{ext}"


class S3StorageService(StorageService):
    """S3-compatible storage (Supabase Storage, AWS S3, MinIO)."""

    def __init__(self) -> None:
        settings = get_settings()
        self._client = boto3.client(
            "s3",
            endpoint_url=settings.STORAGE_ENDPOINT or None,
            aws_access_key_id=settings.STORAGE_ACCESS_KEY,
            aws_secret_access_key=settings.STORAGE_SECRET_KEY,
            config=BotoConfig(signature_version="s3v4"),
        )
        self._bucket = settings.STORAGE_BUCKET

    async def upload(
        self, key: str, data: bytes | BinaryIO, content_type: str
    ) -> str:
        if isinstance(data, bytes):
            from io import BytesIO
            data = BytesIO(data)

        self._client.upload_fileobj(
            data,
            self._bucket,
            key,
            ExtraArgs={"ContentType": content_type},
        )
        logger.info("File uploaded to S3", key=key, bucket=self._bucket)
        return key

    async def download(self, key: str) -> bytes:
        from io import BytesIO
        buf = BytesIO()
        self._client.download_fileobj(self._bucket, key, buf)
        buf.seek(0)
        return buf.read()

    async def delete(self, key: str) -> None:
        self._client.delete_object(Bucket=self._bucket, Key=key)
        logger.info("File deleted from S3", key=key)

    async def generate_presigned_url(self, key: str, expires_in: int = 3600) -> str:
        url: str = self._client.generate_presigned_url(
            "get_object",
            Params={"Bucket": self._bucket, "Key": key},
            ExpiresIn=expires_in,
        )
        return url


class LocalStorageService(StorageService):
    """Local filesystem storage for development — avoids needing S3 for docker-compose up."""

    def __init__(self) -> None:
        settings = get_settings()
        self._base_path = Path(settings.STORAGE_LOCAL_PATH)
        self._base_path.mkdir(parents=True, exist_ok=True)

    def _full_path(self, key: str) -> Path:
        path = self._base_path / key
        path.parent.mkdir(parents=True, exist_ok=True)
        return path

    async def upload(
        self, key: str, data: bytes | BinaryIO, content_type: str
    ) -> str:
        path = self._full_path(key)
        if isinstance(data, bytes):
            path.write_bytes(data)
        else:
            with open(path, "wb") as f:
                shutil.copyfileobj(data, f)
        logger.info("File saved locally", path=str(path))
        return key

    async def download(self, key: str) -> bytes:
        path = self._full_path(key)
        return path.read_bytes()

    async def delete(self, key: str) -> None:
        path = self._full_path(key)
        if path.exists():
            path.unlink()
            logger.info("File deleted locally", path=str(path))

    async def generate_presigned_url(self, key: str, expires_in: int = 3600) -> str:
        # Local dev: return a direct file path (not a real presigned URL)
        return f"/api/v1/users/me/resume/download?key={key}"


def get_storage_service() -> StorageService:
    """Factory: return the appropriate storage backend based on config."""
    settings = get_settings()
    if settings.STORAGE_PROVIDER == "s3":
        return S3StorageService()
    return LocalStorageService()
