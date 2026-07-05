"""Application settings loaded from environment variables."""
from functools import lru_cache

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Database
    database_url: str = "postgresql://fraudguard:fraudguard_local@localhost:5432/fraudguard"

    # Redis / Celery
    redis_url: str = "redis://localhost:6379/0"

    # Storage
    storage_type: str = "minio"  # minio | s3
    minio_url: str = "http://localhost:9000"
    minio_access_key: str = "fraudguard"
    minio_secret_key: str = "fraudguard_local"
    minio_bucket: str = "fraudguard-documents"

    # OpenAI
    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"

    # JWT
    jwt_secret: str = "local_dev_secret_change_in_prod"
    jwt_algorithm: str = "HS256"
    jwt_expiry_hours: int = 24
    jwt_refresh_expiry_days: int = 7

    # GSTIN verification
    gstin_api_key: str = ""
    gstin_api_url: str = "https://api.sandbox.co.in/gsp/assets/resolve-gstin-details"
    gstin_cache_ttl_seconds: int = 7 * 24 * 3600

    # Email
    smtp_host: str = "smtp.gmail.com"
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    email_from: str = "noreply@fraudguard.in"

    # App
    environment: str = "development"
    log_level: str = "INFO"
    allowed_origins: str = "http://localhost:3000"

    # Upload limits
    max_upload_bytes: int = 50 * 1024 * 1024  # 50 MB
    allowed_mime_types: tuple = (
        "application/pdf",
        "image/jpeg",
        "image/png",
        "image/webp",
        "image/tiff",
    )

    class Config:
        env_file = ".env"
        extra = "ignore"

    @property
    def origins_list(self) -> list[str]:
        return [o.strip() for o in self.allowed_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
