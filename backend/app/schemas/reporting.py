from typing import Dict, Any, List, Optional
from datetime import datetime
from pydantic import BaseModel, Field


class ReportGenerateRequest(BaseModel):
    report_type: str = Field(..., description="INCIDENT, FACILITY, REGIONAL, EXECUTIVE")
    target_id: Optional[str] = Field(None, description="Event ID, Facility ID, or Region identifier")
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    title: Optional[str] = None
    sections: Optional[List[str]] = Field(default_factory=lambda: [
        "summary",
        "thermal_evidence",
        "industrial_context",
        "satellite_evidence",
        "ai_assessment",
        "analyst_review",
        "alert_history",
        "provenance"
    ])
    format: str = Field("JSON", description="PDF, CSV, GEOJSON, JSON")


class ReportMetadata(BaseModel):
    report_id: str
    report_type: str
    title: str
    generated_at: str
    generated_by: str
    target_id: Optional[str] = None
    date_range: Optional[Dict[str, Optional[str]]] = None


class ReportProvenance(BaseModel):
    data_sources: List[str]
    retrieval_timestamps: Dict[str, str]
    model_version: str
    feature_schema_version: str
    risk_model_version: str
    analytics_version: str
    report_generation_timestamp: str


class ReportDataPayload(BaseModel):
    metadata: ReportMetadata
    summary: Dict[str, Any]
    sections: Dict[str, Any]
    provenance: ReportProvenance
    download_urls: Optional[Dict[str, str]] = None


class ReportListItem(BaseModel):
    id: int
    report_id: str
    report_type: str
    title: str
    target_id: Optional[str] = None
    format: str
    created_at: str
    created_by: str
