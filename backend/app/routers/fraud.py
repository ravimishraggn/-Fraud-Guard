"""Fraud flag endpoints."""
import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.models import Document, FraudFlag, User
from app.schemas.fraud import FraudFlagResponse

router = APIRouter(prefix="/api/v1/documents", tags=["fraud"])

SEVERITY_ORDER = {"critical": 0, "high": 1, "medium": 2, "low": 3}


@router.get("/{document_id}/flags", response_model=list[FraudFlagResponse])
def get_fraud_flags(
    document_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    doc = (
        db.query(Document)
        .filter(Document.id == document_id, Document.tenant_id == user.tenant_id)
        .first()
    )
    if doc is None:
        raise HTTPException(status_code=404, detail="Document not found")
    flags = db.query(FraudFlag).filter(FraudFlag.document_id == doc.id).all()
    return sorted(flags, key=lambda f: SEVERITY_ORDER.get(f.severity, 9))
