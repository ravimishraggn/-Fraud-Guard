"""Document processing pipeline — upload → OCR → extraction → fraud checks."""
import logging
import uuid
from datetime import datetime, timezone

from app.database import SessionLocal
from app.models import Document, ExtractedField, Tenant, User, Vendor
from app.models.document import (
    STATUS_APPROVED,
    STATUS_FAILED,
    STATUS_PROCESSING,
    STATUS_REVIEW_REQUIRED,
)
from app.models.fraud_flag import FraudFlag
from app.services.audit import write_audit
from app.services.extraction import extract_fields
from app.services.fraud_engine import fraud_engine, rupees_to_paise
from app.services.ocr import run_ocr
from app.services.storage import storage_service
from app.tasks.celery_app import celery_app
from app.tasks.notifications import send_review_notification
from app.utils.confidence import clamp_confidence

logger = logging.getLogger(__name__)

FIELDS_TO_STORE = (
    "vendor_name", "vendor_gstin", "vendor_pan", "vendor_bank_account",
    "vendor_bank_ifsc", "invoice_number", "invoice_date", "due_date",
    "amount_numeric", "amount_in_words", "tax_amount", "tax_rate",
    "po_reference", "payment_terms",
)


@celery_app.task(bind=True, max_retries=3)
def process_document(self, document_id: str):
    db = SessionLocal()
    try:
        doc = db.query(Document).filter(Document.id == uuid.UUID(document_id)).first()
        if doc is None:
            logger.error("Document %s not found", document_id)
            return

        started = datetime.now(timezone.utc)
        doc.status = STATUS_PROCESSING
        doc.processing_started_at = started
        db.commit()

        # 1. Download from storage
        data = storage_service.download(doc.storage_path)

        # 2-4. Quality check + preprocessing + OCR
        ocr_result = run_ocr(data, doc.mime_type or "application/pdf")
        if ocr_result.get("error"):
            _mark_failed(db, doc, ocr_result.get("message", "OCR failed"))
            return

        # 5. Persist raw OCR summary in metadata
        doc.doc_metadata = {
            **(doc.doc_metadata or {}),
            "ocr": {
                "overall_confidence": ocr_result.get("overall_confidence", 0.0),
                "engine_used": ocr_result.get("engine_used"),
                "pages": ocr_result.get("pages", 1),
                "char_count": len(ocr_result.get("text", "")),
            },
        }
        db.commit()

        # 6. AI extraction
        extracted = extract_fields(ocr_result.get("text", ""))
        confidence_scores = extracted.get("confidence_scores") or {}
        doc.doc_type = extracted.get("document_type") or "unknown"
        doc.doc_type_confidence = clamp_confidence(confidence_scores.get("vendor_name", 0.5))

        fields_dict: dict[str, str | None] = {}
        for name in FIELDS_TO_STORE:
            value = extracted.get(name)
            str_value = str(value) if value is not None else None
            fields_dict[name] = str_value
            db.add(
                ExtractedField(
                    document_id=doc.id,
                    field_name=name,
                    raw_value=str_value,
                    normalised_value=str_value,
                    confidence=clamp_confidence(confidence_scores.get(name, 0.75)),
                    source="llm",
                )
            )
        db.commit()

        # 7. Fraud checks
        flag_dicts = fraud_engine.run_all_checks(doc, fields_dict, doc.tenant_id, db)
        for f in flag_dicts:
            db.add(FraudFlag(document_id=doc.id, **f))

        # 8. Risk score
        score, level = fraud_engine.calculate_risk_score(flag_dicts)
        doc.overall_risk_score = score
        doc.risk_level = level

        # 9. Status transition
        doc.status = STATUS_APPROVED if score <= 20 else STATUS_REVIEW_REQUIRED
        if doc.status == STATUS_APPROVED:
            doc.review_decision = "approved"
            doc.reviewed_at = datetime.now(timezone.utc)
            doc.review_note = "Auto-approved: risk score within clean threshold"

        completed = datetime.now(timezone.utc)
        doc.processing_completed_at = completed
        doc.processing_ms = int((completed - started).total_seconds() * 1000)
        db.commit()

        # 10. Upsert vendor record
        _update_vendor(db, doc, fields_dict, bool(flag_dicts))

        # 11. Notify if review required
        if doc.status == STATUS_REVIEW_REQUIRED:
            owner = (
                db.query(User)
                .filter(User.tenant_id == doc.tenant_id, User.role == "owner")
                .first()
            )
            if owner:
                send_review_notification.delay(
                    owner.email, doc.original_filename or "invoice", level, len(flag_dicts)
                )

        # 12. Usage counter
        tenant = db.query(Tenant).filter(Tenant.id == doc.tenant_id).first()
        if tenant:
            tenant.docs_used_this_month = (tenant.docs_used_this_month or 0) + 1
            db.commit()

        # 13. Audit trail
        write_audit(
            db,
            tenant_id=doc.tenant_id,
            event_type="document.processed",
            document_id=doc.id,
            event_data={
                "risk_score": score,
                "risk_level": level,
                "flags": len(flag_dicts),
                "status": doc.status,
            },
        )
        logger.info("Processed %s → %s (score %s)", document_id, doc.status, score)

    except Exception as exc:
        from celery.exceptions import Retry

        db.rollback()
        if isinstance(exc, Retry):
            raise
        logger.exception("Processing failed for %s", document_id)
        if self.request.retries < self.max_retries:
            # Exponential backoff: 10s, 20s, 40s
            raise self.retry(exc=exc, countdown=2 ** self.request.retries * 10)
        doc = db.query(Document).filter(Document.id == uuid.UUID(document_id)).first()
        if doc:
            _mark_failed(db, doc, f"Processing failed after retries: {exc}")
    finally:
        db.close()


