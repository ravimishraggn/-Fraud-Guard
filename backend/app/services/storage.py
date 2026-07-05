"""MinIO (S3-compatible) object storage service."""
import io
import logging
import uuid
from urllib.parse import urlparse

from minio import Minio
from minio.error import S3Error

from app.config import settings

logger = logging.getLogger(__name__)


class StorageService:
    def __init__(self) -> None:
        parsed = urlparse(settings.minio_url)
        self.client = Minio(
            parsed.netloc,
            access_key=settings.minio_access_key,
            secret_key=settings.minio_secret_key,
            secure=parsed.scheme == "https",
        )
        self.bucket = settings.minio_bucket

    def ensure_bucket(self) -> None:
        try:
            if not self.client.bucket_exists(self.bucket):
                self.client.make_bucket(self.bucket)
                logger.info("Created bucket %s", self.bucket)
        except S3Error:
            logger.exception("Failed to ensure bucket %s", self.bucket)
            raise

    def upload(self, tenant_id: str, filename: str, data: bytes, content_type: str) -> str:
        """Store a file and return its storage path (object key)."""
        self.ensure_bucket()
        key = f"{tenant_id}/{uuid.uuid4()}/{filename}"
        self.client.put_object(
            self.bucket,
            key,
            io.BytesIO(data),
            length=len(data),
            content_type=content_type,
        )
        return key

    def download(self, storage_path: str) -> bytes:
        response = self.client.get_object(self.bucket, storage_path)
        try:
            return response.read()
        finally:
            response.close()
            response.release_conn()

    def presigned_url(self, storage_path: str, expiry_seconds: int = 3600) -> str:
        from datetime import timedelta

        return self.client.presigned_get_object(
            self.bucket, storage_path, expires=timedelta(seconds=expiry_seconds)
        )

    def health_check(self) -> bool:
        try:
            self.client.bucket_exists(self.bucket)
            return True
        except Exception:
            return False


storage_service = StorageService()
