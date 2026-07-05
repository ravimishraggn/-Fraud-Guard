"""Async notification tasks."""
import logging

from app.tasks.celery_app import celery_app
from app.services.notification import notify_review_required

logger = logging.getLogger(__name__)


@celery_app.task(max_retries=2, default_retry_delay=30)
def send_review_notification(to: str, filename: str, risk_level: str, flag_count: int):
    sent = notify_review_required(to, filename, risk_level, flag_count)
    if not sent:
        logger.info("Review notification for %s not sent (SMTP unavailable)", filename)
