import httpx
import logging
from typing import List, Dict, Any, Optional
from app.core.config import settings

logger = logging.getLogger(__name__)

class FirmsClient:
    """
    Official NASA FIRMS programmatic API client.
    Domain: https://firms.modaps.eosdis.nasa.gov/api/
    Supports multi-satellite source ingestion (VIIRS SNPP, NOAA-20, NOAA-21, MODIS).
    Never logs or exposes the secret FIRMS_MAP_KEY.
    """
    def __init__(self):
        self.api_key = settings.FIRMS_MAP_KEY
        # Ensure official operational domain is used
        raw_base = getattr(settings, "FIRMS_BASE_URL", None) or settings.FIRMS_API_BASE_URL
        if "firms.modap." in raw_base:
            # Correct any accidental typo to official NASA domain
            raw_base = raw_base.replace("firms.modap.", "firms.modaps.")
        self.base_url = raw_base.rstrip("/")
        self.default_source = settings.FIRMS_SOURCE
        self.area = settings.FIRMS_AREA
        self.days = settings.FIRMS_DAYS
        self.sources_registry = getattr(settings, "FIRMS_SOURCES_REGISTRY", [])

    def get_enabled_sources(self) -> List[Dict[str, Any]]:
        """Returns all currently enabled satellite sources from registry, sorted by priority."""
        if not self.sources_registry:
            return [{
                "source_name": self.default_source,
                "enabled": True,
                "priority": 1,
                "refresh_interval_minutes": 15,
                "satellite": "Suomi NPP",
                "instrument": "VIIRS"
            }]
        enabled = [s for s in self.sources_registry if s.get("enabled", True)]
        return sorted(enabled, key=lambda x: x.get("priority", 99))

    async def fetch_active_fires(self, source: Optional[str] = None) -> str:
        """
        Fetches active fire data from FIRMS API in CSV format for a given satellite source.
        Area endpoint: https://firms.modaps.eosdis.nasa.gov/api/area/csv/[MAP_KEY]/[SOURCE]/[AREA]/[DAY_RANGE]
        Never exposes the MAP_KEY in logs.
        """
        if not self.api_key:
            logger.error("FIRMS_MAP_KEY is not configured.")
            raise ValueError("FIRMS_MAP_KEY is missing from server configuration.")

        active_source = source or self.default_source
        url = f"{self.base_url}/area/csv/{self.api_key}/{active_source}/{self.area}/{self.days}"
        
        # Masked URL for safe audit logging
        masked_url = f"{self.base_url}/area/csv/***REDACTED***/{active_source}/{self.area}/{self.days}"
        logger.info(f"Fetching FIRMS data from source: {active_source}, area: {self.area} [Endpoint: {masked_url}]")
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.get(url)
                response.raise_for_status()
                # If API key is invalid, NASA FIRMS returns text like "Invalid MAP_KEY"
                if "Invalid MAP_KEY" in response.text:
                    logger.error("NASA FIRMS API returned 'Invalid MAP_KEY' error response.")
                    raise ValueError("Invalid NASA FIRMS MAP_KEY provided in server configuration.")
                return response.text
            except httpx.HTTPStatusError as e:
                # Log without exposing URL with key
                logger.error(f"HTTP {e.response.status_code} occurred while querying NASA FIRMS for {active_source}")
                raise RuntimeError(f"NASA FIRMS API returned HTTP status {e.response.status_code}") from None
            except httpx.RequestError as e:
                logger.error(f"Network error querying NASA FIRMS provider: {type(e).__name__}")
                raise RuntimeError("Network error connecting to NASA FIRMS provider.") from None

    async def fetch_all_enabled_sources(self) -> Dict[str, str]:
        """Fetches fire data across all prioritized satellite sources."""
        results: Dict[str, str] = {}
        for src_info in self.get_enabled_sources():
            src_name = src_info["source_name"]
            try:
                csv_text = await self.fetch_active_fires(src_name)
                results[src_name] = csv_text
            except Exception as e:
                logger.warning(f"Failed to fetch satellite source {src_name}: {e}")
        return results
