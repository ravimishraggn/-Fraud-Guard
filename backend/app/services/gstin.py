"""GSTIN verification — multi-level with Redis caching and graceful fallback.

Level 1: format validation (instant, no API)
Level 2: Redis cache (7-day TTL)
Level 3: primary API
Level 4: (fallback API slot)
Level 5: if all fail → status "unverified", never "invalid".
"""
import json
import logging
from typing import Optional

import httpx
import redis

from app.config import settings
from app.utils.validators import is_valid_gstin_format

logger = logging.getLogger(__name__)


class GSTINService:
    def __init__(self) -> None:
        self._redis: Optional[redis.Redis] = None

    @property
    def cache(self) -> Optional[redis.Redis]:
        if self._redis is None:
            try:
                self._redis = redis.from_url(settings.redis_url, decode_responses=True)
                self._redis.ping()
            except Exception:
                logger.warning("Redis unavailable — GSTIN cache disabled")
                self._redis = None
        return self._redis

    def verify(self, gstin: str) -> dict:
        """Return {"status": valid|invalid|unverified, "registered_name": str|None, "reason": str}."""
        gstin = (gstin or "").strip().upper()

        # Level 1 — format
        if not is_valid_gstin_format(gstin):
            return {"status": "invalid", "registered_name": None, "reason": "format_invalid"}

        # Level 2 — cache
        cached = self._cache_get(gstin)
        if cached:
            return cached

        # Level 3 — API (only when a key is configured)
        if not settings.gstin_api_key:
            result = {
                "status": "unverified",
                "registered_name": None,
                "reason": "api_not_configured",
            }
            return result

        try:
            response = httpx.get(
                settings.gstin_api_url,
                params={"gstin": gstin},
                headers={"Authorization": settings.gstin_api_key},
                timeout=10,
            )
            if response.status_code == 200:
                payload = response.json()
                name = (
                    payload.get("data", {}).get("lgnm")
                    or payload.get("legal_name")
                    or payload.get("registered_name")
                )
                result = {
                    "status": "valid" if name else "invalid",
                    "registered_name": name,
                    "reason": "api_verified" if name else "not_found",
                }
                self._cache_set(gstin, result)
                return result
            if response.status_code == 404:
                result = {"status": "invalid", "registered_name": None, "reason": "not_found"}
                self._cache_set(gstin, result)
                return result
            logger.warning("GSTIN API returned %s", response.status_code)
        except Exception:
            logger.exception("GSTIN API call failed")

        # Level 5 — degrade to unverified, NEVER invalid on API failure
        return {"status": "unverified", "registered_name": None, "reason": "api_unavailable"}

    def _cache_get(self, gstin: str) -> Optional[dict]:
        if not self.cache:
            return None
        try:
            raw = self.cache.get(f"gstin:{gstin}")
            return json.loads(raw) if raw else None
        except Exception:
            return None

    def _cache_set(self, gstin: str, result: dict) -> None:
        if not self.cache:
            return
        try:
            self.cache.setex(
                f"gstin:{gstin}", settings.gstin_cache_ttl_seconds, json.dumps(result)
            )
        except Exception:
            logger.warning("Failed to cache GSTIN result", exc_info=True)


gstin_service = GSTINService()
