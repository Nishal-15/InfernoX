import pytest
from datetime import datetime, timezone, timedelta
from app.services.features.engineer import FeatureEngineer

def test_feature_extraction_determinism():
    now = datetime(2026, 9, 23, 10, 0, tzinfo=timezone.utc)
    event_data = {
        "id": 42,
        "latitude": 22.45,
        "longitude": 70.05,
        "detected_at": now,
        "satellite": "VIIRS",
        "frp": 120.0,
        "confidence": 90.0,
        "brightness_temperature": 340.0
    }
    
    spatial_context = {
        "nearest_facility": {
            "name": "Jamnagar Refinery",
            "facility_type": "Oil Refinery",
            "distance_meters": 350.0
        },
        "distance_meters": 350.0,
        "land_cover": {
            "class": "Industrial",
            "source": "Prototype Land Cover"
        }
    }
    
    temporal_data = {
        "temporal_status": "ABNORMAL",
        "metrics": {
            "event_count": 8,
            "active_days": 5,
            "duration_hours": 120.0,
            "mean_frp": 40.0,
            "max_frp": 120.0,
            "frp_std": 15.0,
            "frp_deviation_ratio": 3.0,
            "spatial_spread_meters": 200.0,
            "detection_frequency": 1.6
        }
    }
    
    # Extract twice to confirm strict determinism
    f1 = FeatureEngineer.extract_features(event_data, spatial_context, temporal_data)
    f2 = FeatureEngineer.extract_features(event_data, spatial_context, temporal_data)
    
    assert f1.model_dump() == f2.model_dump()
    assert f1.event_id == 42
    assert f1.frp == 120.0
    assert f1.mean_frp == 40.0
    assert f1.frp_deviation_ratio == 3.0
    assert f1.temporal_status == "ABNORMAL"
    assert f1.distance_to_industrial_facility == 350.0
    assert f1.facility_type == "Oil Refinery"
    assert f1.is_industrial_land is True
    assert f1.abnormality_score > 0.0

def test_feature_extraction_minimal():
    event_data = {
        "id": 1,
        "latitude": 10.0,
        "longitude": 20.0,
        "frp": 15.0
    }
    f = FeatureEngineer.extract_features(event_data)
    assert f.event_id == 1
    assert f.temporal_status == "NEW"
    assert f.detection_count == 1
    assert f.active_days == 1
    assert f.distance_to_industrial_facility is None
    assert f.is_industrial_land is False
