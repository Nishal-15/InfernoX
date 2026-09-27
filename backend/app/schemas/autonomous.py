from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List, Dict, Any
from datetime import datetime

class PipelineStageRunResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    stage_name: str
    status: str
    is_transient_error: bool = False
    error_message: Optional[str] = None
    retry_count: int = 0
    duration_seconds: float = 0.0
    stage_output_json: Dict[str, Any] = Field(default_factory=dict)
    started_at: datetime
    completed_at: Optional[datetime] = None

class PipelineJobResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    correlation_id: str
    job_type: str
    source: str
    status: str
    records_received: int = 0
    records_inserted: int = 0
    records_skipped: int = 0
    records_processed: int = 0
    records_succeeded: int = 0
    records_failed: int = 0
    retry_count: int = 0
    max_retries: int = 3
    error_message: Optional[str] = None
    started_at: datetime
    completed_at: Optional[datetime] = None
    duration_seconds: float = 0.0
    metadata_json: Dict[str, Any] = Field(default_factory=dict)
    stages: Optional[List[PipelineStageRunResponse]] = None

class PipelineJobListResponse(BaseModel):
    items: List[PipelineJobResponse]
    total: int

class ProviderHealthInfo(BaseModel):
    provider: str
    status: str  # HEALTHY, DEGRADED, UNAVAILABLE, UNKNOWN
    latency_ms: float = 0.0
    last_successful_request: Optional[str] = None
    last_failure: Optional[str] = None
    failure_count: int = 0
    message: Optional[str] = None
    details: Dict[str, Any] = Field(default_factory=dict)

class SystemHealthResponse(BaseModel):
    system_status: str  # OPERATIONAL, DEGRADED, CRITICAL
    timestamp: str
    uptime_seconds: float
    database: Dict[str, Any]
    postgis_available: bool
    scheduler_active: bool
    active_model_version: str
    providers: List[ProviderHealthInfo]
    recent_jobs_summary: Dict[str, Any]

class DemoTriggerRequest(BaseModel):
    latitude: float = 22.4630
    longitude: float = 70.0710
    frp: float = 425.0
    brightness_temperature: float = 388.4
    satellite: str = "VIIRS_NPP"
    confidence: float = 95.0
    label: str = "DEMO_EVENT"

class DemoTriggerResponse(BaseModel):
    status: str
    correlation_id: str
    job_id: int
    event_id: int
    classification: str
    risk_score: float
    risk_level: str
    incident_code: Optional[str] = None
    alert_code: Optional[str] = None
    stages_executed: List[str]
    duration_seconds: float
