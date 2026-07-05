"""Document endpoints: upload, list, detail, review, status."""
import logging
import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, File, HTTPException, Query, Request, UploadFile, status
from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.dependencies import get_current_user, require_roles
from app.models import Document, User
from app.models.document import (
    STATUS_APPROVED,
    STATUS_REJECTED,
    STATUS_REVIEW_REQUIRED,
    STATUS_UPLOADED,
)
from app.schemas.document import (
    DocumentListResponse,
    DocumentResponse,
    DocumentStatusResponse,
    ReviewRequest,
    UploadResponse,
)
from app.services.audit import write_audit
from app.services.storage import storage_service

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/documents", tags=["documents"])


def _get_tenant_document(document_id: uuid.UUID, user: User, db: Session) -> Document:
    doc = (
        db.query(Document)
        .filter(Document.id == document_id, Document.tenant_id == user.tenant_id)
        .first()
    )
    if doc is None:
        raise HTTPException(status_code=404, detail="Document not found")
    return doc


@router.post("", response_model=UploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_document(
    request: Request,
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if file.content_type not in settings.allowed_mime_types:
        raise HTTPException(
            status_code=415,
            detail="Unsupported file type. Please upload a PDF or an image (JPG/PNG).",
        )
    data = await file.read()
    if len(data) > settings.max_upload_bytes:
        raise HTTPException(status_code=413, detail="File is larger than the 50 MB limit")
    if len(data) == 0:
        raise HTTPException(status_code=400, detail="Uploaded file is empty")

    try:
        storage_path = storage_service.upload(
            str(user.tenant_id), file.filename or "document", data, file.content_type
        )
    except Exception:
        logger.exception("Storage upload failed")
        raise HTTPException(status_code=503, detail="File storage is temporarily unavailable")

    doc = Document(
        tenant_id=user.tenant_id,
        uploaded_by=user.id,
        original_filename=file.filename,
        mime_type=file.content_type,
        file_size_bytes=len(data),
        storage_path=storage_path,
        status=STATUS_UPLOADED,
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)

    write_audit(
        db,
        tenant_id=user.tenant_id,
        user_id=user.id,
        document_id=doc.id,
        event_type="document.uploaded",
        event_data={"filename": file.filename, "size": len(data)},
        ip_address=request.client.host if request.client else None,
    )

    # Queue async processing
    try:
        from app.tasks.process_document import process_document

        process_document.delay(str(doc.id))
    except Exception:
        logger.exception("Failed to enqueue processing for %s", doc.id)

    return UploadResponse(
        id=doc.id,
        status=doc.status,
        original_filename=doc.original_filename,
        message="Upload received. Processing has started.",
    )


@router.get("", response_model=DocumentListResponse)
def list_documents(
    status_filter: Optional[str] = Query(default=None, alias="status"),
    risk_level: Optional[str] = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    query = db.query(Document).filter(Document.tenant_id == user.tenant_id)
    if status_filter:
        query = query.filter(Document.status == status_filter.upper())
    if risk_level:
        query = query.filter(Document.risk_level == risk_level.lower())
    total = query.count()
    items = (
        query.order_by(desc(Document.overall_risk_score), desc(Document.created_at))
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return DocumentListResponse(items=items, total=total, page=page, page_size=page_size)


@router.get("/{document_id}", response_model=DocumentResponse)
def get_document(
    document_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return _get_tenant_document(document_id, user, db)


@router.get("/{document_id}/status", response_model=DocumentStatusResponse)
def get_document_status(
    document_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    doc = _get_tenant_document(document_id, user, db)
    return DocumentStatusResponse(
        id=doc.id,
        status=doc.status,
        overall_risk_score=doc.overall_risk_score,
        risk_level=doc.risk_level,
    )


@router.get("/{document_id}/file-url")
def get_document_file_url(
    document_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    doc = _get_tenant_document(document_id, user, db)
    if not doc.storage_path:
        raise HTTPException(status_code=404, detail="No file stored for this document")
    try:
        url = storage_service.presigned_url(doc.storage_path)
    except Exception:
        logger.exception("Failed to create presigned URL")
        raise HTTPException(status_code=503, detail="File storage is temporarily unavailable")
    return {"url": url}


@router.post("/{document_id}/review", response_model=DocumentResponse)
def review_document(
    document_id: uuid.UUID,
    payload: ReviewRequest,
    request: Request,
    user: User = Depends(require_roles("owner", "reviewer", "operator")),
    db: Session = Depends(get_db),
):
    doc = _get_tenant_document(document_id, user, db)
    if doc.status not in (STATUS_REVIEW_REQUIRED, STATUS_APPROVED, STATUS_REJECTED):
        raise HTTPException(
            status_code=409,
            detail="This document is still being processed and cannot be reviewed yet",
        )

    decision_status = {
        "approved": STATUS_APPROVED,
        "rejected": STATUS_REJECTED,
        "escalated": STATUS_REVIEW_REQUIRED,
    }[payload.decision]

    doc.status = decision_status
    doc.review_decision = payload.decision
    doc.review_note = payload.note
    doc.reviewed_by = user.id
    doc.reviewed_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(doc)

    write_audit(
        db,
        tenant_id=user.tenant_id,
        user_id=user.id,
        document_id=doc.id,
        event_type=f"document.review.{payload.decision}",
        event_data={"note": payload.note},
        ip_address=request.client.host if request.client else None,
    )
    return doc
