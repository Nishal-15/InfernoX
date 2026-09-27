import logging
from sqlalchemy.orm import Session
from sqlalchemy.dialects.postgresql import insert
from datetime import datetime, timezone
from app.services.osm.client import OsmClient
from app.services.osm.normalizer import OsmNormalizer
from app.models.facility import Facility

logger = logging.getLogger(__name__)

class OsmIngestionService:
    def __init__(self):
        self.client = OsmClient()
        self.normalizer = OsmNormalizer()

    async def ingest_facilities(self, db: Session) -> dict:
        result = {
            "status": "started",
            "fetched": 0,
            "inserted": 0,
            "skipped": 0,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        try:
            data = await self.client.fetch_industrial_facilities()
            elements = data.get('elements', [])
            result["fetched"] = len(elements)

            for element in elements:
                normalized = self.normalizer.normalize(element)
                if not normalized:
                    continue
                
                # PostgreSQL ON CONFLICT DO NOTHING for deduplication
                stmt = insert(Facility).values(
                    osm_id=normalized.osm_id,
                    name=normalized.name,
                    facility_type=normalized.facility_type,
                    latitude=normalized.latitude,
                    longitude=normalized.longitude,
                    geometry=f"SRID=4326;POINT({normalized.longitude} {normalized.latitude})",
                    operator=normalized.operator,
                    tags=normalized.tags,
                    source=normalized.source
                )
                
                # If facility already exists, we could UPDATE it. For phase 3, DO NOTHING is fine.
                stmt = stmt.on_conflict_do_nothing(
                    index_elements=['osm_id']
                )
                
                exec_result = db.execute(stmt)
                if exec_result.rowcount > 0:
                    result["inserted"] += 1
                else:
                    result["skipped"] += 1
            
            db.commit()
            result["status"] = "completed"
            
        except Exception as e:
            db.rollback()
            logger.error(f"OSM Ingestion failed: {e}")
            result["status"] = "failed"
            result["error"] = str(e)
            
        return result
