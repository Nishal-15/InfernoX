from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from app.schemas.reporting import ReportProvenance


class ReportProvenanceBuilder:
    @staticmethod
    def get_provenance(sources: Optional[List[str]] = None) -> ReportProvenance:
        now = datetime.now(timezone.utc).isoformat()
        default_sources = [
            "NASA FIRMS Active Fire (VIIRS NRT / MODIS)",
            "OpenStreetMap Industrial Infrastructure",
            "ESA WorldCover 10m v200 (2021)",
            "Sentinel-2 MSI Level-2A BOA Surface Reflectance"
        ]
        
        return ReportProvenance(
            data_sources=sources or default_sources,
            retrieval_timestamps={
                "nasa_firms": now,
                "osm_overpass": now,
                "worldcover_10m": now,
                "sentinel2_stac": now
            },
            model_version="InfernoX-XGB-v1.0",
            feature_schema_version="v1.1",
            risk_model_version="risk-v1",
            analytics_version="analytics-v1",
            report_generation_timestamp=now
        )
