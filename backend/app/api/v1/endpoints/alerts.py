from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.api.deps import get_db
from app.models.risk_alert import Alert, AlertAuditLog
from app.schemas.risk_alert import (
    AlertResponse,
    AlertListResponse,
    AlertActionRequest,
    AlertStatsSummary
)
from app.services.alert.engine import AlertEngine

router = APIRouter()


@router.get("", response_model=AlertListResponse)
def list_alerts(
    severity: Optional[str] = Query(None, description="Filter by severity: CRITICAL, HIGH, MODERATE, LOW"),
    status: Optional[str] = Query(None, description="Filter by status: NEW, ACKNOWLEDGED, INVESTIGATING, ESCALATED, RESOLVED, DISMISSED"),
    event_id: Optional[int] = Query(None, description="Filter by thermal event ID"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """
    List alerts with optional filtering by severity, status, and event ID.
    """
    query = db.query(Alert)

    if severity:
        query = query.filter(Alert.severity == severity.upper())
    if status:
        query = query.filter(Alert.status == status.upper())
    if event_id:
        query = query.filter(Alert.event_id == event_id)

    total = query.count()
    items = query.order_by(Alert.created_at.desc()).offset(skip).limit(limit).all()

    return {"total": total, "items": items}


@router.get("/stats/summary", response_model=AlertStatsSummary)
def get_alert_stats(db: Session = Depends(get_db)):
    """
    Aggregated summary KPIs of alert counts grouped by severity and lifecycle status.
    """
    total = db.query(func.count(Alert.id)).scalar() or 0
    critical_c = db.query(func.count(Alert.id)).filter(Alert.severity == "CRITICAL").scalar() or 0
    high_c = db.query(func.count(Alert.id)).filter(Alert.severity == "HIGH").scalar() or 0
    mod_c = db.query(func.count(Alert.id)).filter(Alert.severity == "MODERATE").scalar() or 0
    low_c = db.query(func.count(Alert.id)).filter(Alert.severity == "LOW").scalar() or 0

    new_c = db.query(func.count(Alert.id)).filter(Alert.status == "NEW").scalar() or 0
    ack_c = db.query(func.count(Alert.id)).filter(Alert.status == "ACKNOWLEDGED").scalar() or 0
    inv_c = db.query(func.count(Alert.id)).filter(Alert.status == "INVESTIGATING").scalar() or 0
    esc_c = db.query(func.count(Alert.id)).filter(Alert.status == "ESCALATED").scalar() or 0
    res_c = db.query(func.count(Alert.id)).filter(Alert.status == "RESOLVED").scalar() or 0

    return {
        "total_alerts": total,
        "critical_count": critical_c,
        "high_count": high_c,
        "moderate_count": mod_c,
        "low_count": low_c,
        "new_count": new_c,
        "acknowledged_count": ack_c,
        "investigating_count": inv_c,
        "escalated_count": esc_c,
        "resolved_count": res_c,
        "avg_acknowledgement_minutes": None
    }


@router.get("/{alert_id}", response_model=AlertResponse)
def get_alert(alert_id: int, db: Session = Depends(get_db)):
    """
    Retrieve single alert with complete incident payload and audit history.
    """
    alert = db.query(Alert).filter(Alert.id == alert_id).first()
    if not alert:
        raise HTTPException(status_code=404, detail=f"Alert {alert_id} not found")
    return alert


@router.post("/{alert_id}/acknowledge", response_model=AlertResponse)
def acknowledge_alert(
    alert_id: int,
    action: AlertActionRequest,
    db: Session = Depends(get_db)
):
    """
    Acknowledge an alert to verify receipt and assign to analyst.
    """
    try:
        return AlertEngine.transition_status(
            db=db,
            alert_id=alert_id,
            target_status="ACKNOWLEDGED",
            actor=action.actor,
            comment=action.comment
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{alert_id}/investigate", response_model=AlertResponse)
def investigate_alert(
    alert_id: int,
    action: AlertActionRequest,
    db: Session = Depends(get_db)
):
    """
    Transition alert into active investigation status.
    """
    try:
        return AlertEngine.transition_status(
            db=db,
            alert_id=alert_id,
            target_status="INVESTIGATING",
            actor=action.actor,
            comment=action.comment
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{alert_id}/escalate", response_model=AlertResponse)
def escalate_alert(
    alert_id: int,
    action: AlertActionRequest,
    db: Session = Depends(get_db)
):
    """
    Escalate an alert to incident supervisor or designated response contact.
    """
    try:
        return AlertEngine.transition_status(
            db=db,
            alert_id=alert_id,
            target_status="ESCALATED",
            actor=action.actor,
            comment=action.comment
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{alert_id}/resolve", response_model=AlertResponse)
def resolve_alert(
    alert_id: int,
    action: AlertActionRequest,
    db: Session = Depends(get_db)
):
    """
    Resolve an alert when threat is contained or remediated.
    """
    try:
        return AlertEngine.transition_status(
            db=db,
            alert_id=alert_id,
            target_status="RESOLVED",
            actor=action.actor,
            comment=action.comment
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{alert_id}/dismiss", response_model=AlertResponse)
def dismiss_alert(
    alert_id: int,
    action: AlertActionRequest,
    db: Session = Depends(get_db)
):
    """
    Dismiss an alert as false positive or non-actionable anomaly.
    """
    try:
        return AlertEngine.transition_status(
            db=db,
            alert_id=alert_id,
            target_status="DISMISSED",
            actor=action.actor,
            comment=action.comment
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
