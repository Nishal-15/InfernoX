import os
import glob
import logging
from typing import Optional, Dict, Any, List
from sqlalchemy.orm import Session
from app.services.firms.client import FirmsClient
from app.services.firms.parser import FirmsParser
from app.services.firms.validator import FirmsValidator
from app.services.firms.normalizer import FirmsNormalizer
from app.models.thermal_event import ThermalEvent
from app.models.ingestion_job import IngestionJob
from app.core.config import settings
from datetime import datetime, timezone
from sqlalchemy.dialects.postgresql import insert

logger = logging.getLogger(__name__)

# Real-time synchronization telemetry cache for provider health inspection (Section 7)
FIRMS_SYNC_STATE: Dict[str, Any] = {
    "status": "AVAILABLE",
    "last_successful_sync": None,
    "last_failure": None,
    "records_last_sync": 0,
    "failure_count": 0,
    "active_sources": ["VIIRS_SNPP_NRT", "VIIRS_NOAA20_NRT", "VIIRS_NOAA21_NRT"]
}

# Sample verified FIRMS CSV data for demo/test mode when no API key is provided
DEMO_FIRMS_CSV = """latitude,longitude,brightness,scan,track,acq_date,acq_time,satellite,instrument,confidence,version,bright_t31,frp,daynight
22.4632,70.0712,345.2,1.1,1.0,2026-09-20,0830,NPP,VIIRS,88,2.0NRT,298.5,145.8,D
22.4635,70.0715,350.1,1.1,1.0,2026-09-21,0825,NPP,VIIRS,92,2.0NRT,299.1,180.2,D
22.4630,70.0710,388.4,1.0,1.0,2026-09-23,0820,NPP,VIIRS,95,2.0NRT,305.4,420.5,D
19.0125,72.8540,320.1,1.2,1.1,2026-09-22,1430,NOAA-20,VIIRS,78,2.0NRT,292.0,38.5,N
19.0128,72.8545,318.5,1.2,1.1,2026-09-23,1415,NOAA-20,VIIRS,80,2.0NRT,291.5,35.0,N
28.6139,77.2090,305.0,1.0,1.0,2026-09-23,0610,Terra,MODIS,65,6.1NRT,289.0,18.2,D
"""

