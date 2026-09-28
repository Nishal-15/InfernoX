"""
InfernoX Phase 9: Outbound Webhook Dispatcher
Delivers signed, timestamped event notifications to organization-configured endpoints with retry policy.
"""

import json
import time
import httpx
from datetime import datetime, timezone
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session
import structlog

from app.models.saas import WebhookEndpoint
from app.core.security import generate_webhook_signature

logger = structlog.get_logger(__name__)

MAX_RETRIES = 3
INITIAL_BACKOFF = 0.5  # seconds
MAX_CONSECUTIVE_FAILURES = 10


def dispatch_organization_webhook(
    db: Session,
    organization_id: str,
    event_type: str,
    data: Dict[str, Any]
) -> int:
    """
    Finds active webhook endpoints registered for this organization and event type,
    then dispatches signed payloads to them.
    Returns the count of endpoints dispatched to.
    """
    endpoints = db.query(WebhookEndpoint).filter(
        WebhookEndpoint.organization_id == organization_id,
        WebhookEndpoint.is_active == True
    ).all()

    dispatched_count = 0
    now_ts = int(time.time())
    iso_time = datetime.now(timezone.utc).isoformat()

    for ep in endpoints:
        # Check if subscribed to this event type
        if ep.subscribed_events and event_type not in ep.subscribed_events:
            continue

        payload_dict = {
            "id": f"evt_{now_ts}_{ep.id[:8]}",
            "event": event_type,
            "organization_id": organization_id,
            "created_at": iso_time,
            "data": data
        }

        payload_bytes = json.dumps(payload_dict, default=str).encode("utf-8")
        signature = generate_webhook_signature(payload_bytes, ep.secret)

        headers = {
            "Content-Type": "application/json",
            "X-InfernoX-Signature": f"sha256={signature}",
            "X-InfernoX-Timestamp": str(now_ts),
            "X-InfernoX-Event": event_type,
            "User-Agent": "InfernoX-Webhook-Delivery/1.0"
        }

        success = _deliver_with_retry(ep.url, payload_bytes, headers)

        ep.last_triggered_at = datetime.now(timezone.utc)
        if success:
            ep.consecutive_failures = 0
            dispatched_count += 1
        else:
            ep.consecutive_failures = (ep.consecutive_failures or 0) + 1
            if ep.consecutive_failures >= MAX_CONSECUTIVE_FAILURES:
                ep.is_active = False
                logger.warning(
                    "webhook_endpoint_disabled_excessive_failures",
                    endpoint_id=ep.id,
                    url=ep.url,
                    failures=ep.consecutive_failures
                )

    try:
        db.commit()
    except Exception as e:
        db.rollback()
        logger.error("webhook_status_commit_failed", error=str(e))

    return dispatched_count


def _deliver_with_retry(url: str, payload_bytes: bytes, headers: Dict[str, str]) -> bool:
    """Delivers payload with exponential backoff retry."""
    backoff = INITIAL_BACKOFF
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            with httpx.Client(timeout=5.0) as client:
                res = client.post(url, content=payload_bytes, headers=headers)
                if 200 <= res.status_code < 300:
                    logger.info("webhook_delivered_success", url=url, attempt=attempt, status=res.status_code)
                    return True
                else:
                    logger.warning(
                        "webhook_delivery_http_error",
                        url=url,
                        attempt=attempt,
                        status=res.status_code
                    )
        except Exception as exc:
            logger.warning("webhook_delivery_attempt_failed", url=url, attempt=attempt, error=str(exc))

        if attempt < MAX_RETRIES:
            time.sleep(backoff)
            backoff *= 2

    return False
