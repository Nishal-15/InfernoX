from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Float, DateTime, Text, JSON, ForeignKey
from geoalchemy2 import Geometry
from app.db.database import Base

def utc_now():
    return datetime.now(timezone.utc)

class ThermalIncident(Base):
    """
    Thermal Incident grouping correlated thermal observations over space and time.
    Prevents alert storms by aggregating detections within spatial proximity (1.5km)
    and temporal lookback window (48h) or facility match into a single incident.
    """
    __tablename__ = "thermal_incidents"

    id = Column(Integer, primary_key=True, index=True)
    incident_code = Column(String(64), unique=True, nullable=False, index=True)  # e.g. INC-2026-000124
    title = Column(String(256), nullable=False)
    status = Column(String(32), default="ACTIVE", nullable=False, index=True)  # ACTIVE, CONTAINED, RESOLVED, MONITORING
    severity = Column(String(32), default="MODERATE", nullable=False, index=True)  # CRITICAL, HIGH, MODERATE, LOW
    classification = Column(String(128), default="UNKNOWN", nullable=False, index=True)
    
    first_detected_at = Column(DateTime, nullable=False, index=True)
    last_detected_at = Column(DateTime, nullable=False, index=True)
    duration_hours = Column(Float, default=0.0, nullable=False)
    
    event_count = Column(Integer, default=1, nullable=False)
    peak_frp = Column(Float, default=0.0, nullable=False)
    mean_frp = Column(Float, default=0.0, nullable=False)
    risk_score = Column(Float, default=0.0, nullable=False)
    risk_level = Column(String(32), default="LOW", nullable=False)
    
    primary_facility_id = Column(Integer, ForeignKey("facilities.id", ondelete="SET NULL"), nullable=True, index=True)
    primary_facility_name = Column(String(256), nullable=True)
    distance_to_facility_meters = Column(Float, nullable=True)
    
    centroid_latitude = Column(Float, nullable=False)
    centroid_longitude = Column(Float, nullable=False)
    geometry = Column(Geometry(geometry_type='POINT', srid=4326, spatial_index=True), nullable=True)
    
    incident_summary_json = Column(JSON, nullable=False, default=dict)
    
    created_at = Column(DateTime, default=utc_now, nullable=False)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now, nullable=False)


class IncidentEvent(Base):
    """
    Associates individual ThermalEvent detections with a correlated ThermalIncident.
    Preserves raw observation immutability while maintaining relational grouping.
    """
    __tablename__ = "incident_events"

    id = Column(Integer, primary_key=True, index=True)
    incident_id = Column(Integer, ForeignKey("thermal_incidents.id", ondelete="CASCADE"), nullable=False, index=True)
    event_id = Column(Integer, ForeignKey("thermal_events.id", ondelete="CASCADE"), nullable=False, index=True)
    created_at = Column(DateTime, default=utc_now, nullable=False)

