from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List, Dict, Any
from datetime import datetime

class ThermalIncidentBase(BaseModel):
    incident_code: str
    title: str
    status: str = "ACTIVE"
    severity: str = "MODERATE"
    classification: str = "UNKNOWN"
    first_detected_at: datetime
    last_detected_at: datetime
    duration_hours: float = 0.0
    event_count: int = 1
    peak_frp: float = 0.0
    mean_frp: float = 0.0
    risk_score: float = 0.0
    risk_level: str = "LOW"
    primary_facility_id: Optional[int] = None
    primary_facility_name: Optional[str] = None
    distance_to_facility_meters: Optional[float] = None
    centroid_latitude: float
    centroid_longitude: float
    incident_summary_json: Dict[str, Any] = Field(default_factory=dict)

class ThermalIncidentResponse(ThermalIncidentBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
    updated_at: datetime

class ThermalIncidentList(BaseModel):
    items: List[ThermalIncidentResponse]
    total: int
    active_count: int
    critical_count: int

class IncidentStatusUpdate(BaseModel):
    status: str = Field(..., description="ACTIVE, CONTAINED, RESOLVED, MONITORING")
    analyst_notes: Optional[str] = None
