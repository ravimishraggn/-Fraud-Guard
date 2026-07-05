"""Health check endpoints."""
import logging

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.database import get_db

logger = logging.getLogger(__name__)
router = APIRouter(tags=["health"])


@router.get("/health")
def health():
    return {"status": "ok", "service": "fraudguard-api"}


@router.get("/health/detailed")
def health_detailed(db: Session = Depends(get_db)):
    checks: dict[str, str] = {}

    try:
        db.execute(text("SELECT 1"))
        checks["postgres"] = "ok"
    except Exception:
        logger.exception("Postgres health check failed")
        checks["postgres"] = "down"

    try:
        import redis

        from app.config import settings

        r = redis.from_url(settings.redis_url, socket_connect_timeout=3)
        r.ping()
        checks["redis"] = "ok"
    except Exception:
        checks["redis"] = "down"

    try:
        from app.services.storage import storage_service

        checks["minio"] = "ok" if storage_service.health_check() else "down"
    except Exception:
        checks["minio"] = "down"

    overall = "ok" if all(v == "ok" for v in checks.values()) else "degraded"
    return {"status": overall, "dependencies": checks}
