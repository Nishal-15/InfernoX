import pytest # type: ignore
from app.services.osm.normalizer import OsmNormalizer

def test_osm_normalizer_oil_refinery():
    normalizer = OsmNormalizer()
    element = {
        "type": "way",
        "id": 12345,
        "center": {"lat": 22.0, "lon": 70.0},
        "tags": {
            "name": "Reliance Jamnagar Refinery",
            "industrial": "oil_refinery",
            "operator": "Reliance Industries"
        }
    }
    facility = normalizer.normalize(element)
    
    assert facility is not None
    assert facility.osm_id == "way/12345"
    assert facility.facility_type == "Oil Refinery"
    assert facility.name == "Reliance Jamnagar Refinery"
    assert facility.operator == "Reliance Industries"
    assert facility.latitude == 22.0
    assert facility.longitude == 70.0

def test_osm_normalizer_missing_name():
    normalizer = OsmNormalizer()
    element = {
        "type": "node",
        "id": 67890,
        "lat": 19.0,
        "lon": 72.8,
        "tags": {
            "power": "plant"
        }
    }
    facility = normalizer.normalize(element)
    
    assert facility is not None
    assert facility.facility_type == "Power Plant"
    assert facility.name == "Unnamed industrial facility"

def test_osm_normalizer_missing_coordinates():
    normalizer = OsmNormalizer()
    element = {
        "type": "relation",
        "id": 11111,
        "tags": {
            "industrial": "petrochemical"
        }
    }
    # Should return None because coordinates are missing
    facility = normalizer.normalize(element)
    assert facility is None
