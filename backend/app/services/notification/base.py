from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session
from app.models.risk_alert import Alert, NotificationLog


class BaseNotificationProvider(ABC):
    """
    Abstract interface for alert notification channels.
    """
    channel_name: str = "BASE"

    @abstractmethod
    def send_alert_notification(
        self,
        db: Session,
        alert: Alert,
        recipient: str,
        config: Optional[Dict[str, Any]] = None
    ) -> NotificationLog:
        """
        Processes and dispatches an alert notification or creates an audit record.
        """
        pass
