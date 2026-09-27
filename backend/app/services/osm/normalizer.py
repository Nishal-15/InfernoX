from typing import Dict, Any, Optional
from app.schemas.facility import FacilityCreate
import logging

logger = logging.getLogger(__name__)

class OsmNormalizer:
    def _determine_facility_type(self, tags: dict) -> str:
        # Priority mapping based on OSM tags
        if tags.get('industrial') == 'oil_refinery' or tags.get('refinery') == 'oil':
            return 'Oil Refinery'
        if tags.get('industrial') == 'petrochemical':
            return 'Petrochemical Facility'
        if tags.get('industrial') == 'chemical' or tags.get('man_made') == 'works' and tags.get('product') == 'chemical':
            return 'Chemical Plant'
        if tags.get('power') == 'plant':
            return 'Power Plant'
        if tags.get('industrial') == 'steel' or tags.get('industrial') == 'metal':
            return 'Steel/Metal Facility'
        if tags.get('landuse') == 'quarry' or tags.get('industrial') == 'mine':
            return 'Mining Area'
        if tags.get('industrial') == 'gas' or tags.get('industrial') == 'lng':
            return 'LNG/Gas Facility'
        if tags.get('industrial') == 'depot' or tags.get('industrial') == 'storage':
            return 'Storage/Depot'
            
        # Fallbacks
        if 'man_made' in tags and tags['man_made'] == 'works':
            return 'Industrial Plant'
        if tags.get('landuse') == 'industrial':
            return 'Industrial Area'
            
        return 'Industrial Facility'

    def normalize(self, element: Dict[str, Any]) -> Optional[FacilityCreate]:
        try:
            osm_type = element.get('type')
            osm_id = str(element.get('id'))
            unique_id = f"{osm_type}/{osm_id}"
            
            tags = element.get('tags', {})
            
            # Name extraction
            name = tags.get('name')
            if not name:
                name = "Unnamed industrial facility"
                
            # Coordinates
            # If it's a node, lat/lon are direct. If way/relation with 'out center', they are in 'center' object.
            lat = element.get('lat')
            lon = element.get('lon')
            if lat is None or lon is None:
                center = element.get('center', {})
                lat = center.get('lat')
                lon = center.get('lon')
                
            if lat is None or lon is None:
                return None
                
            facility_type = self._determine_facility_type(tags)
            
            return FacilityCreate(
                osm_id=unique_id,
                name=name,
                facility_type=facility_type,
                latitude=float(lat),
                longitude=float(lon),
                operator=tags.get('operator'),
                tags=tags,
                source="OpenStreetMap"
            )
        except Exception as e:
            logger.warning(f"Error normalizing OSM element {element.get('id')}: {e}")
            return None
