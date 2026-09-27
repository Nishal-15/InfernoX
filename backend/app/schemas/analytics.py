from datetime import datetime
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field, ConfigDict


class AnalyticsFilterParams(BaseModel):
    range_preset: Optional[str] = Field("30d", description="24h, 7d, 30d, 90d, 6m, 1y, custom")
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    region: Optional[str] = None
    facility_type: Optional[str] = None
    classification: Optional[str] = None
    risk_level: Optional[str] = None
    min_frp: Optional[float] = None
    max_frp: Optional[float] = None


class TrendSummary(BaseModel):
    metric: str
    current: float
    previous: float
    delta_pct: float
    state: str  # STABLE, INCREASING, DECREASING, VOLATILE, EMERGING
    explanation: str


class KPISummary(BaseModel):
    total_events: int
    new_events_count: int
    recurring_events_count: int
    persistent_sources_count: int
    abnormal_events_count: int
    avg_frp: float
    max_frp: float
    total_frp: float
    avg_risk_score: float
    max_risk_score: float
    critical_risk_count: int
    high_risk_count: int
    moderate_risk_count: int
    low_risk_count: int
    total_alerts: int
    active_alerts: int
    escalated_alerts: int
    resolved_alerts: int
    trends: Dict[str, TrendSummary] = Field(default_factory=dict)
    calculated_at: str


class TimeSeriesPoint(BaseModel):
    timestamp: str
    event_count: int
    avg_frp: float
    max_frp: float
    total_frp: float
    critical_count: int
    high_risk_count: int
    alert_count: int


class TimeSeriesResponse(BaseModel):
    interval: str  # hour, day, week, month
    start_date: str
    end_date: str
    points: List[TimeSeriesPoint]
    total_points: int


class ClassificationMetric(BaseModel):
    classification: str
    count: int
    percentage: float
    avg_frp: float
    max_frp: float
    avg_confidence: float
    risk_distribution: Dict[str, int]
    persistent_count: int


class ClassificationAnalyticsResponse(BaseModel):
    items: List[ClassificationMetric]
    total_classified: int


class RiskAnalyticsResponse(BaseModel):
    distribution: Dict[str, int]
    avg_score: float
    max_score: float
    high_critical_ratio: float
    history_recalculations_count: int


class AlertAnalyticsResponse(BaseModel):
    total_alerts: int
    by_severity: Dict[str, int]
    by_status: Dict[str, int]
    escalation_rate: float
    resolution_rate: float
    avg_resolution_time_minutes: float
    avg_acknowledgement_time_minutes: float


class FacilityMetric(BaseModel):
    facility_id: int
    osm_id: str
    name: str
    facility_type: str
    latitude: float
    longitude: float
    operator: Optional[str] = None
    total_nearby_events: int
    avg_frp: float
    max_frp: float
    persistent_sources: int
    high_risk_events: int
    critical_alerts: int
    last_detected_at: Optional[str] = None


class FacilityTimelineNode(BaseModel):
    date: str
    event_count: int
    max_frp: float
    has_high_risk: bool
    status: str
    description: str


class GeospatialCell(BaseModel):
    cell_id: str
    latitude: float
    longitude: float
    bounds: List[float]  # [min_lat, min_lon, max_lat, max_lon]
    event_count: int
    avg_frp: float
    max_frp: float
    persistent_count: int
    high_risk_count: int
    alert_count: int


class GeospatialHeatmapResponse(BaseModel):
    grid_resolution_deg: float
    cell_count: int
    cells: List[GeospatialCell]
    geojson: Dict[str, Any]


class ComparisonTarget(BaseModel):
    label: str
    identifier: str
    metrics: Dict[str, Any]


class ComparisonResponse(BaseModel):
    comparison_type: str  # REGION, FACILITY, TIME_PERIOD
    target_a: ComparisonTarget
    target_b: ComparisonTarget
    delta_metrics: Dict[str, Any]
    analysis_narrative: List[str]


class AnomalyItem(BaseModel):
    event_id: int
    detected_at: str
    latitude: float
    longitude: float
    frp: float
    anomaly_factor: str
    score: float
    description: str
