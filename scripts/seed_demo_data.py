"""Seed demo data for FraudGuard.

Creates the "Sharma Construction Pvt Ltd" tenant with 50 invoices,
including planted fraud cases that light up every fraud check:
  - 3 exact duplicate invoices
  - 2 invoices with invalid GSTIN
  - 1 amount-in-words mismatch (₹47,500 vs "Forty One Thousand Five Hundred")
  - 1 invoice dated ~35 days in the future
  - 2 vendors sharing one bank account (shell company pattern)
  - 1 invoice from a non-whitelisted vendor (whitelist-only rule enabled)

Run inside the backend container:
    docker compose exec backend python scripts/seed_demo_data.py
"""
import random
import sys
from datetime import datetime, timedelta, timezone

sys.path.insert(0, "/app")
sys.path.insert(0, ".")

from app.database import SessionLocal  # noqa: E402
from app.models import (  # noqa: E402
    Document,
    ExtractedField,
    FraudFlag,
    FraudRule,
    Tenant,
    User,
    Vendor,
)
from app.services.fraud_engine import fraud_engine, rupees_to_paise  # noqa: E402
from app.utils.security import hash_password  # noqa: E402

DEMO_EMAIL = "demo@fraudguard.in"
DEMO_PASSWORD = "Demo@1234"

random.seed(42)

# name, gstin (valid format), bank_account, ifsc
LEGIT_VENDORS = [
    ("UltraTech Cement Dealers", "27AAPFU0939F1ZV", "50100234567891", "HDFC0001234"),
    ("Jindal Steel Traders", "07AABCJ4567K1Z8", "60200345678912", "ICIC0004567"),
    ("Asian Paints Distributor", "24AACCA8907B1Z4", "30300456789123", "SBIN0007890"),
    ("Maruti Hardware Stores", "09AADCM2345L1Z6", "40400567891234", "PUNB0012345"),
    ("Om Sai Electricals", "27AAEFO6789M1Z1", "50500678912345", "AXIS0045678"),
    ("Ganesh Timber Mart", "33AAFCG3456N1Z5", "60600789123456", "KKBK0078912"),
    ("Balaji Sand Suppliers", "36AAGCB7891P1Z9", "70700891234567", "YESB0023456"),
    ("Shree Cement Agency", "08AAHCS2345Q1Z2", "80800912345678", "IDIB0056789"),
    ("National Plumbing Co", "29AAJCN6789R1Z7", "90901123456789", "CNRB0089123"),
    ("Prakash Tiles House", "27AAKCP3456S1Z3", "11012234567891", "UBIN0034567"),
    ("Krishna Traders", "27AALCK7891T1ZX", "12345678901234", "HDFC0009876"),
    ("Verma Machinery Rentals", "06AAMCV2345U1Z0", "13123345678912", "ICIC0008765"),
]

# Fraud actors
SHELL_VENDOR = ("Raj Enterprises", "27AANCR6789V1Z5", "12345678901234", "HDFC0009876")  # same account as Krishna Traders
NON_WHITELISTED_VENDOR = ("Speedy Logistics", "27AAPCS3456W1Z8", "14134456789123", "AXIS0011223")
BAD_GSTIN_VENDORS = [
    ("Sunrise Suppliers", "INVALID123GST99", "15145567891234", "SBIN0033445"),
    ("Deepak Trading Co", "99ZZZZZ0000A0A0", "16156678912345", "PUNB0055667"),
]

RUPEES_TO_WORDS_UNITS = {
    0: "Zero", 1: "One", 2: "Two", 3: "Three", 4: "Four", 5: "Five", 6: "Six",
    7: "Seven", 8: "Eight", 9: "Nine", 10: "Ten", 11: "Eleven", 12: "Twelve",
    13: "Thirteen", 14: "Fourteen", 15: "Fifteen", 16: "Sixteen",
    17: "Seventeen", 18: "Eighteen", 19: "Nineteen",
}
RUPEES_TO_WORDS_TENS = {
    2: "Twenty", 3: "Thirty", 4: "Forty", 5: "Fifty",
    6: "Sixty", 7: "Seventy", 8: "Eighty", 9: "Ninety",
}


