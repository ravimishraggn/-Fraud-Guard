import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class DocumentResponse(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    uploaded_by: uuid.UUID
    original_filename: Optional[str] = None
    mime_type: Optional[str] = None
    file_size_bytes: Optional[int] = None
    status: str
    doc_type: Optional[str] = None
    doc_type_confidence: Optional[float] = None
    overall_risk_score: int
    risk_level: str
    reviewed_by: Optional[uuid.UUID] = None
    reviewed_at: Optional[datetime] = None
    review_decision: Optional[str] = None
    review_note: Optional[str] = None
    processing_ms: Optional[int] = None
    created_at: datetime
    doc_metadata: dict = Field(default_factory=dict)

    class Config:
        from_attributes = True


class DocumentListResponse(BaseModel):
    items: list[DocumentResponse]
    total: int
    page: int
    page_size: int


class DocumentStatusResponse(BaseModel):
    id: uuid.UUID
    status: str
    overall_risk_score: int
    risk_level: str


class ReviewRequest(BaseModel):
    decision: str = Field(pattern="^(approved|rejected|escalated)$")
    note: Optional[str] = Field(default=None, max_length=2000)


class UploadResponse(BaseModel):
    id: uuid.UUID
    status: str
    original_filename: Optional[str] = None
    message: str
