import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class FraudFlagResponse(BaseModel):
    id: uuid.UUID
    document_id: uuid.UUID
    flag_type: str
    severity: str
    title: str
    description: str
    evidence: dict = Field(default_factory=dict)
    confidence: Optional[float] = None
    is_false_positive: bool = False
    created_at: datetime

    class Config:
        from_attributes = True


class FraudRuleResponse(BaseModel):
    id: uuid.UUID
    rule_name: str
    rule_type: str
    is_active: bool
    config: dict = Field(default_factory=dict)
    created_at: datetime

    class Config:
        from_attributes = True


class FraudRuleCreate(BaseModel):
    rule_name: str = Field(min_length=2, max_length=255)
    rule_type: str = Field(
        pattern="^(amount_limit|vendor_whitelist_only|frequency_limit|require_po|custom)$"
    )
    config: dict = Field(default_factory=dict)


class FraudRuleUpdate(BaseModel):
    rule_name: Optional[str] = None
    is_active: Optional[bool] = None
    config: Optional[dict] = None
