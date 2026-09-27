import pytest
from datetime import datetime, timezone
from app.schemas.features import ThermalFeatures
from app.services.priority.engine import PriorityEngine

def make_features(**kwargs):
    defaults = {
        "event_id": 1,
        "latitude": 20.0,
        "longitude": 75.0,
        "detected_at": datetime.now(timezone.utc),
        "satellite": "VIIRS",
        "frp": 40.0,
        "temporal_status": "NEW",
        "distance_to_industrial_facility": None,
        "frp_deviation_ratio": 1.0
    }
    defaults.update(kwargs)
    return ThermalFeatures(**defaults)

def test_priority_critical_industrial_fire():
    features = make_features(
        temporal_status="ABNORMAL",
        frp=600.0,
        frp_deviation_ratio=4.5,
        distance_to_industrial_facility=150.0
    )
    score, level = PriorityEngine.evaluate_priority(features, "INDUSTRIAL_FIRE")
    assert level == "CRITICAL"
    assert score >= PriorityEngine.CRITICAL_THRESHOLD

def test_priority_low_gas_flare():
    features = make_features(
        temporal_status="PERSISTENT",
        frp=40.0,
        distance_to_industrial_facility=200.0,
        frp_deviation_ratio=1.0
    )
    score, level = PriorityEngine.evaluate_priority(features, "GAS_FLARE")
    assert level == "LOW"
    assert score < PriorityEngine.MEDIUM_THRESHOLD

def test_priority_high_moderate_anomaly():
    features = make_features(
        temporal_status="ABNORMAL",
        frp=250.0,
        frp_deviation_ratio=2.6,
        distance_to_industrial_facility=800.0
    )
    score, level = PriorityEngine.evaluate_priority(features, "OTHER_THERMAL_ANOMALY")
    assert level in ["HIGH", "CRITICAL"]
