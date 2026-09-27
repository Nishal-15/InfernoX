from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func, desc

from app.models.thermal_event import ThermalEvent
from app.models.risk_alert import RiskAssessment, Alert
from app.schemas.analytics import TimeSeriesPoint, TimeSeriesResponse


class EventAnalyticsService:
    @staticmethod
    def get_event_kpis(
        db: Session,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        min_frp: Optional[float] = None,
        max_frp: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Compute high-level thermal event metrics from actual database records.
        """
        query = db.query(ThermalEvent)
        if start_date:
            query = query.filter(ThermalEvent.detected_at >= start_date)
        if end_date:
            query = query.filter(ThermalEvent.detected_at <= end_date)
        if min_frp is not None:
            query = query.filter(ThermalEvent.frp >= min_frp)
        if max_frp is not None:
            query = query.filter(ThermalEvent.frp <= max_frp)

        events = query.all()
        total_events = len(events)
        if total_events == 0:
            return {
                "total_events": 0,
                "new_events_count": 0,
                "recurring_events_count": 0,
                "persistent_sources_count": 0,
                "abnormal_events_count": 0,
                "avg_frp": 0.0,
                "max_frp": 0.0,
                "total_frp": 0.0,
            }

        frp_values = [e.frp for e in events if e.frp is not None]
        avg_frp = round(float(sum(frp_values) / len(frp_values)), 2) if frp_values else 0.0
        max_frp = round(float(max(frp_values)), 2) if frp_values else 0.0
        total_frp = round(float(sum(frp_values)), 2) if frp_values else 0.0

        # Status breakdown
        status_counts = {}
        for e in events:
            st = (e.status or "NEW").upper()
            status_counts[st] = status_counts.get(st, 0) + 1

        # Heuristic/cluster indicators based on active days and detections
        persistent_count = sum(1 for e in events if (e.confidence or 0) > 80 and (e.frp or 0) > 40)
        abnormal_count = sum(1 for e in events if (e.frp or 0) >= 100.0)

        return {
            "total_events": total_events,
            "new_events_count": status_counts.get("NEW", 0),
            "recurring_events_count": status_counts.get("INVESTIGATING", 0) + status_counts.get("CONFIRMED", 0),
            "persistent_sources_count": persistent_count,
            "abnormal_events_count": abnormal_count,
            "avg_frp": avg_frp,
            "max_frp": max_frp,
            "total_frp": total_frp,
        }

    @staticmethod
    def get_timeseries(
        db: Session,
        interval: str = "day",  # hour, day, week, month
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        min_frp: Optional[float] = None
    ) -> TimeSeriesResponse:
        """
        Group events into chronological bins with average FRP and critical indicators.
        """
        now = datetime.now(timezone.utc)
        if not end_date:
            end_date = now
        if not start_date:
            start_date = end_date - timedelta(days=30)

        query = db.query(ThermalEvent).filter(
            ThermalEvent.detected_at >= start_date,
            ThermalEvent.detected_at <= end_date
        )
        if min_frp is not None:
            query = query.filter(ThermalEvent.frp >= min_frp)

        events = query.order_by(ThermalEvent.detected_at.asc()).all()

        # Date bucketing format
        def bucket_key(dt: datetime) -> str:
            if not dt:
                return "Unknown"
            if interval == "hour":
                return dt.strftime("%Y-%m-%d %H:00")
            elif interval == "week":
                return dt.strftime("%Y-W%W")
            elif interval == "month":
                return dt.strftime("%Y-%m")
            return dt.strftime("%Y-%m-%d")

        buckets: Dict[str, List[ThermalEvent]] = {}
        for ev in events:
            k = bucket_key(ev.detected_at)
            if k not in buckets:
                buckets[k] = []
            buckets[k].append(ev)

        # Cross reference risks and alerts for events
        event_ids = [e.id for e in events]
        critical_risk_event_ids = set()
        high_risk_event_ids = set()
        if event_ids:
            risks = db.query(RiskAssessment.event_id, RiskAssessment.risk_level).filter(
                RiskAssessment.event_id.in_(event_ids)
            ).all()
            for r_eid, r_lvl in risks:
                if (r_lvl or "").upper() == "CRITICAL":
                    critical_risk_event_ids.add(r_eid)
                elif (r_lvl or "").upper() == "HIGH":
                    high_risk_event_ids.add(r_eid)

        alerts_by_event: Dict[int, int] = {}
        if event_ids:
            alert_counts = db.query(
                Alert.event_id, func.count(Alert.id)
            ).filter(Alert.event_id.in_(event_ids)).group_by(Alert.event_id).all()
            for a_eid, a_count in alert_counts:
                alerts_by_event[a_eid] = a_count

        points: List[TimeSeriesPoint] = []
        for key in sorted(buckets.keys()):
            ev_list = buckets[key]
            frps = [e.frp for e in ev_list if e.frp is not None]
            avg_frp = round(float(sum(frps) / len(frps)), 2) if frps else 0.0
            max_frp = round(float(max(frps)), 2) if frps else 0.0
            total_frp = round(float(sum(frps)), 2) if frps else 0.0

            crit_count = sum(1 for e in ev_list if e.id in critical_risk_event_ids or (e.frp or 0) >= 80)
            high_count = sum(1 for e in ev_list if e.id in high_risk_event_ids or (e.frp or 0) >= 50)
            alert_count = sum(alerts_by_event.get(e.id, 0) for e in ev_list)

            points.append(
                TimeSeriesPoint(
                    timestamp=key,
                    event_count=len(ev_list),
                    avg_frp=avg_frp,
                    max_frp=max_frp,
                    total_frp=total_frp,
                    critical_count=crit_count,
                    high_risk_count=high_count,
                    alert_count=alert_count
                )
            )

        return TimeSeriesResponse(
            interval=interval,
            start_date=start_date.isoformat(),
            end_date=end_date.isoformat(),
            points=points,
            total_points=len(points)
        )
