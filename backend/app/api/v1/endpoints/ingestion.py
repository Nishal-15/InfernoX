from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from app.api.deps import get_db
from app.models.ingestion_job import IngestionJob
from app.schemas.ingestion import IngestionJobOut, IngestionStatusSummary
from app.services.firms.ingestion import FirmsIngestionService
from app.services.osm.ingestion import OsmIngestionService

router = APIRouter()

@router.get("/status", response_model=IngestionStatusSummary)
def get_ingestion_status(db: Session = Depends(get_db)):
    """
    Returns persistent ingestion health and status summary from the database.
    Survives application restarts.
    """
    latest_job = (
        db.query(IngestionJob)
        .order_by(IngestionJob.started_at.desc())
        .first()
    )
    
    last_success = (
        db.query(IngestionJob)
        .filter(IngestionJob.status == "COMPLETED")
        .order_by(IngestionJob.completed_at.desc())
        .first()
    )
    
    status_str = "idle"
    error_state = None
    records_fetched = 0
    records_inserted = 0
    records_rejected = 0

    if latest_job:
        status_str = latest_job.status.lower()
        error_state = latest_job.error_message
        records_fetched = latest_job.records_received
        records_inserted = latest_job.records_inserted
        records_rejected = latest_job.records_failed

    return IngestionStatusSummary(
        status=status_str,
        last_attempt=latest_job.started_at if latest_job else None,
        last_successful_ingestion=last_success.completed_at if last_success else None,
        records_fetched=records_fetched,
        records_inserted=records_inserted,
        records_rejected=records_rejected,
        error_state=error_state,
        latest_job=latest_job
    )

@router.get("/jobs", response_model=List[IngestionJobOut])
def get_ingestion_jobs(
    db: Session = Depends(get_db),
    source: Optional[str] = None,
    limit: int = Query(50, le=200),
    offset: int = 0
):
    """
    Retrieves historical ingestion execution jobs.
    """
    query = db.query(IngestionJob)
    if source:
        query = query.filter(IngestionJob.source == source)
    return query.order_by(IngestionJob.started_at.desc()).offset(offset).limit(limit).all()

@router.post("/firms")
async def trigger_firms_ingestion(
    db: Session = Depends(get_db),
    use_demo_data: bool = Query(False, description="Run with verified demo data if real FIRMS key is absent")
):
    """
    Triggers a NASA FIRMS ingestion run and records persistent job status.
    """
    service = FirmsIngestionService()
    return await service.ingest_data(db, use_demo_if_missing_key=use_demo_data)

@router.post("/osm")
async def trigger_osm_ingestion(db: Session = Depends(get_db)):
    """
    Triggers an OSM Overpass ingestion run for industrial infrastructure.
    """
    service = OsmIngestionService()
    return await service.ingest_facilities(db)
