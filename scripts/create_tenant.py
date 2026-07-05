"""Quick tenant + owner setup script.

Usage (inside backend container):
    docker compose exec backend python scripts/create_tenant.py \
        "Acme Industries" "Priya Patel" priya@acme.in StrongPass1
"""
import re
import sys

sys.path.insert(0, "/app")
sys.path.insert(0, ".")

from app.database import SessionLocal  # noqa: E402
from app.models import FraudRule, Tenant, User  # noqa: E402
from app.utils.security import hash_password  # noqa: E402


def main():
    if len(sys.argv) != 5:
        print(__doc__)
        sys.exit(1)
    company, full_name, email, password = sys.argv[1:5]

    db = SessionLocal()
    try:
        if db.query(User).filter(User.email == email.lower()).first():
            print(f"User {email} already exists.")
            sys.exit(1)
        slug = re.sub(r"[^a-z0-9]+", "-", company.lower()).strip("-")
        tenant = Tenant(name=company, slug=slug)
        db.add(tenant)
        db.flush()
        user = User(
            tenant_id=tenant.id,
            email=email.lower(),
            full_name=full_name,
            hashed_password=hash_password(password),
            role="owner",
        )
        db.add(user)
        for rule_name, rule_type in (
            ("Duplicate invoice detection", "builtin_duplicate"),
            ("GSTIN format validation", "builtin_gstin"),
            ("Amount vs words mismatch", "builtin_amount_words"),
            ("Future invoice date", "builtin_future_date"),
            ("Shared bank account detection", "builtin_shared_bank"),
        ):
            db.add(FraudRule(tenant_id=tenant.id, rule_name=rule_name,
                             rule_type=rule_type, is_active=True, config={"builtin": True}))
        db.commit()
        print(f"✅ Created tenant '{company}' with owner {email}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