def rupees_in_words(amount: int) -> str:
    """Simple Indian-style amount to words (integer rupees, up to crores)."""

    def two_digits(n: int) -> str:
        if n < 20:
            return RUPEES_TO_WORDS_UNITS[n]
        tens, units = divmod(n, 10)
        word = RUPEES_TO_WORDS_TENS[tens]
        return f"{word} {RUPEES_TO_WORDS_UNITS[units]}" if units else word

    def three_digits(n: int) -> str:
        hundreds, rest = divmod(n, 100)
        parts = []
        if hundreds:
            parts.append(f"{RUPEES_TO_WORDS_UNITS[hundreds]} Hundred")
        if rest:
            parts.append(two_digits(rest))
        return " ".join(parts) or "Zero"

    if amount == 0:
        return "Zero Rupees Only"
    crore, rest = divmod(amount, 10_000_000)
    lakh, rest = divmod(rest, 100_000)
    thousand, rest = divmod(rest, 1_000)
    parts = []
    if crore:
        parts.append(f"{two_digits(crore)} Crore")
    if lakh:
        parts.append(f"{two_digits(lakh)} Lakh")
    if thousand:
        parts.append(f"{two_digits(thousand)} Thousand")
    if rest:
        parts.append(three_digits(rest))
    return " ".join(parts) + " Rupees Only"


def make_fields(vendor, invoice_number, invoice_date, amount_rupees, words=None, po=None):
    return {
        "vendor_name": vendor[0],
        "vendor_gstin": vendor[1],
        "vendor_pan": None,
        "vendor_bank_account": vendor[2],
        "vendor_bank_ifsc": vendor[3],
        "invoice_number": invoice_number,
        "invoice_date": invoice_date.strftime("%Y-%m-%d"),
        "due_date": (invoice_date + timedelta(days=30)).strftime("%Y-%m-%d"),
        "amount_numeric": str(amount_rupees),
        "amount_in_words": words if words is not None else rupees_in_words(amount_rupees),
        "tax_amount": str(round(amount_rupees * 0.18 / 1.18, 2)),
        "tax_rate": "18",
        "po_reference": po,
        "payment_terms": "Net 30",
    }


def insert_invoice(db, tenant, owner, fields, created_at, filename):
    doc = Document(
        tenant_id=tenant.id,
        uploaded_by=owner.id,
        original_filename=filename,
        mime_type="application/pdf",
        file_size_bytes=random.randint(80_000, 900_000),
        storage_path=None,
        status="PROCESSING",
        doc_type="invoice",
        doc_type_confidence=0.95,
        created_at=created_at,
        processing_started_at=created_at,
        doc_metadata={"seeded": True},
    )
    db.add(doc)
    db.flush()

    for name, value in fields.items():
        db.add(
            ExtractedField(
                document_id=doc.id,
                field_name=name,
                raw_value=value,
                normalised_value=value,
                confidence=round(random.uniform(0.82, 0.99), 2),
                source="llm",
            )
        )
    db.commit()

    flags = fraud_engine.run_all_checks(doc, fields, tenant.id, db)
    for f in flags:
        db.add(FraudFlag(document_id=doc.id, **f))
    score, level = fraud_engine.calculate_risk_score(flags)
    doc.overall_risk_score = score
    doc.risk_level = level
    doc.status = "APPROVED" if score <= 20 else "REVIEW_REQUIRED"
    if doc.status == "APPROVED":
        doc.review_decision = "approved"
        doc.reviewed_at = created_at + timedelta(minutes=1)
        doc.review_note = "Auto-approved: risk score within clean threshold"
    doc.processing_completed_at = created_at + timedelta(seconds=random.randint(8, 40))
    doc.processing_ms = random.randint(8_000, 40_000)
    db.commit()

    # Maintain vendor stats
    vendor_name = fields["vendor_name"]
    vendor = db.query(Vendor).filter(Vendor.tenant_id == tenant.id, Vendor.name == vendor_name).first()
    if vendor is None:
        vendor = Vendor(
            tenant_id=tenant.id,
            name=vendor_name,
            gstin=fields.get("vendor_gstin"),
            bank_account=fields.get("vendor_bank_account"),
            bank_ifsc=fields.get("vendor_bank_ifsc"),
        )
        db.add(vendor)
        db.flush()
    vendor.total_invoices = (vendor.total_invoices or 0) + 1
    vendor.total_amount_paise = (vendor.total_amount_paise or 0) + (rupees_to_paise(fields["amount_numeric"]) or 0)
    if flags:
        vendor.flagged_count = (vendor.flagged_count or 0) + 1
    vendor.risk_score = min(100, int(100 * (vendor.flagged_count or 0) / max(vendor.total_invoices, 1)))
    vendor.last_seen = created_at
    db.commit()
    return doc, flags


