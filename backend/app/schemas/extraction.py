import uuid
from typing import Optional

from pydantic import BaseModel


class ExtractedFieldResponse(BaseModel):
    id: uuid.UUID
    document_id: uuid.UUID
    field_name: str
    raw_value: Optional[str] = None
    normalised_value: Optional[str] = None
    confidence: Optional[float] = None
    source: Optional[str] = None
    page_number: int = 1
    is_verified: bool = False
    corrected_value: Optional[str] = None

    class Config:
        from_attributes = True
