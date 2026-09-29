import httpx
import logging
from typing import List, Dict, Any, Optional, Tuple
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

    async def fetch_active_fires(self, source: Optional[str] = None, max_retries: int = 2) -> str:
        """
        Fetches active fire data from FIRMS API in CSV format for a given satellite source.
        Area endpoint: https://firms.modaps.eosdis.nasa.gov/api/area/csv/[MAP_KEY]/[SOURCE]/[AREA]/[DAY_RANGE]
        Includes retry logic with exponential backoff for transient errors.
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
        
        import asyncio
        async with httpx.AsyncClient(timeout=30.0) as client:
            last_err = None
            for attempt in range(max_retries + 1):
                try:
                    response = await client.get(url)
                    response.raise_for_status()
                    # If API key is invalid, NASA FIRMS returns text like "Invalid MAP_KEY"
                    if "Invalid MAP_KEY" in response.text:
                        logger.error("NASA FIRMS API returned 'Invalid MAP_KEY' error response.")
                        raise ValueError("Invalid NASA FIRMS MAP_KEY provided in server configuration.")
                    return response.text
                except httpx.HTTPStatusError as e:
                    last_err = e
                    status = e.response.status_code
                    if status in (429, 502, 503, 504) and attempt < max_retries:
                        backoff = 2 ** attempt
                        logger.warning(f"Transient HTTP {status} from NASA FIRMS for {active_source}. Retrying in {backoff}s...")
                        await asyncio.sleep(backoff)
                        continue
                    logger.error(f"HTTP {status} occurred while querying NASA FIRMS for {active_source}")
                    raise RuntimeError(f"NASA FIRMS API returned HTTP status {status}") from None
                except httpx.RequestError as e:
                    last_err = e
                    if attempt < max_retries:
                        backoff = 2 ** attempt
                        logger.warning(f"Network error from NASA FIRMS: {type(e).__name__}. Retrying in {backoff}s...")
                        await asyncio.sleep(backoff)
                        continue
                    logger.error(f"Network error querying NASA FIRMS provider: {type(e).__name__}")
                    raise RuntimeError("Network error connecting to NASA FIRMS provider.") from None

            raise RuntimeError(f"Failed to fetch NASA FIRMS data after {max_retries + 1} attempts: {last_err}")

    async def fetch_with_fallback(self, preferred_source: Optional[str] = None) -> Tuple[str, str, str]:
        """
        Attempts to fetch from prioritized satellite sources with graceful fallback.
        Priority: Preferred -> VIIRS_SNPP_NRT -> VIIRS_NOAA20_NRT -> VIIRS_NOAA21_NRT -> MODIS_NRT.
        Returns:
            Tuple of (csv_content, active_source_name, provenance_status)
            where provenance_status is "LIVE" or "FALLBACK_SENSOR".
        """
        fallback_order = [
            preferred_source or self.default_source,
            "VIIRS_SNPP_NRT",
            "VIIRS_NOAA20_NRT",
            "VIIRS_NOAA21_NRT",
            "MODIS_NRT"
        ]
        # Deduplicate while preserving order
        seen = set()
        candidates = [s for s in fallback_order if s and not (s in seen or seen.add(s))]

        errors = []
        for i, source_candidate in enumerate(candidates):
            try:
                csv_data = await self.fetch_active_fires(source_candidate, max_retries=1)
                provenance = "LIVE" if i == 0 else "FALLBACK_SENSOR"
                if i > 0:
                    logger.warning(f"Primary sensor failed; successfully fell back to {source_candidate} ({provenance})")
                return csv_data, source_candidate, provenance
            except Exception as e:
                errors.append(f"{source_candidate}: {str(e)}")
                logger.info(f"Sensor source {source_candidate} failed: {e}. Trying next available sensor...")

        raise RuntimeError(f"All sensor fallback sources failed: {'; '.join(errors)}")

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

