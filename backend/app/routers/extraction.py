"""Extracted fields endpoints."""
import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.models import Document, ExtractedField, User
from app.schemas.extraction import ExtractedFieldResponse

router = APIRouter(prefix="/api/v1/documents", tags=["extraction"])


@router.get("/{document_id}/fields", response_model=list[ExtractedFieldResponse])
def get_extracted_fields(
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
    return (
        db.query(ExtractedField)
        .filter(ExtractedField.document_id == doc.id)
        .order_by(ExtractedField.field_name)
        .all()
    )
