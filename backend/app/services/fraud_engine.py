"""Fraud detection engine — the core of FraudGuard.

All checks operate on a plain dict of extracted field values so they can be
run from the Celery pipeline, the seeder, and tests identically.

Amounts are handled in paise (integer) throughout.
"""
import logging
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from rapidfuzz import fuzz
from sqlalchemy import and_, func
from sqlalchemy.orm import Session

from app.models import Document, ExtractedField, FraudRule, Vendor
from app.services.gstin import gstin_service
from app.utils.validators import is_valid_gstin_format, words_to_number

logger = logging.getLogger(__name__)

# Risk scoring weights: (points, max flags counted)
SEVERITY_POINTS = {
    "critical": (40, 2),
    "high": (25, 3),
    "medium": (15, 3),
    "low": (5, None),
}


def _flag(
    flag_type: str,
    severity: str,
    title: str,
    description: str,
    evidence: Optional[dict] = None,
    confidence: float = 0.9,
) -> dict[str, Any]:
    return {
        "flag_type": flag_type,
        "severity": severity,
        "title": title,
        "description": description,
        "evidence": evidence or {},
        "confidence": confidence,
    }


def rupees_to_paise(value: Any) -> Optional[int]:
    """Convert a rupee amount (str/float/int) to integer paise."""
    if value is None:
        return None
    try:
        return int(round(float(str(value).replace(",", "").replace("₹", "").strip()) * 100))
    except (ValueError, TypeError):
        return None


