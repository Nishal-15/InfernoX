import pytest
from datetime import datetime, timezone
from app.schemas.features import ThermalFeatures
from app.services.classification.classifier import PrototypeClassifier

@pytest.fixture
def classifier():
    return PrototypeClassifier()

def make_features(**kwargs):
    defaults = {
        "event_id": 1,
        "latitude": 20.0,
        "longitude": 75.0,
        "detected_at": datetime.now(timezone.utc),
        "satellite": "VIIRS",
        "frp": 50.0,
        "confidence": 85.0,
        "detection_count": 5,
        "active_days": 3,
        "duration_hours": 48.0,
        "mean_frp": 50.0,
        "max_frp": 50.0,
        "frp_std": 5.0,
        "frp_deviation_ratio": 1.0,
        "spatial_spread_meters": 150.0,
        "detection_frequency": 1.5,
        "temporal_status": "NEW",
        "distance_to_industrial_facility": None,
        "facility_type": None,
        "nearest_facility_name": None,
        "land_cover_class": None,
        "is_industrial_land": False,
        "persistence_score": 0.2,
        "recurrence_score": 0.3,
        "abnormality_score": 0.0
    }
    defaults.update(kwargs)
    return ThermalFeatures(**defaults)

def test_classify_industrial_fire(classifier):
    features = make_features(
        temporal_status="ABNORMAL",
        frp=350.0,
        mean_frp=80.0,
        frp_deviation_ratio=4.3,
        distance_to_industrial_facility=200.0,
        facility_type="Chemical Plant",
        is_industrial_land=True
    )
    res = classifier.classify(features)
    assert res["classification"] == PrototypeClassifier.CLASS_INDUSTRIAL_FIRE
    assert res["confidence_type"] == "heuristic"
    assert res["model_type"] == "rule_based_prototype"
    assert any("ABNORMAL" in e for e in res["evidence_factors"])
    assert any("Chemical Plant" in e for e in res["evidence_factors"])

def test_classify_gas_flare(classifier):
    features = make_features(
        temporal_status="PERSISTENT",
        active_days=10,
        spatial_spread_meters=180.0,
        distance_to_industrial_facility=150.0,
        facility_type="Oil Refinery",
        nearest_facility_name="Coastal Refinery",
        is_industrial_land=True
    )
    res = classifier.classify(features)
    assert res["classification"] == PrototypeClassifier.CLASS_GAS_FLARE
    assert any("flare" in e.lower() for e in res["evidence_factors"])

def test_classify_persistent_source(classifier):
    features = make_features(
        temporal_status="PERSISTENT",
        active_days=14,
        distance_to_industrial_facility=600.0,
        facility_type="Power Plant",
        is_industrial_land=True
    )
    res = classifier.classify(features)
    assert res["classification"] == PrototypeClassifier.CLASS_PERSISTENT_SOURCE

def test_classify_agricultural_burning(classifier):
    features = make_features(
        temporal_status="RECURRING",
        land_cover_class="Cropland / Agriculture",
        distance_to_industrial_facility=15000.0, # far from industry
        frp=35.0
    )
    res = classifier.classify(features)
    assert res["classification"] == PrototypeClassifier.CLASS_AGRICULTURAL_BURNING

def test_classify_wildfire(classifier):
    features = make_features(
        temporal_status="NEW",
        land_cover_class="Forest / Woodland",
        distance_to_industrial_facility=25000.0,
        frp=250.0,
        spatial_spread_meters=1200.0
    )
    res = classifier.classify(features)
    assert res["classification"] == PrototypeClassifier.CLASS_WILDFIRE

def test_classify_mining_activity(classifier):
    features = make_features(
        temporal_status="RECURRING",
        distance_to_industrial_facility=250.0,
        facility_type="Quarry / Mine",
        frp=40.0
    )
    res = classifier.classify(features)
    assert res["classification"] == PrototypeClassifier.CLASS_MINING_ACTIVITY

def test_classify_unknown(classifier):
    features = make_features(
        detection_count=1,
        active_days=1,
        confidence=30.0, # low confidence single point
        temporal_status="NEW",
        frp=15.0
    )
    res = classifier.classify(features)
    assert res["classification"] == PrototypeClassifier.CLASS_UNKNOWN
