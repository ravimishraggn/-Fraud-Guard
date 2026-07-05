"""Fraud rule endpoints. Built-in rules can be disabled, never deleted."""
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user, require_roles
from app.models import FraudRule, User
from app.schemas.fraud import FraudRuleCreate, FraudRuleResponse, FraudRuleUpdate

router = APIRouter(prefix="/api/v1/rules", tags=["rules"])


def _get_tenant_rule(rule_id: uuid.UUID, user: User, db: Session) -> FraudRule:
    rule = (
        db.query(FraudRule)
        .filter(FraudRule.id == rule_id, FraudRule.tenant_id == user.tenant_id)
        .first()
    )
    if rule is None:
        raise HTTPException(status_code=404, detail="Rule not found")
    return rule


@router.get("", response_model=list[FraudRuleResponse])
def list_rules(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return (
        db.query(FraudRule)
        .filter(FraudRule.tenant_id == user.tenant_id)
        .order_by(FraudRule.created_at)
        .all()
    )


@router.post("", response_model=FraudRuleResponse, status_code=status.HTTP_201_CREATED)
def create_rule(
    payload: FraudRuleCreate,
    user: User = Depends(require_roles("owner", "operator")),
    db: Session = Depends(get_db),
):
    rule = FraudRule(
        tenant_id=user.tenant_id,
        rule_name=payload.rule_name,
        rule_type=payload.rule_type,
        config=payload.config,
        created_by=user.id,
    )
    db.add(rule)
    db.commit()
    db.refresh(rule)
    return rule


@router.put("/{rule_id}", response_model=FraudRuleResponse)
def update_rule(
    rule_id: uuid.UUID,
    payload: FraudRuleUpdate,
    user: User = Depends(require_roles("owner", "operator")),
    db: Session = Depends(get_db),
):
    rule = _get_tenant_rule(rule_id, user, db)
    updates = payload.model_dump(exclude_unset=True)
    if rule.rule_type.startswith("builtin_") and "rule_name" in updates:
        del updates["rule_name"]  # built-in rule names are fixed
    for field, value in updates.items():
        setattr(rule, field, value)
    db.commit()
    db.refresh(rule)
    return rule


@router.delete("/{rule_id}", response_model=FraudRuleResponse)
def disable_rule(
    rule_id: uuid.UUID,
    user: User = Depends(require_roles("owner", "operator")),
    db: Session = Depends(get_db),
):
    """Rules are never hard-deleted — DELETE disables them."""
    rule = _get_tenant_rule(rule_id, user, db)
    rule.is_active = False
    db.commit()
    db.refresh(rule)
    return rule
