"""Audit log writer — append-only event trail."""
import logging
import uuid
from typing import Optional

from sqlalchemy.orm import Session

from app.models import AuditLog

logger = logging.getLogger(__name__)


def write_audit(
    db: Session,
    tenant_id: uuid.UUID,
    event_type: str,
    user_id: Optional[uuid.UUID] = None,
    document_id: Optional[uuid.UUID] = None,
    event_data: Optional[dict] = None,
    ip_address: Optional[str] = None,
) -> None:
    """Write an audit event. Failures are logged, never propagated."""
    try:
        db.add(
            AuditLog(
                tenant_id=tenant_id,
                user_id=user_id,
                document_id=document_id,
                event_type=event_type,
                event_data=event_data or {},
                ip_address=ip_address,
            )
        )
        db.commit()
    except Exception:
        logger.exception("Failed to write audit log for %s", event_type)
        db.rollback()
