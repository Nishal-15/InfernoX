from datetime import datetime, timezone
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session
from app.models.risk_alert import Alert, NotificationLog
from app.services.notification.base import BaseNotificationProvider


class InAppNotificationProvider(BaseNotificationProvider):
    channel_name: str = "IN_APP"

    def send_alert_notification(
        self,
        db: Session,
        alert: Alert,
        recipient: str = "mission-control-analysts",
        config: Optional[Dict[str, Any]] = None
    ) -> NotificationLog:
        """
        Creates an in-app notification record displayed in the Mission Control Alert Center.
        """
        payload = {
            "alert_id": alert.id,
            "alert_code": alert.alert_code,
            "severity": alert.severity,
            "title": alert.title,
            "message": alert.message,
            "event_id": alert.event_id,
            "created_at": alert.created_at.isoformat() if alert.created_at else datetime.now(timezone.utc).isoformat()
        }

        log = NotificationLog(
            alert_id=alert.id,
            channel=self.channel_name,
            recipient=recipient,
            status="DELIVERED",
            payload_json=payload,
            created_at=datetime.now(timezone.utc)
        )
        db.add(log)
        db.commit()
        db.refresh(log)
        return log
