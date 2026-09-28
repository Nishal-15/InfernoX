from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, DateTime, JSON
from app.db.database import Base


def utc_now():
    return datetime.now(timezone.utc)


class GeneratedReport(Base):
    __tablename__ = "generated_reports"

    id = Column(Integer, primary_key=True, index=True)
    report_id = Column(String(64), unique=True, index=True, nullable=False)
    report_type = Column(String(64), index=True, nullable=False)  # INCIDENT, FACILITY, REGIONAL, EXECUTIVE
    title = Column(String(256), nullable=False)
    target_id = Column(String(64), nullable=True, index=True)  # event_id or facility_id
    parameters_json = Column(JSON, nullable=False, default=dict)
    summary_json = Column(JSON, nullable=False, default=dict)
    provenance_json = Column(JSON, nullable=False, default=dict)
    format = Column(String(16), default="JSON", nullable=False)  # PDF, CSV, GEOJSON, JSON
    organization_id = Column(Integer, nullable=True, index=True)
    created_at = Column(DateTime, default=utc_now, nullable=False, index=True)
    created_by = Column(String(128), default="analyst-default", nullable=False)