class FirmsIngestionService:
    def __init__(self):
        self.client = FirmsClient()
        self.parser = FirmsParser()
        self.validator = FirmsValidator()
        self.normalizer = FirmsNormalizer()

    async def ingest_data(self, db: Session, use_demo_if_missing_key: bool = False) -> dict:
        """
        Executes a FIRMS data ingestion run and persists the IngestionJob in the database.
        """
        job = IngestionJob(
            source="NASA_FIRMS",
            status="RUNNING",
            started_at=datetime.now(timezone.utc)
        )
        try:
            db.add(job)
            db.commit()
            db.refresh(job)
        except Exception as e:
            logger.warning(f"Could not persist initial IngestionJob: {e}")
            job.id = -1

        result = {
            "job_id": job.id,
            "status": "RUNNING",
            "fetched": 0,
            "inserted": 0,
            "skipped": 0,
            "rejected": 0,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        try:
            csv_data = ""
            if not self.client.api_key:
                if settings.DEMO_MODE or use_demo_if_missing_key:
                    logger.info("FIRMS_MAP_KEY is empty. Using designated DEMO/TEST data provider.")
                    csv_data = DEMO_FIRMS_CSV
                    job.source = "DEMO_NASA_FIRMS"
                else:
                    msg = "FIRMS_MAP_KEY is not configured in .env. Real ingestion cannot proceed."
                    logger.error(msg)
                    result["status"] = "FAILED"
                    result["error"] = msg
                    if job.id != -1:
                        job.status = "FAILED"
                        job.error_message = msg
                        job.completed_at = datetime.now(timezone.utc)
                        db.commit()
                    return result
            else:
                csv_data = await self.client.fetch_active_fires()

            records = self.parser.parse_csv(csv_data)
            result["fetched"] = len(records)
            job.records_received = len(records)

            for record in records:
                is_valid, reason = self.validator.validate(record)
                if not is_valid:
                    logger.debug(f"Record rejected: {reason}")
                    result["rejected"] += 1
                    job.records_failed += 1
                    continue
                
                normalized = self.normalizer.normalize(record)
                if job.source == "DEMO_NASA_FIRMS":
                    normalized.source = "DEMO_NASA_FIRMS"
                
                # PostgreSQL ON CONFLICT DO NOTHING for deduplication
                stmt = insert(ThermalEvent).values(
                    source=normalized.source,
                    latitude=normalized.latitude,
                    longitude=normalized.longitude,
                    geometry=f"SRID=4326;POINT({normalized.longitude} {normalized.latitude})",
                    detected_at=normalized.detected_at,
                    acquired_at=normalized.acquired_at,
                    satellite=normalized.satellite,
                    instrument=normalized.instrument,
                    confidence=normalized.confidence,
                    frp=normalized.frp,
                    brightness_temperature=normalized.brightness_temperature,
                    day_night=normalized.day_night,
                    scan=normalized.scan,
                    track=normalized.track
                )
                stmt = stmt.on_conflict_do_nothing(
                    constraint='_thermal_event_uc'
                )
                
                exec_result = db.execute(stmt)
                if exec_result.rowcount > 0:
                    result["inserted"] += 1
                    job.records_inserted += 1
                else:
                    result["skipped"] += 1
                    job.records_skipped += 1
            
            db.commit()
            status = "COMPLETED" if job.records_failed == 0 else "PARTIAL"
            result["status"] = status
            job.status = status
            job.completed_at = datetime.now(timezone.utc)
            db.commit()

            # Update telemetry cache for health monitor
            FIRMS_SYNC_STATE["status"] = "AVAILABLE"
            FIRMS_SYNC_STATE["last_successful_sync"] = datetime.now(timezone.utc).isoformat()
            FIRMS_SYNC_STATE["records_last_sync"] = result["inserted"]
            FIRMS_SYNC_STATE["failure_count"] = 0
            
        except Exception as e:
            db.rollback()
            logger.error(f"Ingestion failed: {e}")
            result["status"] = "FAILED"
            result["error"] = str(e)

            FIRMS_SYNC_STATE["last_failure"] = datetime.now(timezone.utc).isoformat()
            FIRMS_SYNC_STATE["failure_count"] += 1
            FIRMS_SYNC_STATE["status"] = "RATE_LIMITED" if "429" in str(e) else ("DEGRADED" if FIRMS_SYNC_STATE["failure_count"] < 3 else "UNAVAILABLE")

            if job.id != -1:
                try:
                    job.status = "FAILED"
                    job.error_message = str(e)
                    job.completed_at = datetime.now(timezone.utc)
                    db.commit()
                except Exception as commit_err:
                    logger.error(f"Failed to record failed job status: {commit_err}")
            
        return result

    async def ingest_csv_content(
        self,
        db: Session,
        csv_data: str,
        source_label: str = "HISTORICAL_NASA_FIRMS",
        provenance_notes: Optional[str] = None
    ) -> dict:
        """
        Normalized ingestion for historical and external FIRMS CSV datasets (Section 6).
        Routes directly through Parser -> Validator -> Normalizer -> PostGIS deduplication.
        Preserves all physical observation attributes and data provenance.
        """
        records = self.parser.parse_csv(csv_data)
        result = {
            "source": source_label,
            "fetched": len(records),
            "inserted": 0,
            "skipped": 0,
            "rejected": 0,
            "provenance": {
                "source": source_label,
                "source_url": "https://firms.modaps.eosdis.nasa.gov/",
                "ingested_at": datetime.now(timezone.utc).isoformat(),
                "notes": provenance_notes or "Historical FIRMS Verified Observation Pipeline"
            }
        }

        for record in records:
            is_valid, reason = self.validator.validate(record)
            if not is_valid:
                result["rejected"] += 1
                continue

            normalized = self.normalizer.normalize(record)
            normalized.source = source_label

            stmt = insert(ThermalEvent).values(
                source=normalized.source,
                latitude=normalized.latitude,
                longitude=normalized.longitude,
                geometry=f"SRID=4326;POINT({normalized.longitude} {normalized.latitude})",
                detected_at=normalized.detected_at,
                acquired_at=normalized.acquired_at,
                satellite=normalized.satellite,
                instrument=normalized.instrument,
                confidence=normalized.confidence,
                frp=normalized.frp,
                brightness_temperature=normalized.brightness_temperature,
                day_night=normalized.day_night,
                scan=normalized.scan,
                track=normalized.track
            ).on_conflict_do_nothing(
                constraint='_thermal_event_uc'
            )

            exec_result = db.execute(stmt)
            if exec_result.rowcount > 0:
                result["inserted"] += 1
            else:
                result["skipped"] += 1

        db.commit()
        return result

    def ingest_historical_data(self, db: Session, year: Optional[int] = None) -> dict:
        """
        Discovers and ingests all historical FIRMS CSV files from backend/data/historical/firms/ (Section 6).
        Converges into the exact same PostGIS spatial-temporal intelligence pipeline.
        """
        import asyncio
        base_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data", "historical", "firms")
        if not os.path.exists(base_dir):
            base_dir = os.path.join("data", "historical", "firms")

        pattern = f"{base_dir}/**/*.csv" if not year else f"{base_dir}/{year}/*.csv"
        files = glob.glob(pattern, recursive=True)

        total_inserted = 0
        total_skipped = 0
        total_rejected = 0
        files_processed = []

        for fpath in files:
            try:
                with open(fpath, "r", encoding="utf-8") as f:
                    content = f.read()
                file_year = os.path.basename(os.path.dirname(fpath))
                source_label = f"HISTORICAL_FIRMS_{file_year}"
                loop = asyncio.get_event_loop()
                res = loop.run_until_complete(self.ingest_csv_content(
                    db=db,
                    csv_data=content,
                    source_label=source_label,
                    provenance_notes=f"Loaded from archive file: {os.path.basename(fpath)}"
                )) if loop.is_running() else asyncio.run(self.ingest_csv_content(
                    db=db,
                    csv_data=content,
                    source_label=source_label,
                    provenance_notes=f"Loaded from archive file: {os.path.basename(fpath)}"
                ))
                total_inserted += res["inserted"]
                total_skipped += res["skipped"]
                total_rejected += res["rejected"]
                files_processed.append(os.path.basename(fpath))
            except Exception as e:
                logger.error(f"Error importing historical file {fpath}: {e}")

        return {
            "status": "COMPLETED",
            "files_processed": files_processed,
            "total_inserted": total_inserted,
            "total_skipped": total_skipped,
            "total_rejected": total_rejected
        }

    async def ingest_incremental(self, db: Session, use_demo: bool = False) -> dict:
        """
        Incremental FIRMS ingestion tracking state cursors and avoiding full re-processing.
        Returns newly inserted ThermalEvent IDs for autonomous pipeline consumption.
        """
        from app.models.pipeline import FirmsIngestionState
        source_name = "DEMO_NASA_FIRMS" if (use_demo or not self.client.api_key) else "NASA_FIRMS"

        state = db.query(FirmsIngestionState).filter(FirmsIngestionState.source == source_name).first()
        if not state:
            state = FirmsIngestionState(
                source=source_name,
                bounding_box=settings.FIRMS_AREA,
                total_runs=0,
                total_records_ingested=0,
                last_run_status="RUNNING"
            )
            db.add(state)
            db.commit()
            db.refresh(state)

        result = {
            "source": source_name,
            "fetched": 0,
            "inserted": 0,
            "skipped": 0,
            "rejected": 0,
            "inserted_event_ids": [],
            "cursor": state.last_ingested_timestamp.isoformat() if state.last_ingested_timestamp else None
        }

        try:
            csv_data = ""
            if source_name == "DEMO_NASA_FIRMS":
                csv_data = DEMO_FIRMS_CSV
            else:
                csv_data = await self.client.fetch_active_fires()

            records = self.parser.parse_csv(csv_data)
            result["fetched"] = len(records)

            latest_ts = state.last_ingested_timestamp
            inserted_ids = []

            for record in records:
                is_valid, reason = self.validator.validate(record)
                if not is_valid:
                    result["rejected"] += 1
                    continue

                normalized = self.normalizer.normalize(record)
                normalized.source = source_name

                # Deduplication check: check if event with identical key already exists
                existing = db.query(ThermalEvent).filter(
                    ThermalEvent.source == normalized.source,
                    ThermalEvent.satellite == normalized.satellite,
                    ThermalEvent.detected_at == normalized.detected_at,
                    ThermalEvent.latitude == normalized.latitude,
                    ThermalEvent.longitude == normalized.longitude
                ).first()

                if existing:
                    result["skipped"] += 1
                    continue

                # Insert new event
                new_event = ThermalEvent(
                    source=normalized.source,
                    latitude=normalized.latitude,
                    longitude=normalized.longitude,
                    geometry=f"SRID=4326;POINT({normalized.longitude} {normalized.latitude})",
                    detected_at=normalized.detected_at,
                    acquired_at=normalized.acquired_at,
                    satellite=normalized.satellite,
                    instrument=normalized.instrument,
                    confidence=normalized.confidence,
                    frp=normalized.frp,
                    brightness_temperature=normalized.brightness_temperature,
                    day_night=normalized.day_night,
                    scan=normalized.scan,
                    track=normalized.track,
                    status="NEW"
                )
                db.add(new_event)
                db.commit()
                db.refresh(new_event)

                inserted_ids.append(new_event.id)
                result["inserted"] += 1

                if normalized.detected_at:
                    if latest_ts is None or normalized.detected_at > latest_ts:
                        latest_ts = normalized.detected_at

            state.last_ingested_timestamp = latest_ts
            state.total_runs += 1
            state.total_records_ingested += len(inserted_ids)
            state.last_run_status = "COMPLETED"
            db.commit()

            result["inserted_event_ids"] = inserted_ids
            result["status"] = "COMPLETED"
            return result

        except Exception as e:
            db.rollback()
            state.last_run_status = "FAILED"
            state.last_error = str(e)
            db.commit()
            result["status"] = "FAILED"
            result["error"] = str(e)
            return result

