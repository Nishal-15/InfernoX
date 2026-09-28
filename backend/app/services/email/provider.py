"""
InfernoX Phase 9: Production Email Provider Abstraction
Handles system transactional emails: verification, invitations, password resets, critical alerts.
Configurable via environment variables (SMTP or Console Mock for dev/test).
"""

import smtplib
from abc import ABC, abstractmethod
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Dict, Any, Optional
import structlog

from app.core.config import settings

logger = structlog.get_logger(__name__)


class EmailProvider(ABC):
    """
    Abstract email provider for transactional notifications.
    """

    @abstractmethod
    def send(
        self,
        to_email: str,
        subject: str,
        body_text: str,
        body_html: Optional[str] = None
    ) -> bool:
        """Sends a plain text / HTML email message."""
        pass

    @abstractmethod
    def send_template(
        self,
        to_email: str,
        template_name: str,
        context: Dict[str, Any]
    ) -> bool:
        """Sends a templated email with context substitution."""
        pass


class ConsoleEmailProvider(EmailProvider):
    """
    Development & Test provider that logs outbound emails safely without external network calls.
    """

    def send(
        self,
        to_email: str,
        subject: str,
        body_text: str,
        body_html: Optional[str] = None
    ) -> bool:
        logger.info(
            "email_dispatched_console",
            to=to_email,
            subject=subject,
            preview=body_text[:120]
        )
        return True

    def send_template(
        self,
        to_email: str,
        template_name: str,
        context: Dict[str, Any]
    ) -> bool:
        subject, body = _render_template(template_name, context)
        return self.send(to_email, subject, body)


class SMTPEmailProvider(EmailProvider):
    """
    Production SMTP email provider using standard Python smtplib with TLS.
    """

    def __init__(
        self,
        host: str = settings.SMTP_HOST,
        port: int = settings.SMTP_PORT,
        user: str = settings.SMTP_USER,
        password: str = settings.SMTP_PASSWORD,
        from_email: str = settings.EMAILS_FROM_EMAIL or "noreply@infernox.ai"
    ):
        self.host = host
        self.port = port
        self.user = user
        self.password = password
        self.from_email = from_email

    def send(
        self,
        to_email: str,
        subject: str,
        body_text: str,
        body_html: Optional[str] = None
    ) -> bool:
        if not self.host or not self.user:
            logger.warning("smtp_not_configured_falling_back_to_console")
            return ConsoleEmailProvider().send(to_email, subject, body_text, body_html)

        try:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = self.from_email
            msg["To"] = to_email

            part1 = MIMEText(body_text, "plain")
            msg.attach(part1)

            if body_html:
                part2 = MIMEText(body_html, "html")
                msg.attach(part2)

            with smtplib.SMTP(self.host, self.port) as server:
                server.starttls()
                server.login(self.user, self.password)
                server.sendmail(self.from_email, [to_email], msg.as_string())

            logger.info("smtp_email_sent_successfully", to=to_email, subject=subject)
            return True
        except Exception as e:
            logger.error("smtp_email_send_failed", to=to_email, error=str(e))
            return False

    def send_template(
        self,
        to_email: str,
        template_name: str,
        context: Dict[str, Any]
    ) -> bool:
        subject, body = _render_template(template_name, context)
        return self.send(to_email, subject, body)


def _render_template(template_name: str, context: Dict[str, Any]) -> tuple[str, str]:
    """Simple safe string substitution for transactional email templates."""
    if template_name == "invitation":
        org = context.get("organization_name", "InfernoX Organization")
        inviter = context.get("inviter_name", "An administrator")
        role = context.get("role", "Member")
        token = context.get("token", "")
        subject = f"Invitation to join {org} on InfernoX"
        body = (
            f"Hello,\n\n"
            f"{inviter} has invited you to join '{org}' on InfernoX as {role}.\n\n"
            f"Please accept your invitation using your token:\n{token}\n\n"
            f"Welcome to the Autonomous Thermal Intelligence Platform.\n"
            f"— InfernoX Team"
        )
        return subject, body

    elif template_name == "password_reset":
        token = context.get("token", "")
        subject = "InfernoX Password Reset Request"
        body = (
            f"Hello,\n\n"
            f"A password reset request was received for your InfernoX account.\n"
            f"Reset Token: {token}\n\n"
            f"If you did not request this, please ignore this email.\n"
        )
        return subject, body

    elif template_name == "critical_alert":
        facility = context.get("facility_name", "Unknown Facility")
        frp = context.get("frp", "N/A")
        subject = f"[CRITICAL ALERT] Thermal Anomaly detected at {facility}"
        body = (
            f"CRITICAL THERMAL ALERT\n\n"
            f"Facility: {facility}\n"
            f"Max FRP: {frp} MW\n"
            f"Classification: {context.get('classification', 'Unconfirmed')}\n"
            f"View in Mission Control: {context.get('url', 'https://infernox.ai')}\n"
        )
        return subject, body

    # Default fallback
    return (
        f"InfernoX Notification: {template_name}",
        f"System notification for event: {template_name}\nDetails: {context}"
    )


# Factory function to get active email provider
def get_email_provider() -> EmailProvider:
    if settings.EMAIL_PROVIDER.lower() == "smtp" and settings.SMTP_HOST:
        return SMTPEmailProvider()
    return ConsoleEmailProvider()
