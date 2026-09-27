from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.api.deps import get_db
from app.services.firms.ingestion import FirmsIngestionService
from app.services.osm.ingestion import OsmIngestionService
from app.models.ingestion_job import IngestionJob

router = APIRouter()

# Global fallback cache for dev when DB is unreachable
ingestion_status_cache = {
    "last_attempt": None,
    "last_successful_ingestion": None,
    "records_fetched": 0,
    "records_inserted": 0,
    "records_rejected": 0,
    "error_state": None,
    "status": "idle"
}

@router.post("/firms/ingest")
async def ingest_firms_data(db: Session = Depends(get_db)):
    """
    Triggers FIRMS ingestion.
    """
    service = FirmsIngestionService()
    result = await service.ingest_data(db)
    
    # Update cache
    ingestion_status_cache["last_attempt"] = result.get("timestamp")
    if result["status"] == "COMPLETED":
        ingestion_status_cache["last_successful_ingestion"] = result.get("timestamp")
        ingestion_status_cache["records_fetched"] = result.get("fetched", 0)
        ingestion_status_cache["records_inserted"] = result.get("inserted", 0)
        ingestion_status_cache["records_rejected"] = result.get("rejected", 0)
        ingestion_status_cache["error_state"] = None
        ingestion_status_cache["status"] = "connected"
    else:
        ingestion_status_cache["error_state"] = result.get("error")
        ingestion_status_cache["status"] = "connection error"
        
    return result

@router.get("/firms/status")
def get_firms_status(db: Session = Depends(get_db)):
    """
    Returns the persistent status of FIRMS ingestion from PostgreSQL.
    """
    try:
        latest = (
            db.query(IngestionJob)
            .filter(IngestionJob.source.in_(["NASA_FIRMS", "DEMO_NASA_FIRMS"]))
            .order_by(IngestionJob.started_at.desc())
            .first()
        )
        if latest:
            last_success = (
                db.query(IngestionJob)
                .filter(IngestionJob.source.in_(["NASA_FIRMS", "DEMO_NASA_FIRMS"]))
                .filter(IngestionJob.status == "COMPLETED")
                .order_by(IngestionJob.completed_at.desc())
                .first()
            )
            return {
                "status": "connected" if latest.status == "COMPLETED" else latest.status.lower(),
                "last_attempt": latest.started_at.isoformat() if latest.started_at else None,
                "last_successful_ingestion": last_success.completed_at.isoformat() if last_success and last_success.completed_at else None,
                "records_fetched": latest.records_received,
                "records_inserted": latest.records_inserted,
                "records_rejected": latest.records_failed,
                "error_state": latest.error_message,
                "job_id": latest.id,
                "data_source": latest.source
            }
    except Exception:
        pass
    return ingestion_status_cache

@router.post("/osm/ingest")
async def ingest_osm_data(db: Session = Depends(get_db)):
    """
    Triggers OSM industrial facilities ingestion.
    """
    service = OsmIngestionService()
    result = await service.ingest_facilities(db)
    return result
