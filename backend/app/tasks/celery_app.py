"""Celery application configured against Redis."""
from celery import Celery

from app.config import settings

celery_app = Celery(
    "fraudguard",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=["app.tasks.process_document", "app.tasks.notifications"],
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    task_track_started=True,
)
