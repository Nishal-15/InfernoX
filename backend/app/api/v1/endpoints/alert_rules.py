from datetime import datetime, timezone
from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.models.risk_alert import AlertRule
from app.schemas.risk_alert import AlertRuleCreate, AlertRuleUpdate, AlertRuleResponse

router = APIRouter()


@router.get("", response_model=List[AlertRuleResponse])
def list_alert_rules(db: Session = Depends(get_db)):
    """
    List all configured alert rules.
    """
    return db.query(AlertRule).order_by(AlertRule.id.asc()).all()


@router.post("", response_model=AlertRuleResponse, status_code=201)
def create_alert_rule(rule_in: AlertRuleCreate, db: Session = Depends(get_db)):
    """
    Create a new structured alert rule.
    """
    existing = db.query(AlertRule).filter(AlertRule.name == rule_in.name).first()
    if existing:
        raise HTTPException(status_code=400, detail=f"Alert rule '{rule_in.name}' already exists")

    rule = AlertRule(
        name=rule_in.name,
        description=rule_in.description,
        enabled=rule_in.enabled,
        severity=rule_in.severity.upper(),
        conditions_json=rule_in.conditions,
        cooldown_minutes=rule_in.cooldown_minutes,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc)
    )
    db.add(rule)
    db.commit()
    db.refresh(rule)
    return rule


@router.patch("/{rule_id}", response_model=AlertRuleResponse)
def update_alert_rule(rule_id: int, rule_in: AlertRuleUpdate, db: Session = Depends(get_db)):
    """
    Update an existing alert rule's configuration, conditions, or status.
    """
    rule = db.query(AlertRule).filter(AlertRule.id == rule_id).first()
    if not rule:
        raise HTTPException(status_code=404, detail=f"Alert rule {rule_id} not found")

    if rule_in.name is not None:
        rule.name = rule_in.name
    if rule_in.description is not None:
        rule.description = rule_in.description
    if rule_in.enabled is not None:
        rule.enabled = rule_in.enabled
    if rule_in.severity is not None:
        rule.severity = rule_in.severity.upper()
    if rule_in.conditions is not None:
        rule.conditions_json = rule_in.conditions
    if rule_in.cooldown_minutes is not None:
        rule.cooldown_minutes = rule_in.cooldown_minutes

    rule.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(rule)
    return rule
