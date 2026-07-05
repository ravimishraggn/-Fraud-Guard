"""Analytics endpoints: KPI summary, trends, vendor risk, savings."""
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.models import Document, ExtractedField, FraudFlag, User, Vendor
from app.services.fraud_engine import rupees_to_paise

router = APIRouter(prefix="/api/v1/analytics", tags=["analytics"])


def _month_start() -> datetime:
    now = datetime.now(timezone.utc)
    return now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)


def _rejected_amount_paise(db: Session, tenant_id) -> int:
    """Sum of amounts on rejected documents = money saved."""
    rows = (
        db.query(ExtractedField.normalised_value)
        .join(Document, Document.id == ExtractedField.document_id)
        .filter(
            Document.tenant_id == tenant_id,
            Document.status == "REJECTED",
            ExtractedField.field_name == "amount_numeric",
        )
        .all()
    )
    total = 0
    for (value,) in rows:
        paise = rupees_to_paise(value)
        if paise:
            total += paise
    return total


@router.get("/summary")
def summary(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    tenant_id = user.tenant_id
    month_start = _month_start()

    docs_this_month = (
        db.query(func.count(Document.id))
        .filter(Document.tenant_id == tenant_id, Document.created_at >= month_start)
        .scalar()
        or 0
    )
    total_docs = (
        db.query(func.count(Document.id)).filter(Document.tenant_id == tenant_id).scalar() or 0
    )
    flags_raised = (
        db.query(func.count(FraudFlag.id))
        .join(Document, Document.id == FraudFlag.document_id)
        .filter(Document.tenant_id == tenant_id)
        .scalar()
        or 0
    )
    processed = (
        db.query(func.count(Document.id))
        .filter(
            Document.tenant_id == tenant_id,
            Document.status.in_(("APPROVED", "REJECTED", "REVIEW_REQUIRED")),
        )
        .scalar()
        or 0
    )
    auto_approved = (
        db.query(func.count(Document.id))
        .filter(
            Document.tenant_id == tenant_id,
            Document.status == "APPROVED",
            Document.review_note == "Auto-approved: risk score within clean threshold",
        )
        .scalar()
        or 0
    )
    pending_review = (
        db.query(func.count(Document.id))
        .filter(Document.tenant_id == tenant_id, Document.status == "REVIEW_REQUIRED")
        .scalar()
        or 0
    )

    return {
        "documents_this_month": docs_this_month,
        "documents_total": total_docs,
        "fraud_flags_raised": flags_raised,
        "money_saved_paise": _rejected_amount_paise(db, tenant_id),
        "automation_rate": round(auto_approved / processed * 100, 1) if processed else 0.0,
        "pending_review": pending_review,
    }


@router.get("/trends")
def trends(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Daily document volume for the last 30 days."""
    since = datetime.now(timezone.utc) - timedelta(days=30)
    rows = (
        db.query(func.date(Document.created_at), func.count(Document.id))
        .filter(Document.tenant_id == user.tenant_id, Document.created_at >= since)
        .group_by(func.date(Document.created_at))
        .order_by(func.date(Document.created_at))
        .all()
    )
    by_date = {str(d): c for d, c in rows}
    series = []
    for i in range(30, -1, -1):
        day = (datetime.now(timezone.utc) - timedelta(days=i)).date()
        series.append({"date": day.isoformat(), "count": by_date.get(day.isoformat(), 0)})
    return {"series": series}


@router.get("/vendors")
def vendor_risk(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    vendors = (
        db.query(Vendor)
        .filter(Vendor.tenant_id == user.tenant_id)
        .order_by(Vendor.risk_score.desc())
        .limit(20)
        .all()
    )
    return {
        "vendors": [
            {
                "id": str(v.id),
                "name": v.name,
                "risk_score": v.risk_score,
                "total_invoices": v.total_invoices,
                "flagged_count": v.flagged_count,
                "total_amount_paise": v.total_amount_paise,
                "is_whitelisted": v.is_whitelisted,
            }
            for v in vendors
        ]
    }


@router.get("/savings")
def savings(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Money saved breakdown by flag type on rejected documents."""
    tenant_id = user.tenant_id
    rejected_docs = (
        db.query(Document.id)
        .filter(Document.tenant_id == tenant_id, Document.status == "REJECTED")
        .subquery()
    )
    flag_rows = (
        db.query(FraudFlag.flag_type, func.count(FraudFlag.id))
        .filter(FraudFlag.document_id.in_(rejected_docs))
        .group_by(FraudFlag.flag_type)
        .all()
    )
    return {
        "total_saved_paise": _rejected_amount_paise(db, tenant_id),
        "by_flag_type": [{"flag_type": t, "count": c} for t, c in flag_rows],
    }
