"""Authentication: register (tenant + owner), login, refresh, me."""
import logging
import re
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.models import FraudRule, Tenant, User
from app.schemas.auth import (
    LoginRequest,
    RefreshRequest,
    RegisterRequest,
    TokenResponse,
    UserResponse,
)
from app.services.audit import write_audit
from app.utils.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/auth", tags=["auth"])

DEFAULT_RULES = (
    ("Duplicate invoice detection", "builtin_duplicate"),
    ("GSTIN format validation", "builtin_gstin"),
    ("Amount vs words mismatch", "builtin_amount_words"),
    ("Future invoice date", "builtin_future_date"),
    ("Shared bank account detection", "builtin_shared_bank"),
)


def _slugify(name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")[:80]
    return slug or "tenant"


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
def register(payload: RegisterRequest, request: Request, db: Session = Depends(get_db)):
    existing = db.query(User).filter(User.email == payload.email.lower()).first()
    if existing:
        raise HTTPException(status_code=409, detail="An account with this email already exists")

    slug = _slugify(payload.company_name)
    if db.query(Tenant).filter(Tenant.slug == slug).first():
        slug = f"{slug}-{uuid.uuid4().hex[:6]}"

    tenant = Tenant(name=payload.company_name, slug=slug)
    db.add(tenant)
    db.flush()

    user = User(
        tenant_id=tenant.id,
        email=payload.email.lower(),
        full_name=payload.full_name,
        hashed_password=hash_password(payload.password),
        role="owner",
    )
    db.add(user)
    db.flush()

    # Seed the five built-in rules so the Rules page is populated from day one
    for rule_name, rule_type in DEFAULT_RULES:
        db.add(
            FraudRule(
                tenant_id=tenant.id,
                rule_name=rule_name,
                rule_type=rule_type,
                is_active=True,
                config={"builtin": True},
                created_by=user.id,
            )
        )
    db.commit()

    write_audit(
        db,
        tenant_id=tenant.id,
        user_id=user.id,
        event_type="auth.register",
        event_data={"email": user.email},
        ip_address=request.client.host if request.client else None,
    )
    return TokenResponse(
        access_token=create_access_token(str(user.id), str(tenant.id), user.role),
        refresh_token=create_refresh_token(str(user.id)),
    )


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, request: Request, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == payload.email.lower()).first()
    if user is None or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Incorrect email or password")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="This account has been deactivated")

    user.last_login = datetime.now(timezone.utc)
    db.commit()
    write_audit(
        db,
        tenant_id=user.tenant_id,
        user_id=user.id,
        event_type="auth.login",
        ip_address=request.client.host if request.client else None,
    )
    return TokenResponse(
        access_token=create_access_token(str(user.id), str(user.tenant_id), user.role),
        refresh_token=create_refresh_token(str(user.id)),
    )


@router.post("/refresh", response_model=TokenResponse)
def refresh(payload: RefreshRequest, db: Session = Depends(get_db)):
    data = decode_token(payload.refresh_token)
    if not data or data.get("type") != "refresh":
        raise HTTPException(status_code=401, detail="Invalid refresh token")
    try:
        user_id = uuid.UUID(data.get("sub", ""))
    except ValueError:
        raise HTTPException(status_code=401, detail="Invalid refresh token")
    user = db.query(User).filter(User.id == user_id, User.is_active.is_(True)).first()
    if user is None:
        raise HTTPException(status_code=401, detail="Invalid refresh token")
    return TokenResponse(
        access_token=create_access_token(str(user.id), str(user.tenant_id), user.role),
        refresh_token=create_refresh_token(str(user.id)),
    )


@router.get("/me", response_model=UserResponse)
def me(user: User = Depends(get_current_user)):
    return user
