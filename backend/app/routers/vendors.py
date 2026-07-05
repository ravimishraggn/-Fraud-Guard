"""Vendor endpoints: list, detail, whitelist toggle, update."""
import uuid

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user, require_roles
from app.models import Document, ExtractedField, User, Vendor
from app.schemas.vendor import VendorResponse, VendorUpdate, WhitelistToggleResponse
from app.services.audit import write_audit

router = APIRouter(prefix="/api/v1/vendors", tags=["vendors"])


def _get_tenant_vendor(vendor_id: uuid.UUID, user: User, db: Session) -> Vendor:
    vendor = (
        db.query(Vendor)
        .filter(Vendor.id == vendor_id, Vendor.tenant_id == user.tenant_id)
        .first()
    )
    if vendor is None:
        raise HTTPException(status_code=404, detail="Vendor not found")
    return vendor


@router.get("", response_model=list[VendorResponse])
def list_vendors(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return (
        db.query(Vendor)
        .filter(Vendor.tenant_id == user.tenant_id)
        .order_by(desc(Vendor.risk_score), desc(Vendor.total_invoices))
        .all()
    )


@router.get("/{vendor_id}")
def get_vendor(
    vendor_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    vendor = _get_tenant_vendor(vendor_id, user, db)

    # Invoice history: documents whose extracted vendor_name matches
    from sqlalchemy import func

    doc_ids = [
        row[0]
        for row in db.query(ExtractedField.document_id)
        .join(Document, Document.id == ExtractedField.document_id)
        .filter(
            Document.tenant_id == user.tenant_id,
            ExtractedField.field_name == "vendor_name",
            func.lower(ExtractedField.normalised_value) == vendor.name.lower(),
        )
        .all()
    ]
    documents = (
        db.query(Document)
        .filter(Document.tenant_id == user.tenant_id, Document.id.in_(doc_ids))
        .order_by(desc(Document.created_at))
        .limit(50)
        .all()
        if doc_ids
        else []
    )
    return {
        "vendor": VendorResponse.model_validate(vendor),
        "invoices": [
            {
                "id": str(d.id),
                "original_filename": d.original_filename,
                "status": d.status,
                "risk_level": d.risk_level,
                "overall_risk_score": d.overall_risk_score,
                "created_at": d.created_at.isoformat() if d.created_at else None,
            }
            for d in documents
        ],
    }


@router.post("/{vendor_id}/whitelist", response_model=WhitelistToggleResponse)
def toggle_whitelist(
    vendor_id: uuid.UUID,
    request: Request,
    user: User = Depends(require_roles("owner", "operator")),
    db: Session = Depends(get_db),
):
    vendor = _get_tenant_vendor(vendor_id, user, db)
    vendor.is_whitelisted = not vendor.is_whitelisted
    db.commit()
    write_audit(
        db,
        tenant_id=user.tenant_id,
        user_id=user.id,
        event_type="vendor.whitelist_toggled",
        event_data={"vendor_id": str(vendor.id), "is_whitelisted": vendor.is_whitelisted},
        ip_address=request.client.host if request.client else None,
    )
    return WhitelistToggleResponse(id=vendor.id, is_whitelisted=vendor.is_whitelisted)


@router.put("/{vendor_id}", response_model=VendorResponse)
def update_vendor(
    vendor_id: uuid.UUID,
    payload: VendorUpdate,
    user: User = Depends(require_roles("owner", "operator")),
    db: Session = Depends(get_db),
):
    vendor = _get_tenant_vendor(vendor_id, user, db)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(vendor, field, value)
    db.commit()
    db.refresh(vendor)
    return vendor
