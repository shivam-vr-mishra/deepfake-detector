"""MinIO (S3-compatible) storage service.

Files are stored under a UUID key in an isolated bucket. The API layer never
references the original filename when retrieving data — it always uses the
``storage_key`` written into the ``Scan`` row.
"""
from __future__ import annotations

import io
import uuid
from datetime import timedelta
from typing import BinaryIO

from minio import Minio
from minio.error import S3Error

from app.core.config import settings
from app.core.logging import get_logger

log = get_logger(__name__)


class StorageService:
    def __init__(self) -> None:
        self.client = Minio(
            endpoint=settings.minio_endpoint,
            access_key=settings.minio_access_key,
            secret_key=settings.minio_secret_key,
            secure=settings.minio_secure,
        )
        self.bucket = settings.minio_bucket
        self._ensure_bucket()

    def _ensure_bucket(self) -> None:
        try:
            if not self.client.bucket_exists(self.bucket):
                self.client.make_bucket(self.bucket)
                log.info("storage.bucket_created", bucket=self.bucket)
        except S3Error as e:
            log.error("storage.bucket_error", error=str(e))
            raise

    @staticmethod
    def make_key(scan_type: str, extension: str) -> str:
        return f"{scan_type}/{uuid.uuid4().hex}{extension}"

    def upload_bytes(
        self, key: str, data: bytes, content_type: str = "application/octet-stream"
    ) -> str:
        self.client.put_object(
            self.bucket,
            key,
            io.BytesIO(data),
            length=len(data),
            content_type=content_type,
        )
        return key

    def upload_stream(
        self,
        key: str,
        stream: BinaryIO,
        size: int,
        content_type: str = "application/octet-stream",
    ) -> str:
        self.client.put_object(
            self.bucket,
            key,
            stream,
            length=size,
            content_type=content_type,
        )
        return key

    def download_bytes(self, key: str) -> bytes:
        response = self.client.get_object(self.bucket, key)
        try:
            return response.read()
        finally:
            response.close()
            response.release_conn()

    def delete(self, key: str) -> None:
        try:
            self.client.remove_object(self.bucket, key)
        except S3Error as e:
            log.warning("storage.delete_failed", key=key, error=str(e))

    def presigned_get(self, key: str, expires_minutes: int = 30) -> str:
        return self.client.presigned_get_object(
            self.bucket, key, expires=timedelta(minutes=expires_minutes)
        )


_default: StorageService | None = None


def get_storage() -> StorageService:
    global _default
    if _default is None:
        _default = StorageService()
    return _default