class FraudEngine:
    def __init__(self) -> None:
        self.gstin_service = gstin_service

    def run_all_checks(
        self,
        document: Document,
        fields: dict[str, Optional[str]],
        tenant_id: uuid.UUID,
        db: Session,
    ) -> list[dict]:
        """Run all fraud checks. Never raises — always returns a list."""
        flags: list[dict] = []
        checks = (
            self.check_duplicate_invoice,
            self.check_gstin_validity,
            self.check_amount_words_mismatch,
            self.check_future_date,
            self.check_shared_bank_account,
            self.check_vendor_whitelist,
            self.check_custom_rules,
        )
        for check in checks:
            try:
                flags.extend(check(document, fields, tenant_id, db))
            except Exception:
                logger.exception("Fraud check %s failed", check.__name__)
        return flags

    # ------------------------------------------------------------------
    # Check 1 — Duplicate invoice
    # ------------------------------------------------------------------
    def check_duplicate_invoice(self, document, fields, tenant_id, db) -> list[dict]:
        flags = []
        invoice_number = (fields.get("invoice_number") or "").strip()
        vendor_name = (fields.get("vendor_name") or "").strip()
        amount_paise = rupees_to_paise(fields.get("amount_numeric"))
        invoice_date = _parse_date(fields.get("invoice_date"))
        if not vendor_name:
            return flags

        one_year_ago = datetime.now(timezone.utc) - timedelta(days=365)
        candidates = (
            db.query(Document, ExtractedField)
            .join(ExtractedField, ExtractedField.document_id == Document.id)
            .filter(
                Document.tenant_id == tenant_id,
                Document.id != document.id,
                Document.created_at >= one_year_ago,
                Document.status.notin_(("FAILED",)),
                ExtractedField.field_name == "vendor_name",
            )
            .all()
        )
        # Filter to same-vendor documents (fuzzy, OCR tolerant)
        same_vendor_doc_ids = [
            doc.id
            for doc, field in candidates
            if field.normalised_value
            and fuzz.token_sort_ratio(field.normalised_value.lower(), vendor_name.lower()) > 85
        ]
        if not same_vendor_doc_ids:
            return flags

        other_fields = (
            db.query(ExtractedField)
            .filter(
                ExtractedField.document_id.in_(same_vendor_doc_ids),
                ExtractedField.field_name.in_(
                    ("invoice_number", "amount_numeric", "invoice_date")
                ),
            )
            .all()
        )
        by_doc: dict[uuid.UUID, dict[str, str]] = {}
        for f in other_fields:
            by_doc.setdefault(f.document_id, {})[f.field_name] = f.normalised_value or ""

        for doc_id, doc_fields in by_doc.items():
            other_inv = doc_fields.get("invoice_number", "").strip()
            other_amount = rupees_to_paise(doc_fields.get("amount_numeric"))
            other_date = _parse_date(doc_fields.get("invoice_date"))

            # DEFINITE duplicate: same invoice number + same vendor
            if invoice_number and other_inv and invoice_number.lower() == other_inv.lower():
                flags.append(
                    _flag(
                        "DUPLICATE_INVOICE",
                        "critical",
                        "Duplicate invoice number",
                        f"Invoice {invoice_number} from {vendor_name} was already "
                        "submitted within the last 365 days.",
                        {
                            "matched_document_id": str(doc_id),
                            "matched_invoice_number": other_inv,
                            "matched_date": doc_fields.get("invoice_date"),
                            "matched_amount_paise": other_amount,
                        },
                        confidence=0.98,
                    )
                )
                continue

            # POSSIBLE duplicate: same amount + same vendor, dates within 30 days
            if (
                amount_paise
                and other_amount
                and amount_paise == other_amount
                and invoice_date
                and other_date
                and abs((invoice_date - other_date).days) <= 30
            ):
                flags.append(
                    _flag(
                        "DUPLICATE_INVOICE",
                        "high",
                        "Possible duplicate invoice (same amount)",
                        f"Another invoice from {vendor_name} for the identical amount "
                        "was submitted within 30 days under a different invoice number. "
                        "This may be a resubmission.",
                        {
                            "matched_document_id": str(doc_id),
                            "matched_invoice_number": other_inv,
                            "matched_date": doc_fields.get("invoice_date"),
                            "matched_amount_paise": other_amount,
                        },
                        confidence=0.8,
                    )
                )
        return flags

    # ------------------------------------------------------------------
    # Check 2 — GSTIN validity
    # ------------------------------------------------------------------
    def check_gstin_validity(self, document, fields, tenant_id, db) -> list[dict]:
        flags = []
        gstin = (fields.get("vendor_gstin") or "").strip().upper()
        vendor_name = (fields.get("vendor_name") or "").strip()
        if not gstin:
            return flags

        if not is_valid_gstin_format(gstin):
            flags.append(
                _flag(
                    "INVALID_GSTIN",
                    "high",
                    "GSTIN format is invalid",
                    f"The GSTIN '{gstin}' does not match the official 15-character "
                    "GSTIN format. This vendor may not be GST-registered.",
                    {"gstin": gstin, "check_level": "format"},
                    confidence=0.99,
                )
            )
            return flags

        result = self.gstin_service.verify(gstin)
        if result["status"] == "invalid":
            flags.append(
                _flag(
                    "INVALID_GSTIN",
                    "high",
                    "GSTIN not found in GST registry",
                    f"The GSTIN '{gstin}' passed format checks but the GST registry "
                    "reports it as not found.",
                    {"gstin": gstin, "check_level": "api", "reason": result["reason"]},
                    confidence=0.9,
                )
            )
        elif result["status"] == "valid" and result.get("registered_name") and vendor_name:
            similarity = fuzz.token_sort_ratio(
                result["registered_name"].lower(), vendor_name.lower()
            )
            if similarity < 80:
                flags.append(
                    _flag(
                        "INVALID_GSTIN",
                        "medium",
                        "GSTIN registered to a different name",
                        f"GSTIN '{gstin}' is registered to "
                        f"'{result['registered_name']}' but the invoice names "
                        f"'{vendor_name}' ({similarity:.0f}% match).",
                        {
                            "gstin": gstin,
                            "gstin_name": result["registered_name"],
                            "invoice_vendor": vendor_name,
                            "similarity": similarity,
                        },
                        confidence=0.85,
                    )
                )
        elif result["status"] == "unverified" and result.get("reason") == "api_unavailable":
            flags.append(
                _flag(
                    "INVALID_GSTIN",
                    "low",
                    "GSTIN could not be verified online",
                    f"GSTIN '{gstin}' has a valid format, but online verification "
                    "was unavailable. Format checks passed.",
                    {"gstin": gstin, "reason": result["reason"]},
                    confidence=0.5,
                )
            )
        return flags

    # ------------------------------------------------------------------
    # Check 3 — Amount in words vs figures
    # ------------------------------------------------------------------
    def check_amount_words_mismatch(self, document, fields, tenant_id, db) -> list[dict]:
        flags = []
        amount_paise = rupees_to_paise(fields.get("amount_numeric"))
        words_text = fields.get("amount_in_words")
        if not amount_paise or not words_text:
            return flags
        words_rupees = words_to_number(words_text)
        if words_rupees is None:
            return flags
        words_paise = words_rupees * 100
        if words_paise == 0:
            return flags
        deviation = abs(amount_paise - words_paise) / max(amount_paise, words_paise)
        if deviation > 0.01:  # 1% rounding tolerance
            flags.append(
                _flag(
                    "AMOUNT_WORDS_MISMATCH",
                    "critical",
                    "Amount in words does not match figures",
                    f"The invoice shows ₹{amount_paise / 100:,.2f} in figures but "
                    f"'{words_text.strip()}' (₹{words_rupees:,.0f}) in words. "
                    "This is the most common sign of a manually altered invoice.",
                    {
                        "numeric_paise": amount_paise,
                        "words_value_paise": words_paise,
                        "words_text": words_text.strip(),
                    },
                    confidence=0.95,
                )
            )
        return flags

    # ------------------------------------------------------------------
    # Check 4 — Future / stale invoice date
    # ------------------------------------------------------------------
    def check_future_date(self, document, fields, tenant_id, db) -> list[dict]:
        flags = []
        invoice_date = _parse_date(fields.get("invoice_date"))
        if not invoice_date:
            return flags
        today = datetime.now(timezone.utc).date()
        delta_days = (invoice_date - today).days

        if delta_days > 30:
            flags.append(
                _flag(
                    "FUTURE_DATE",
                    "critical",
                    "Invoice dated far in the future",
                    f"The invoice is dated {invoice_date.isoformat()} — "
                    f"{delta_days} days in the future.",
                    {"invoice_date": invoice_date.isoformat(), "days_in_future": delta_days},
                    confidence=0.95,
                )
            )
        elif delta_days > 1:  # 1-day grace for timezones
            flags.append(
                _flag(
                    "FUTURE_DATE",
                    "high",
                    "Invoice date is in the future",
                    f"The invoice is dated {invoice_date.isoformat()} — "
                    f"{delta_days} days ahead of today.",
                    {"invoice_date": invoice_date.isoformat(), "days_in_future": delta_days},
                    confidence=0.9,
                )
            )
        elif delta_days < -730:
            flags.append(
                _flag(
                    "STALE_DATE",
                    "medium",
                    "Invoice date is unusually old",
                    f"The invoice is dated {invoice_date.isoformat()}, more than two "
                    "years ago. Old invoice numbers are sometimes reused for fraud.",
                    {"invoice_date": invoice_date.isoformat(), "days_old": -delta_days},
                    confidence=0.7,
                )
            )
        return flags

    # ------------------------------------------------------------------
    # Check 5 — Shared bank account across different vendors
    # ------------------------------------------------------------------
    def check_shared_bank_account(self, document, fields, tenant_id, db) -> list[dict]:
        flags = []
        bank_account = (fields.get("vendor_bank_account") or "").strip()
        vendor_name = (fields.get("vendor_name") or "").strip()
        if not bank_account or not vendor_name:
            return flags

        matches = (
            db.query(Vendor)
            .filter(
                Vendor.tenant_id == tenant_id,
                Vendor.bank_account == bank_account,
                func.lower(Vendor.name) != vendor_name.lower(),
            )
            .all()
        )
        for match in matches:
            flags.append(
                _flag(
                    "SHARED_BANK_ACCOUNT",
                    "critical",
                    "Bank account shared with another vendor",
                    f"'{vendor_name}' uses the same bank account "
                    f"({_mask_account(bank_account)}) as existing vendor "
                    f"'{match.name}'. This is a strong shell-company indicator.",
                    {
                        "current_vendor": vendor_name,
                        "matched_vendor": match.name,
                        "bank_account": bank_account,
                        "matched_vendor_id": str(match.id),
                    },
                    confidence=0.97,
                )
            )
        return flags

    # ------------------------------------------------------------------
    # Whitelist + custom tenant rules
    # ------------------------------------------------------------------
    def check_vendor_whitelist(self, document, fields, tenant_id, db) -> list[dict]:
        flags = []
        vendor_name = (fields.get("vendor_name") or "").strip()
        if not vendor_name:
            return flags
        rule = (
            db.query(FraudRule)
            .filter(
                FraudRule.tenant_id == tenant_id,
                FraudRule.rule_type == "vendor_whitelist_only",
                FraudRule.is_active.is_(True),
            )
            .first()
        )
        if not rule:
            return flags
        vendor = (
            db.query(Vendor)
            .filter(
                Vendor.tenant_id == tenant_id,
                func.lower(Vendor.name) == vendor_name.lower(),
            )
            .first()
        )
        if vendor is None or not vendor.is_whitelisted:
            flags.append(
                _flag(
                    "VENDOR_NOT_WHITELISTED",
                    "high",
                    "Vendor is not on the approved list",
                    f"'{vendor_name}' is not on your approved vendor whitelist, and "
                    "your rules require all invoices to come from whitelisted vendors.",
                    {"vendor_name": vendor_name, "rule_id": str(rule.id)},
                    confidence=0.9,
                )
            )
        return flags

    def check_custom_rules(self, document, fields, tenant_id, db) -> list[dict]:
        flags = []
        rules = (
            db.query(FraudRule)
            .filter(
                FraudRule.tenant_id == tenant_id,
                FraudRule.is_active.is_(True),
                FraudRule.rule_type.in_(("amount_limit", "frequency_limit", "require_po")),
            )
            .all()
        )
        amount_paise = rupees_to_paise(fields.get("amount_numeric"))
        vendor_name = (fields.get("vendor_name") or "").strip()

        for rule in rules:
            config = rule.config or {}
            if rule.rule_type == "amount_limit" and amount_paise:
                max_rupees = config.get("max_amount")
                if max_rupees and amount_paise > int(max_rupees) * 100:
                    flags.append(
                        _flag(
                            "AMOUNT_EXCEEDS_LIMIT",
                            "high",
                            f"Amount exceeds limit set by rule '{rule.rule_name}'",
                            f"Invoice amount ₹{amount_paise / 100:,.2f} exceeds your "
                            f"configured limit of ₹{float(max_rupees):,.2f}.",
                            {
                                "amount_paise": amount_paise,
                                "limit_paise": int(max_rupees) * 100,
                                "rule_id": str(rule.id),
                            },
                        )
                    )
            elif rule.rule_type == "frequency_limit" and vendor_name:
                max_per_month = int(config.get("max_invoices_per_month", 0))
                if max_per_month:
                    month_ago = datetime.now(timezone.utc) - timedelta(days=30)
                    count = (
                        db.query(func.count(ExtractedField.id))
                        .join(Document, Document.id == ExtractedField.document_id)
                        .filter(
                            Document.tenant_id == tenant_id,
                            Document.created_at >= month_ago,
                            ExtractedField.field_name == "vendor_name",
                            func.lower(ExtractedField.normalised_value) == vendor_name.lower(),
                        )
                        .scalar()
                    )
                    if count and count > max_per_month:
                        flags.append(
                            _flag(
                                "FREQUENCY_ANOMALY",
                                "medium",
                                "Unusually many invoices from this vendor",
                                f"'{vendor_name}' has submitted {count} invoices in the "
                                f"last 30 days (limit: {max_per_month}).",
                                {
                                    "count": count,
                                    "limit": max_per_month,
                                    "rule_id": str(rule.id),
                                },
                            )
                        )
            elif rule.rule_type == "require_po":
                if not (fields.get("po_reference") or "").strip():
                    flags.append(
                        _flag(
                            "MISSING_PO",
                            "medium",
                            "No purchase order reference",
                            "Your rules require a PO reference on every invoice, "
                            "but none was found on this document.",
                            {"rule_id": str(rule.id)},
                        )
                    )
        return flags

    # ------------------------------------------------------------------
    # Risk scoring
    # ------------------------------------------------------------------
    @staticmethod
    def calculate_risk_score(flags: list[dict]) -> tuple[int, str]:
        """Return (score 0-100, level clean|low|medium|high)."""
        score = 0
        counts: dict[str, int] = {}
        for flag in flags:
            sev = flag.get("severity", "low")
            points, cap = SEVERITY_POINTS.get(sev, (5, None))
            counts[sev] = counts.get(sev, 0) + 1
            if cap is None or counts[sev] <= cap:
                score += points
        score = min(score, 100)
        if score <= 20:
            level = "clean"
        elif score <= 50:
            level = "low"
        elif score <= 75:
            level = "medium"
        else:
            level = "high"
        return score, level


def _parse_date(value: Optional[str]):
    if not value:
        return None
    for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y", "%Y/%m/%d"):
        try:
            return datetime.strptime(str(value).strip(), fmt).date()
        except ValueError:
            continue
    return None


def _mask_account(account: str) -> str:
    if len(account) <= 4:
        return account
    return "•" * (len(account) - 4) + account[-4:]


fraud_engine = FraudEngine()