def reject(db, doc, owner, note):
    doc.status = "REJECTED"
    doc.review_decision = "rejected"
    doc.review_note = note
    doc.reviewed_by = owner.id
    doc.reviewed_at = datetime.now(timezone.utc)
    db.commit()


def main():
    db = SessionLocal()
    try:
        if db.query(User).filter(User.email == DEMO_EMAIL).first():
            print(f"Demo user {DEMO_EMAIL} already exists — skipping seed.")
            return

        now = datetime.now(timezone.utc)
        print("Creating tenant and owner…")
        tenant = Tenant(name="Sharma Construction Pvt Ltd", slug="sharma-construction", plan="growth", doc_limit_monthly=500)
        db.add(tenant)
        db.flush()
        owner = User(
            tenant_id=tenant.id,
            email=DEMO_EMAIL,
            full_name="Rakesh Sharma",
            hashed_password=hash_password(DEMO_PASSWORD),
            role="owner",
        )
        db.add(owner)
        db.flush()

        print("Creating fraud rules…")
        builtin_rules = [
            ("Duplicate invoice detection", "builtin_duplicate"),
            ("GSTIN format validation", "builtin_gstin"),
            ("Amount vs words mismatch", "builtin_amount_words"),
            ("Future invoice date", "builtin_future_date"),
            ("Shared bank account detection", "builtin_shared_bank"),
        ]
        for rule_name, rule_type in builtin_rules:
            db.add(FraudRule(tenant_id=tenant.id, rule_name=rule_name, rule_type=rule_type,
                             is_active=True, config={"builtin": True}, created_by=owner.id))
        db.add(FraudRule(tenant_id=tenant.id, rule_name="Approved vendors only",
                         rule_type="vendor_whitelist_only", is_active=True, config={}, created_by=owner.id))
        db.add(FraudRule(tenant_id=tenant.id, rule_name="Flag invoices above ₹5,00,000",
                         rule_type="amount_limit", is_active=True, config={"max_amount": 500000}, created_by=owner.id))
        db.commit()

        print("Pre-creating whitelisted vendors…")
        for name, gstin, account, ifsc in LEGIT_VENDORS:
            db.add(Vendor(tenant_id=tenant.id, name=name, gstin=gstin,
                          bank_account=account, bank_ifsc=ifsc, is_whitelisted=True))
        # Fraud-case vendors are whitelisted too (except Speedy Logistics),
        # so their specific fraud signals stand out cleanly.
        for vendor in (SHELL_VENDOR, *BAD_GSTIN_VENDORS):
            db.add(Vendor(tenant_id=tenant.id, name=vendor[0], gstin=None,
                          bank_account=None, bank_ifsc=None, is_whitelisted=True))
        db.commit()
        # NB: Krishna Traders (in LEGIT_VENDORS) holds account 12345678901234.
        # Raj Enterprises (SHELL_VENDOR) invoices against the same account.

        print("Inserting 40 clean invoices…")
        originals = {}  # for duplicates later
        for i in range(40):
            vendor = LEGIT_VENDORS[i % len(LEGIT_VENDORS)]
            invoice_date = (now - timedelta(days=random.randint(2, 28))).date()
            created_at = now - timedelta(days=random.randint(1, 27), hours=random.randint(0, 12))
            amount = random.choice([18500, 24750, 32000, 47500, 56800, 78200, 94500, 125000, 156000, 210000])
            inv_no = f"INV-{2026}0{random.randint(100, 999)}-{i:03d}"
            fields = make_fields(vendor, inv_no, invoice_date, amount, po=f"PO-{1000 + i}")
            doc, _ = insert_invoice(db, tenant, owner, fields, created_at, f"{vendor[0].split()[0].lower()}_invoice_{i + 1}.pdf")
            if i in (3, 9, 15):  # remember three to duplicate later
                originals[i] = (vendor, inv_no, invoice_date, amount)

        print("Planting 3 exact duplicate invoices…")
        for j, (vendor, inv_no, invoice_date, amount) in enumerate(originals.values()):
            fields = make_fields(vendor, inv_no, invoice_date, amount)
            created_at = now - timedelta(hours=random.randint(4, 30))
            doc, _ = insert_invoice(db, tenant, owner, fields, created_at, f"duplicate_resubmission_{j + 1}.pdf")
            if j == 0:
                reject(db, doc, owner, "Duplicate of an already-paid invoice. Rejected.")

        print("Planting 2 invalid-GSTIN invoices…")
        for j, vendor in enumerate(BAD_GSTIN_VENDORS):
            invoice_date = (now - timedelta(days=random.randint(3, 10))).date()
            fields = make_fields(vendor, f"SG-{j + 1}-2026", invoice_date, 68500 + j * 12000)
            insert_invoice(db, tenant, owner, fields, now - timedelta(days=j + 1), f"invalid_gstin_{j + 1}.pdf")

        print("Planting amount-in-words mismatch (₹47,500 vs Forty One Thousand Five Hundred)…")
        vendor = LEGIT_VENDORS[4]
        invoice_date = (now - timedelta(days=5)).date()
        fields = make_fields(vendor, "OSE-4471", invoice_date, 47500,
                             words="Forty One Thousand Five Hundred Rupees Only")
        doc, _ = insert_invoice(db, tenant, owner, fields, now - timedelta(days=4), "altered_amount_invoice.pdf")
        reject(db, doc, owner, "Figures were altered — words say ₹41,500. Rejected and vendor contacted.")

        print("Planting future-dated invoice…")
        vendor = LEGIT_VENDORS[7]
        invoice_date = (now + timedelta(days=35)).date()
        fields = make_fields(vendor, "SCA-9911", invoice_date, 89000)
        insert_invoice(db, tenant, owner, fields, now - timedelta(days=2), "future_dated_invoice.pdf")

        print("Planting shared-bank-account invoices (shell company)…")
        # Krishna Traders (legit) invoice first…
        invoice_date = (now - timedelta(days=12)).date()
        fields = make_fields(LEGIT_VENDORS[10], "KT-2201", invoice_date, 134000)
        insert_invoice(db, tenant, owner, fields, now - timedelta(days=12), "krishna_traders_invoice.pdf")
        # …then Raj Enterprises billing against the same bank account
        invoice_date = (now - timedelta(days=1)).date()
        fields = make_fields(SHELL_VENDOR, "RE-0034", invoice_date, 245000)
        insert_invoice(db, tenant, owner, fields, now - timedelta(hours=8), "raj_enterprises_invoice.pdf")

        print("Planting non-whitelisted vendor invoice…")
        invoice_date = (now - timedelta(days=1)).date()
        fields = make_fields(NON_WHITELISTED_VENDOR, "SL-7788", invoice_date, 52000)
        insert_invoice(db, tenant, owner, fields, now - timedelta(hours=5), "speedy_logistics_invoice.pdf")

        total_docs = db.query(Document).filter(Document.tenant_id == tenant.id).count()
        total_flags = (
            db.query(FraudFlag)
            .join(Document, Document.id == FraudFlag.document_id)
            .filter(Document.tenant_id == tenant.id)
            .count()
        )
        print("\n✅ Seed complete!")
        print(f"   Documents: {total_docs}")
        print(f"   Fraud flags: {total_flags}")
        print(f"   Login: {DEMO_EMAIL} / {DEMO_PASSWORD}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
