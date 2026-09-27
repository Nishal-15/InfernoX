from datetime import datetime, timezone
from typing import List
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.models.risk_alert import NotificationLog, NotificationPreference
from app.schemas.risk_alert import NotificationPreferenceBase, NotificationPreferenceResponse

router = APIRouter()


from sqlalchemy.orm.attributes import flag_modified

@router.get("")
def list_notifications(
    limit: int = Query(20, ge=1, le=100),
    channel: str = Query("IN_APP"),
    unread_only: bool = Query(False),
    db: Session = Depends(get_db)
):
    """
    List recent alert notification items (e.g. for Mission Control header bell).
    """
    query = db.query(NotificationLog).filter(
        NotificationLog.channel == channel.upper()
    )
    logs = query.order_by(NotificationLog.created_at.desc()).limit(limit * 2).all()

    formatted = []
    for l in logs:
        payload = l.payload_json or {}
        is_read = payload.get("is_read", False)
        if unread_only and is_read:
            continue
        formatted.append({
            "id": l.id,
            "alert_id": l.alert_id,
            "channel": l.channel,
            "recipient": l.recipient,
            "title": payload.get("title", f"Alert Notification #{l.alert_id}"),
            "message": payload.get("message", f"Alert #{l.alert_id} dispatched to {l.recipient}"),
            "status": l.status,
            "is_read": is_read,
            "metadata": payload.get("metadata", {}),
            "created_at": l.created_at.isoformat() if l.created_at else None
        })
        if len(formatted) >= limit:
            break

    return formatted


@router.post("/{notification_id}/read")
def mark_read(
    notification_id: int,
    db: Session = Depends(get_db)
):
    """
    Mark an in-app notification as read.
    """
    log = db.query(NotificationLog).filter(NotificationLog.id == notification_id).first()
    if not log:
        raise HTTPException(status_code=404, detail="Notification log not found")
    
    if isinstance(log.payload_json, dict):
        log.payload_json["is_read"] = True
        flag_modified(log, "payload_json")
    db.commit()
    return {"status": "success", "id": notification_id, "is_read": True}


@router.get("/preferences", response_model=NotificationPreferenceResponse)
def get_preferences(
    user_id: str = Query("analyst-default"),
    db: Session = Depends(get_db)
):
    """
    Retrieve user alert subscription and notification preferences.
    """
    pref = db.query(NotificationPreference).filter(NotificationPreference.user_id == user_id).first()
    if not pref:
        pref = NotificationPreference(
            user_id=user_id,
            subscribed_severities=["CRITICAL", "HIGH", "MODERATE"],
            subscribed_categories=["INDUSTRIAL_FIRE", "GAS_FLARE", "WILDFIRE", "PERSISTENT_INDUSTRIAL_THERMAL_SOURCE"],
            in_app_enabled=True,
            email_enabled=False,
            updated_at=datetime.now(timezone.utc)
        )
        db.add(pref)
        db.commit()
        db.refresh(pref)
    return pref


@router.put("/preferences", response_model=NotificationPreferenceResponse)
def update_preferences(
    pref_in: NotificationPreferenceBase,
    user_id: str = Query("analyst-default"),
    db: Session = Depends(get_db)
):
    """
    Update user notification preferences.
    """
    pref = db.query(NotificationPreference).filter(NotificationPreference.user_id == user_id).first()
    if not pref:
        pref = NotificationPreference(user_id=user_id)
        db.add(pref)

    pref.subscribed_severities = pref_in.subscribed_severities
    pref.subscribed_categories = pref_in.subscribed_categories
    pref.in_app_enabled = pref_in.in_app_enabled
    pref.email_enabled = pref_in.email_enabled
    pref.webhook_url = pref_in.webhook_url
    pref.updated_at = datetime.now(timezone.utc)

    db.commit()
    db.refresh(pref)
    return pref