def _mark_failed(db, doc: Document, reason: str) -> None:
    doc.status = STATUS_FAILED
    doc.doc_metadata = {**(doc.doc_metadata or {}), "failure_reason": reason}
    doc.processing_completed_at = datetime.now(timezone.utc)
    db.commit()
    write_audit(
        db,
        tenant_id=doc.tenant_id,
        event_type="document.failed",
        document_id=doc.id,
        event_data={"reason": reason},
    )


def _update_vendor(db, doc: Document, fields: dict, was_flagged: bool) -> None:
    """Create or update the vendor record from extracted invoice data."""
    from sqlalchemy import func as sa_func

    vendor_name = (fields.get("vendor_name") or "").strip()
    if not vendor_name:
        return
    vendor = (
        db.query(Vendor)
        .filter(
            Vendor.tenant_id == doc.tenant_id,
            sa_func.lower(Vendor.name) == vendor_name.lower(),
        )
        .first()
    )
    amount_paise = rupees_to_paise(fields.get("amount_numeric")) or 0
    if vendor is None:
        vendor = Vendor(
            tenant_id=doc.tenant_id,
            name=vendor_name,
            gstin=fields.get("vendor_gstin"),
            pan=fields.get("vendor_pan"),
            bank_account=fields.get("vendor_bank_account"),
            bank_ifsc=fields.get("vendor_bank_ifsc"),
        )
        db.add(vendor)
    vendor.total_invoices = (vendor.total_invoices or 0) + 1
    vendor.total_amount_paise = (vendor.total_amount_paise or 0) + amount_paise
    if was_flagged:
        vendor.flagged_count = (vendor.flagged_count or 0) + 1
    vendor.risk_score = min(
        100, int(100 * (vendor.flagged_count or 0) / max(vendor.total_invoices, 1))
    )
    vendor.last_seen = datetime.now(timezone.utc)
    if fields.get("vendor_bank_account") and not vendor.bank_account:
        vendor.bank_account = fields.get("vendor_bank_account")
    if fields.get("vendor_gstin") and not vendor.gstin:
        vendor.gstin = fields.get("vendor_gstin")
    db.commit()
