from datetime import datetime
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.schemas.analytics import (
    AnalyticsFilterParams,
    KPISummary,
    TimeSeriesResponse,
    ClassificationAnalyticsResponse,
    RiskAnalyticsResponse,
    AlertAnalyticsResponse,
    FacilityMetric,
    FacilityTimelineNode,
    GeospatialHeatmapResponse,
    ComparisonResponse,
    TrendSummary,
    AnomalyItem
)
from app.services.analytics.analytics_service import AnalyticsService
from app.services.analytics.event_analytics import EventAnalyticsService
from app.services.analytics.classification_analytics import ClassificationAnalyticsService
from app.services.analytics.risk_analytics import RiskAnalyticsService
from app.services.analytics.alert_analytics import AlertAnalyticsService
from app.services.analytics.facility_analytics import FacilityAnalyticsService
from app.services.analytics.geospatial_analytics import GeospatialAnalyticsService
from app.services.analytics.trend_analysis import TrendAnalysisService
from app.services.analytics.comparison_service import ComparisonService
from app.services.analytics.anomaly_analytics import AnomalyAnalyticsService

router = APIRouter()


@router.get("/overview", response_model=KPISummary)
def get_analytics_overview(
    range_preset: str = Query("30d", description="24h, 7d, 30d, 90d, 6m, 1y, custom"),
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    min_frp: Optional[float] = None,
    max_frp: Optional[float] = None,
    db: Session = Depends(get_db)
):
    """
    Get executive KPI summary across thermal events, classification, risk, and alerts.
    """
    filters = AnalyticsFilterParams(
        range_preset=range_preset,
        start_date=start_date,
        end_date=end_date,
        min_frp=min_frp,
        max_frp=max_frp
    )
    return AnalyticsService.get_overview_kpis(db, filters)


@router.get("/timeseries", response_model=TimeSeriesResponse)
def get_analytics_timeseries(
    interval: str = Query("day", description="hour, day, week, month"),
    range_preset: str = Query("30d", description="24h, 7d, 30d, 90d, 6m, 1y, custom"),
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    min_frp: Optional[float] = None,
    db: Session = Depends(get_db)
):
    """
    Get chronological event frequency, FRP power excursion, and alert volume time-series.
    """
    s_dt, e_dt = AnalyticsService.resolve_date_range(range_preset, start_date, end_date)
    return EventAnalyticsService.get_timeseries(
        db, interval=interval, start_date=s_dt, end_date=e_dt, min_frp=min_frp
    )


@router.get("/classifications", response_model=ClassificationAnalyticsResponse)
def get_classification_analytics(
    range_preset: str = Query("30d"),
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    risk_level: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Get event distribution, confidence scores, and FRP stats grouped by AI classification.
    """
    s_dt, e_dt = AnalyticsService.resolve_date_range(range_preset, start_date, end_date)
    return ClassificationAnalyticsService.get_classification_breakdown(
        db, start_date=s_dt, end_date=e_dt, risk_level=risk_level
    )


@router.get("/risk", response_model=RiskAnalyticsResponse)
def get_risk_analytics(
    range_preset: str = Query("30d"),
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    db: Session = Depends(get_db)
):
    """
    Get analytical risk score distribution and severity tier statistics.
    """
    s_dt, e_dt = AnalyticsService.resolve_date_range(range_preset, start_date, end_date)
    return RiskAnalyticsService.get_risk_analytics(db, start_date=s_dt, end_date=e_dt)


@router.get("/alerts", response_model=AlertAnalyticsResponse)
def get_alert_analytics(
    range_preset: str = Query("30d"),
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    db: Session = Depends(get_db)
):
    """
    Get alert volume, status distribution, escalation rates, and mean resolution times.
    """
    s_dt, e_dt = AnalyticsService.resolve_date_range(range_preset, start_date, end_date)
    return AlertAnalyticsService.get_alert_analytics(db, start_date=s_dt, end_date=e_dt)


@router.get("/facilities", response_model=List[FacilityMetric])
def get_facility_analytics(
    facility_type: Optional[str] = None,
    min_events: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """
    Rank monitored industrial infrastructure by nearby thermal anomaly count and peak FRP.
    """
    return FacilityAnalyticsService.get_facilities_ranking(
        db, facility_type=facility_type, min_events=min_events, limit=limit
    )


@router.get("/facilities/{facility_id}", response_model=List[FacilityTimelineNode])
def get_facility_timeline(
    facility_id: int,
    days: int = Query(90, ge=1, le=365),
    db: Session = Depends(get_db)
):
    """
    Get chronological thermal detection history and risk status for a specific facility.
    """
    return FacilityAnalyticsService.get_facility_thermal_timeline(db, facility_id=facility_id, days=days)


@router.get("/geospatial", response_model=GeospatialHeatmapResponse)
def get_geospatial_heatmap(
    resolution_deg: float = Query(0.25, ge=0.05, le=2.0),
    range_preset: str = Query("30d"),
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    min_frp: Optional[float] = None,
    db: Session = Depends(get_db)
):
    """
    Get spatial grid binning for heatmap overlay and density analysis.
    """
    s_dt, e_dt = AnalyticsService.resolve_date_range(range_preset, start_date, end_date)
    return GeospatialAnalyticsService.get_spatial_heatmap_grid(
        db, resolution_deg=resolution_deg, start_date=s_dt, end_date=e_dt, min_frp=min_frp
    )


@router.get("/comparison", response_model=ComparisonResponse)
def get_analytics_comparison(
    comparison_type: str = Query("FACILITY", description="FACILITY, TIME_PERIOD"),
    id_a: Optional[int] = None,
    id_b: Optional[int] = None,
    period_a_start: Optional[datetime] = None,
    period_a_end: Optional[datetime] = None,
    period_b_start: Optional[datetime] = None,
    period_b_end: Optional[datetime] = None,
    db: Session = Depends(get_db)
):
    """
    Perform factual side-by-side comparison between facilities or time periods.
    """
    if comparison_type.upper() == "FACILITY":
        if id_a is None or id_b is None:
            raise HTTPException(status_code=400, detail="id_a and id_b are required for FACILITY comparison")
        return ComparisonService.compare_facilities(db, id_a, id_b)
    elif comparison_type.upper() == "TIME_PERIOD":
        if not (period_a_start and period_a_end and period_b_start and period_b_end):
            raise HTTPException(status_code=400, detail="All period bounds required for TIME_PERIOD comparison")
        return ComparisonService.compare_timeframes(
            db, period_a_start, period_a_end, period_b_start, period_b_end
        )
    else:
        raise HTTPException(status_code=400, detail=f"Unsupported comparison type: {comparison_type}")


@router.get("/trends", response_model=Dict[str, TrendSummary])
def get_analytics_trends(
    range_preset: str = Query("30d"),
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    db: Session = Depends(get_db)
):
    """
    Get statistical trend detection comparing current window against previous equivalent window.
    """
    s_dt, e_dt = AnalyticsService.resolve_date_range(range_preset, start_date, end_date)
    return TrendAnalysisService.calculate_trends(db, current_start=s_dt, current_end=e_dt)


@router.get("/anomalies", response_model=List[AnomalyItem])
def get_analytics_anomalies(
    limit: int = Query(20, ge=1, le=100),
    range_preset: str = Query("30d"),
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    db: Session = Depends(get_db)
):
    """
    Get identified statistical anomalies and severe FRP excursions.
    """
    s_dt, e_dt = AnalyticsService.resolve_date_range(range_preset, start_date, end_date)
    return AnomalyAnalyticsService.detect_anomalies(db, limit=limit, start_date=s_dt, end_date=e_dt)
