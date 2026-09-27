from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session

from app.schemas.analytics import (
    AnalyticsFilterParams,
    KPISummary,
    TimeSeriesResponse,
    ClassificationAnalyticsResponse,
    RiskAnalyticsResponse,
    AlertAnalyticsResponse,
    GeospatialHeatmapResponse
)
from app.services.analytics.event_analytics import EventAnalyticsService
from app.services.analytics.classification_analytics import ClassificationAnalyticsService
from app.services.analytics.risk_analytics import RiskAnalyticsService
from app.services.analytics.alert_analytics import AlertAnalyticsService
from app.services.analytics.facility_analytics import FacilityAnalyticsService
from app.services.analytics.geospatial_analytics import GeospatialAnalyticsService
from app.services.analytics.trend_analysis import TrendAnalysisService
from app.services.analytics.comparison_service import ComparisonService
from app.services.analytics.anomaly_analytics import AnomalyAnalyticsService


class AnalyticsService:
    @staticmethod
    def resolve_date_range(
        range_preset: Optional[str] = "30d",
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> tuple[datetime, datetime]:
        """
        Convert filter parameters or preset shortcuts into concrete UTC datetime bounds.
        """
        now = datetime.now(timezone.utc)
        if range_preset == "custom" and start_date and end_date:
            return start_date, end_date

        preset = (range_preset or "30d").lower()
        if preset == "24h":
            return now - timedelta(hours=24), now
        elif preset == "7d":
            return now - timedelta(days=7), now
        elif preset == "90d":
            return now - timedelta(days=90), now
        elif preset == "6m":
            return now - timedelta(days=180), now
        elif preset == "1y":
            return now - timedelta(days=365), now
        else:  # default 30d
            return now - timedelta(days=30), now

    @staticmethod
    def get_overview_kpis(
        db: Session,
        filters: Optional[AnalyticsFilterParams] = None
    ) -> KPISummary:
        """
        Assemble unified executive KPIs from real database entities.
        """
        range_p = filters.range_preset if filters else "30d"
        s_date = filters.start_date if filters else None
        e_date = filters.end_date if filters else None
        min_f = filters.min_frp if filters else None
        max_f = filters.max_frp if filters else None

        start_dt, end_dt = AnalyticsService.resolve_date_range(range_p, s_date, e_date)

        event_kpis = EventAnalyticsService.get_event_kpis(
            db, start_date=start_dt, end_date=end_dt, min_frp=min_f, max_frp=max_f
        )
        risk_kpis = RiskAnalyticsService.get_risk_analytics(
            db, start_date=start_dt, end_date=end_dt
        )
        alert_kpis = AlertAnalyticsService.get_alert_analytics(
            db, start_date=start_dt, end_date=end_dt
        )
        trends = TrendAnalysisService.calculate_trends(
            db, current_start=start_dt, current_end=end_dt
        )

        return KPISummary(
            total_events=event_kpis["total_events"],
            new_events_count=event_kpis["new_events_count"],
            recurring_events_count=event_kpis["recurring_events_count"],
            persistent_sources_count=event_kpis["persistent_sources_count"],
            abnormal_events_count=event_kpis["abnormal_events_count"],
            avg_frp=event_kpis["avg_frp"],
            max_frp=event_kpis["max_frp"],
            total_frp=event_kpis["total_frp"],
            avg_risk_score=risk_kpis.avg_score,
            max_risk_score=risk_kpis.max_score,
            critical_risk_count=risk_kpis.distribution.get("CRITICAL", 0),
            high_risk_count=risk_kpis.distribution.get("HIGH", 0),
            moderate_risk_count=risk_kpis.distribution.get("MODERATE", 0),
            low_risk_count=risk_kpis.distribution.get("LOW", 0),
            total_alerts=alert_kpis.total_alerts,
            active_alerts=(
                alert_kpis.by_status.get("NEW", 0) +
                alert_kpis.by_status.get("ACKNOWLEDGED", 0) +
                alert_kpis.by_status.get("INVESTIGATING", 0) +
                alert_kpis.by_status.get("ESCALATED", 0)
            ),
            escalated_alerts=alert_kpis.by_status.get("ESCALATED", 0),
            resolved_alerts=alert_kpis.by_status.get("RESOLVED", 0),
            trends=trends,
            calculated_at=datetime.now(timezone.utc).isoformat()
        )
