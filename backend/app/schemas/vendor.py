import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class VendorResponse(BaseModel):
    id: uuid.UUID
    name: str
    gstin: Optional[str] = None
    pan: Optional[str] = None
    bank_account: Optional[str] = None
    bank_ifsc: Optional[str] = None
    is_whitelisted: bool
    risk_score: int
    total_invoices: int
    total_amount_paise: int
    flagged_count: int
    first_seen: datetime
    last_seen: datetime
    notes: Optional[str] = None

    class Config:
        from_attributes = True


class VendorUpdate(BaseModel):
    gstin: Optional[str] = None
    pan: Optional[str] = None
    bank_account: Optional[str] = None
    bank_ifsc: Optional[str] = None
    notes: Optional[str] = Field(default=None, max_length=5000)


class WhitelistToggleResponse(BaseModel):
    id: uuid.UUID
    is_whitelisted: bool
