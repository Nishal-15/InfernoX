import httpx
import logging
from app.core.config import settings

logger = logging.getLogger(__name__)

class OsmClient:
    def __init__(self):
        self.url = settings.OSM_OVERPASS_URL
        self.bbox = settings.OSM_BBOX # Format: min_lon,min_lat,max_lon,max_lat
        
    def _bbox_to_overpass_format(self, bbox: str) -> str:
        # Overpass expects south,west,north,east (min_lat,min_lon,max_lat,max_lon)
        # Assuming our setting is min_lon,min_lat,max_lon,max_lat
        parts = bbox.split(',')
        if len(parts) == 4:
            return f"{parts[1]},{parts[0]},{parts[3]},{parts[2]}"
        return bbox

    async def fetch_industrial_facilities(self) -> dict:
        """
        Fetches industrial facilities using Overpass API.
        """
        overpass_bbox = self._bbox_to_overpass_format(self.bbox)
        
        # Overpass QL to find industrial nodes, ways, relations
        query = f"""
        [out:json][timeout:25];
        (
          node["industrial"]({overpass_bbox});
          way["industrial"]({overpass_bbox});
          relation["industrial"]({overpass_bbox});
          
          node["landuse"="industrial"]({overpass_bbox});
          way["landuse"="industrial"]({overpass_bbox});
          relation["landuse"="industrial"]({overpass_bbox});
          
          node["man_made"="works"]({overpass_bbox});
          way["man_made"="works"]({overpass_bbox});
          relation["man_made"="works"]({overpass_bbox});
          
          node["power"="plant"]({overpass_bbox});
          way["power"="plant"]({overpass_bbox});
          relation["power"="plant"]({overpass_bbox});
        );
        out center;
        """
        
        logger.info(f"Fetching OSM data from Overpass API for bbox {overpass_bbox}")
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                # We use POST because queries can be long
                response = await client.post(self.url, data={'data': query})
                response.raise_for_status()
                return response.json()
            except httpx.HTTPStatusError as e:
                logger.error(f"HTTP error occurred while fetching OSM data: {e}")
                raise
            except httpx.RequestError as e:
                logger.error(f"Network error occurred while fetching OSM data: {e}")
                raise
