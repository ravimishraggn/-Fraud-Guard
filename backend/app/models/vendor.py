import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import BigInteger, Boolean, ForeignKey, Integer, String, Text, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func
from sqlalchemy.types import TIMESTAMP

from app.database import Base


class Vendor(Base):
    __tablename__ = "vendors"
    __table_args__ = (UniqueConstraint("tenant_id", "name", name="uq_vendors_tenant_name"),)

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    gstin: Mapped[Optional[str]] = mapped_column(String(20))
    pan: Mapped[Optional[str]] = mapped_column(String(15))
    bank_account: Mapped[Optional[str]] = mapped_column(String(50), index=True)
    bank_ifsc: Mapped[Optional[str]] = mapped_column(String(20))
    is_whitelisted: Mapped[bool] = mapped_column(Boolean, server_default=text("false"))
    risk_score: Mapped[int] = mapped_column(Integer, server_default=text("0"))
    total_invoices: Mapped[int] = mapped_column(Integer, server_default=text("0"))
    # Money stored in paise (integer) — never floats.
    total_amount_paise: Mapped[int] = mapped_column(BigInteger, server_default=text("0"))
    flagged_count: Mapped[int] = mapped_column(Integer, server_default=text("0"))
    first_seen: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now()
    )
    last_seen: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now()
    )
    notes: Mapped[Optional[str]] = mapped_column(Text)
