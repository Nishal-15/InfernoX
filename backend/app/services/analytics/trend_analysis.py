from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.models.thermal_event import ThermalEvent
from app.models.risk_alert import RiskAssessment, Alert
from app.schemas.analytics import TrendSummary


class TrendAnalysisService:
    @staticmethod
    def calculate_trends(
        db: Session,
        current_start: datetime,
        current_end: datetime
    ) -> Dict[str, TrendSummary]:
        """
        Compare current observation window with previous equivalent window.
        """
        duration = current_end - current_start
        if duration.total_seconds() <= 0:
            duration = timedelta(days=30)

        prev_start = current_start - duration
        prev_end = current_start

        # 1. Event count & FRP current
        curr_events = db.query(ThermalEvent.frp).filter(
            ThermalEvent.detected_at >= current_start,
            ThermalEvent.detected_at <= current_end
        ).all()
        curr_cnt = len(curr_events)
        curr_frps = [e[0] for e in curr_events if e[0] is not None]
        curr_avg_frp = float(sum(curr_frps) / len(curr_frps)) if curr_frps else 0.0

        # 2. Event count & FRP previous
        prev_events = db.query(ThermalEvent.frp).filter(
            ThermalEvent.detected_at >= prev_start,
            ThermalEvent.detected_at < prev_end
        ).all()
        prev_cnt = len(prev_events)
        prev_frps = [e[0] for e in prev_events if e[0] is not None]
        prev_avg_frp = float(sum(prev_frps) / len(prev_frps)) if prev_frps else 0.0

        # 3. Alert count current & previous
        curr_alerts_cnt = db.query(Alert).filter(
            Alert.created_at >= current_start,
            Alert.created_at <= current_end
        ).count()
        prev_alerts_cnt = db.query(Alert).filter(
            Alert.created_at >= prev_start,
            Alert.created_at < prev_end
        ).count()

        # Helper for trend evaluation
        def evaluate_metric(name: str, cur: float, prev: float, unit: str = "") -> TrendSummary:
            if prev > 0:
                pct = round(((cur - prev) / prev) * 100.0, 1)
            else:
                pct = 100.0 if cur > 0 else 0.0

            if prev == 0 and cur > 0:
                state = "EMERGING"
            elif abs(pct) <= 5.0:
                state = "STABLE"
            elif pct > 5.0:
                state = "INCREASING"
            else:
                state = "DECREASING"

            sign = "+" if pct > 0 else ""
            explanation = f"Current period: {round(cur, 1)}{unit} vs Previous: {round(prev, 1)}{unit} ({sign}{pct}%)."

            return TrendSummary(
                metric=name,
                current=round(cur, 2),
                previous=round(prev, 2),
                delta_pct=pct,
                state=state,
                explanation=explanation
            )

        return {
            "event_volume": evaluate_metric("Event Volume", float(curr_cnt), float(prev_cnt), " events"),
            "average_frp": evaluate_metric("Average FRP", curr_avg_frp, prev_avg_frp, " MW"),
            "alert_volume": evaluate_metric("Alert Volume", float(curr_alerts_cnt), float(prev_alerts_cnt), " alerts")
        }
