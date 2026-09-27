from datetime import datetime, timezone
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session
from app.models.risk_alert import Alert, NotificationLog
from app.services.notification.base import BaseNotificationProvider


class EmailNotificationProvider(BaseNotificationProvider):
    channel_name: str = "EMAIL"

    def __init__(self, integration_enabled: bool = False):
        self.integration_enabled = integration_enabled

    def send_alert_notification(
        self,
        db: Session,
        alert: Alert,
        recipient: str,
        config: Optional[Dict[str, Any]] = None
    ) -> NotificationLog:
        payload = {
            "channel": self.channel_name,
            "recipient": recipient,
            "subject": f"[{alert.severity}] {alert.title}",
            "body": alert.message,
            "prepared_at": datetime.now(timezone.utc).isoformat()
        }

        # Safety check: if integration is disabled, record status as DISABLED
        status = "PENDING" if self.integration_enabled else "DISABLED"

        log = NotificationLog(
            alert_id=alert.id,
            channel=self.channel_name,
            recipient=recipient,
            status=status,
            payload_json=payload,
            created_at=datetime.now(timezone.utc)
        )
        db.add(log)
        db.commit()
        db.refresh(log)
        return log


class WebhookNotificationProvider(BaseNotificationProvider):
    channel_name: str = "WEBHOOK"

    def __init__(self, integration_enabled: bool = False):
        self.integration_enabled = integration_enabled

    def send_alert_notification(
        self,
        db: Session,
        alert: Alert,
        recipient: str,  # webhook URL
        config: Optional[Dict[str, Any]] = None
    ) -> NotificationLog:
        payload = {
            "channel": self.channel_name,
            "webhook_url": recipient,
            "incident_payload": alert.incident_payload_json,
            "prepared_at": datetime.now(timezone.utc).isoformat()
        }

        status = "PENDING" if self.integration_enabled else "DISABLED"

        log = NotificationLog(
            alert_id=alert.id,
            channel=self.channel_name,
            recipient=recipient,
            status=status,
            payload_json=payload,
            created_at=datetime.now(timezone.utc)
        )
        db.add(log)
        db.commit()
        db.refresh(log)
        return log


class SMSNotificationProvider(BaseNotificationProvider):
    channel_name: str = "SMS"

    def __init__(self, integration_enabled: bool = False):
        self.integration_enabled = integration_enabled

    def send_alert_notification(
        self,
        db: Session,
        alert: Alert,
        recipient: str,
        config: Optional[Dict[str, Any]] = None
    ) -> NotificationLog:
        payload = {
            "channel": self.channel_name,
            "phone": recipient,
            "message": f"INFERNOX ALERT [{alert.severity}]: {alert.title}",
            "prepared_at": datetime.now(timezone.utc).isoformat()
        }

        status = "PENDING" if self.integration_enabled else "DISABLED"

        log = NotificationLog(
            alert_id=alert.id,
            channel=self.channel_name,
            recipient=recipient,
            status=status,
            payload_json=payload,
            created_at=datetime.now(timezone.utc)
        )
        db.add(log)
        db.commit()
        db.refresh(log)
        return log
