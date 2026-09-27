import httpx
import logging
from app.core.config import settings

logger = logging.getLogger(__name__)

class FirmsClient:
    def __init__(self):
        self.api_key = settings.FIRMS_MAP_KEY
        self.base_url = settings.FIRMS_API_BASE_URL
        self.source = settings.FIRMS_SOURCE
        self.area = settings.FIRMS_AREA
        self.days = settings.FIRMS_DAYS

    async def fetch_active_fires(self) -> str:
        """
        Fetches active fire data from FIRMS API in CSV format.
        Uses the area endpoint: https://firms.modaps.eosdis.nasa.gov/api/area/csv/[MAP_KEY]/[SOURCE]/[AREA]/[DAY_RANGE]
        """
        if not self.api_key:
            logger.error("FIRMS_MAP_KEY is not configured.")
            raise ValueError("FIRMS_MAP_KEY is missing.")

        url = f"{self.base_url}/area/csv/{self.api_key}/{self.source}/{self.area}/{self.days}"
        
        logger.info(f"Fetching FIRMS data from source: {self.source}, area: {self.area}")
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.get(url)
                response.raise_for_status()
                # If API key is invalid, it sometimes returns HTML or a text error
                if "Invalid MAP_KEY" in response.text:
                    logger.error("Invalid NASA FIRMS API key.")
                    raise ValueError("Invalid NASA FIRMS API key.")
                return response.text
            except httpx.HTTPStatusError as e:
                logger.error(f"HTTP error occurred while fetching FIRMS data: {e}")
                raise
            except httpx.RequestError as e:
                logger.error(f"Network error occurred while fetching FIRMS data: {e}")
                raise
