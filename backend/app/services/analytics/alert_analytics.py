from datetime import datetime
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.models.risk_alert import Alert
from app.schemas.analytics import AlertAnalyticsResponse


class AlertAnalyticsService:
    @staticmethod
    def get_alert_analytics(
        db: Session,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> AlertAnalyticsResponse:
        """
        Aggregate alert counts, escalation rates, and mean operational response times.
        """
        query = db.query(Alert)
        if start_date:
            query = query.filter(Alert.created_at >= start_date)
        if end_date:
            query = query.filter(Alert.created_at <= end_date)

        alerts = query.all()
        total_alerts = len(alerts)

        by_severity = {"CRITICAL": 0, "HIGH": 0, "MODERATE": 0, "LOW": 0}
        by_status = {
            "NEW": 0,
            "ACKNOWLEDGED": 0,
            "INVESTIGATING": 0,
            "ESCALATED": 0,
            "RESOLVED": 0,
            "DISMISSED": 0
        }

        if total_alerts == 0:
            return AlertAnalyticsResponse(
                total_alerts=0,
                by_severity=by_severity,
                by_status=by_status,
                escalation_rate=0.0,
                resolution_rate=0.0,
                avg_resolution_time_minutes=0.0,
                avg_acknowledgement_time_minutes=0.0
            )

        resolution_times = []
        ack_times = []

        for a in alerts:
            sev = (a.severity or "LOW").upper()
            by_severity[sev] = by_severity.get(sev, 0) + 1

            st = (a.status or "NEW").upper()
            by_status[st] = by_status.get(st, 0) + 1

            if a.acknowledged_at and a.created_at:
                delta_ack = (a.acknowledged_at - a.created_at).total_seconds() / 60.0
                if delta_ack >= 0:
                    ack_times.append(delta_ack)

            if a.resolved_at and a.created_at:
                delta_res = (a.resolved_at - a.created_at).total_seconds() / 60.0
                if delta_res >= 0:
                    resolution_times.append(delta_res)

        escalated_count = by_status.get("ESCALATED", 0)
        resolved_count = by_status.get("RESOLVED", 0)
        escalation_rate = round(float(escalated_count / total_alerts), 3) if total_alerts > 0 else 0.0
        resolution_rate = round(float(resolved_count / total_alerts), 3) if total_alerts > 0 else 0.0

        avg_res_min = round(float(sum(resolution_times) / len(resolution_times)), 1) if resolution_times else 0.0
        avg_ack_min = round(float(sum(ack_times) / len(ack_times)), 1) if ack_times else 0.0

        return AlertAnalyticsResponse(
            total_alerts=total_alerts,
            by_severity=by_severity,
            by_status=by_status,
            escalation_rate=escalation_rate,
            resolution_rate=resolution_rate,
            avg_resolution_time_minutes=avg_res_min,
            avg_acknowledgement_time_minutes=avg_ack_min
        )
