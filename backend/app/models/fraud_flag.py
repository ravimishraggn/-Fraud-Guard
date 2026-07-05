import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, Float, ForeignKey, String, Text, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func
from sqlalchemy.types import TIMESTAMP

from app.database import Base

FLAG_TYPES = (
    "DUPLICATE_INVOICE",
    "INVALID_GSTIN",
    "AMOUNT_WORDS_MISMATCH",
    "FUTURE_DATE",
    "STALE_DATE",
    "SHARED_BANK_ACCOUNT",
    "NEW_VENDOR",
    "AMOUNT_EXCEEDS_LIMIT",
    "FREQUENCY_ANOMALY",
    "VENDOR_NOT_WHITELISTED",
    "MISSING_PO",
)

SEVERITIES = ("low", "medium", "high", "critical")


class FraudFlag(Base):
    __tablename__ = "fraud_flags"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    flag_type: Mapped[str] = mapped_column(String(100), nullable=False)
    severity: Mapped[str] = mapped_column(String(20), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    evidence: Mapped[dict] = mapped_column(JSONB, server_default=text("'{}'::jsonb"))
    confidence: Mapped[Optional[float]] = mapped_column(Float)
    is_false_positive: Mapped[bool] = mapped_column(Boolean, server_default=text("false"))
    false_positive_reason: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now()
    )
