import logging
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.core.config import settings
from app.models.pipeline import PipelineJob, PipelineStageRun, AutonomousAuditLog
from app.schemas.autonomous import (
    SystemHealthResponse,
    ProviderHealthInfo,
    PipelineJobResponse,
    PipelineJobListResponse,
    PipelineStageRunResponse,
    DemoTriggerRequest,
    DemoTriggerResponse
)
from app.services.system.health_monitor import HealthMonitor
from app.services.autonomous.pipeline_runner import PipelineRunner
from app.services.websocket.manager import ws_manager

logger = logging.getLogger(__name__)
router = APIRouter()

@router.get("/health", response_model=SystemHealthResponse)
async def get_system_health(db: Session = Depends(get_db)):
    """
    Returns comprehensive system health status, DB & PostGIS availability,
    scheduler state, external provider telemetry, and recent job aggregates.
    """
    health = await HealthMonitor.get_system_health(db)
    return health

from typing import List, Optional, Union, Dict, Any

@router.get("/providers")
async def get_provider_health(format: Optional[str] = Query(None, description="Optional 'dict' or 'list'")):
    """
    Probes and returns real-time health metrics, latencies, and statuses
    for all integrated external data providers (NASA FIRMS, STAC, OSM, ML, WorldCover).
    Supports Section 7 dict format ({'firms': {...}}) when format='dict'.
    """
    providers = await HealthMonitor.get_all_providers()
    if format == "dict":
        firms_info = next((p for p in providers if p.get("provider") == "NASA FIRMS"), {})
        return {
            "firms": {
                "status": firms_info.get("status", "unavailable").lower(),
                "last_successful_sync": firms_info.get("last_successful_sync"),
                "last_failure": firms_info.get("last_failure"),
                "records_last_sync": firms_info.get("records_last_sync", 0),
                "active_sources": firms_info.get("active_sources", [])
            }
        }
    return providers

@router.get("/providers/firms")
async def get_firms_provider_status():
    """
    Dedicated Section 7 FIRMS health endpoint.
    Identifies: available, degraded, rate_limited, unavailable.
    Never exposes FIRMS_MAP_KEY.
    """
    firms_info = await HealthMonitor.check_firms_provider()
    return {
        "firms": {
            "status": firms_info.get("status", "unavailable").lower(),
            "last_successful_sync": firms_info.get("last_successful_sync"),
            "last_failure": firms_info.get("last_failure"),
            "records_last_sync": firms_info.get("records_last_sync", 0),
            "active_sources": firms_info.get("active_sources", [])
        }
    }


@router.get("/jobs", response_model=PipelineJobListResponse)
def list_pipeline_jobs(
    status: Optional[str] = None,
    job_type: Optional[str] = None,
    limit: int = Query(25, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db)
):
    """
    Returns paginated persistent pipeline job execution history with duration and records.
    """
    query = db.query(PipelineJob)
    if status:
        query = query.filter(PipelineJob.status == status.upper())
    if job_type:
        query = query.filter(PipelineJob.job_type == job_type)
    
    total = query.count()
    jobs = query.order_by(PipelineJob.started_at.desc()).offset(offset).limit(limit).all()

    return {
        "items": jobs,
        "total": total
    }

@router.get("/jobs/{job_id}", response_model=PipelineJobResponse)
def get_pipeline_job(job_id: int, db: Session = Depends(get_db)):
    """
    Returns detailed pipeline job telemetry including granular stage-level runs.
    """
    job = db.query(PipelineJob).filter(PipelineJob.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail=f"Pipeline job {job_id} not found")
    
    stages = db.query(PipelineStageRun).filter(PipelineStageRun.job_id == job_id).order_by(PipelineStageRun.started_at.asc()).all()
    
    res = PipelineJobResponse.model_validate(job)
    res.stages = [PipelineStageRunResponse.model_validate(s) for s in stages]
    return res

@router.post("/pipeline/run")
async def trigger_pipeline_cycle(use_demo: bool = False, db: Session = Depends(get_db)):
    """
    Manually triggers an autonomous pipeline cycle (incremental ingestion -> multi-modal intelligence).
    """
    res = await PipelineRunner.run_autonomous_cycle(db, use_demo=use_demo)
    return res

@router.post("/demo/trigger", response_model=DemoTriggerResponse)
async def trigger_demo_event(req: DemoTriggerRequest, db: Session = Depends(get_db)):
    """
    Controlled Demo Mode Trigger (Section 40).
    Creates a clearly labeled DEMO observation and flows it through the complete autonomous pipeline
    (Enrichment -> Temporal -> ML -> Risk -> Incident Correlation -> Alert -> WebSocket Broadcast).
    """
    res = await PipelineRunner.run_demo_pipeline(
        db=db,
        latitude=req.latitude,
        longitude=req.longitude,
        frp=req.frp,
        brightness_temperature=req.brightness_temperature,
        satellite=req.satellite,
        confidence=req.confidence
    )
    return res

@router.get("/audit", response_model=List[dict])
def get_autonomous_audit_logs(
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db)
):
    """
    Retrieves the chronological audit trail of all autonomous machine intelligence operations.
    """
    logs = db.query(AutonomousAuditLog).order_by(AutonomousAuditLog.created_at.desc()).limit(limit).all()
    return [
        {
            "id": l.id,
            "correlation_id": l.correlation_id,
            "action": l.action,
            "source": l.source,
            "event_id": l.event_id,
            "incident_id": l.incident_id,
            "previous_value": l.previous_value,
            "new_value": l.new_value,
            "model_version": l.model_version,
            "details": l.details_json,
            "created_at": l.created_at.isoformat() if l.created_at else None
        }
        for l in logs
    ]

@router.get("/ws/events/recent")
def get_recent_stream_events(limit: int = Query(20, ge=1, le=50)):
    """
    Returns recent broadcasted events from the in-memory stream buffer.
    """
    return ws_manager.get_recent_events(limit=limit)
