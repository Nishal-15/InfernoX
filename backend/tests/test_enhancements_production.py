import pytest
from datetime import datetime, timezone, timedelta
from app.services.firms.validator import FirmsValidator
from app.services.firms.client import FirmsClient
from app.services.temporal.analyzer import TemporalAnalyzer
from app.services.landcover.provider import WorldCoverProvider
from app.services.satellite.provider import Sentinel2Provider
from app.services.ml.classifier import MLClassifier
from app.services.risk.engine import RiskEngine
from app.services.websocket.manager import ConnectionManager
from app.schemas.features import ThermalFeatures


def test_firms_validator_with_flags():
    validator = FirmsValidator()

    # 1. Valid record
    valid_record = {
        "latitude": "19.0760",
        "longitude": "72.8777",
        "acq_date": "2026-09-28",
        "acq_time": "1430",
        "satellite": "Suomi NPP",
        "instrument": "VIIRS",
        "frp": "45.5",
        "brightness": "320.0",
        "scan": "1.0",
        "track": "1.0",
        "confidence": "85",
        "daynight": "D"
    }
    is_valid, reasons, flags = validator.validate_with_flags(valid_record)
    assert is_valid is True
    assert len(reasons) == 0
    assert flags["night_observation"] is False

    # 2. Null Island rejection
    null_record = dict(valid_record, latitude="0.0", longitude="0.0")
    is_valid, reasons, flags = validator.validate_with_flags(null_record)
    assert is_valid is False
    assert flags["is_null_island"] is True
    assert any("Null Island" in r for r in reasons)

    # 3. Extreme unphysical FRP
    extreme_frp_record = dict(valid_record, frp="25000.0")
    is_valid, reasons, _ = validator.validate_with_flags(extreme_frp_record)
    assert is_valid is False
    assert any("FRP" in r for r in reasons)

    # 4. Night observation & high brightness flags
    night_hot_record = dict(valid_record, daynight="N", brightness="480.0", frp="1200.0")
    is_valid, reasons, flags = validator.validate_with_flags(night_hot_record)
    assert is_valid is True
    assert flags["night_observation"] is True
    assert flags["high_brightness"] is True
    assert flags["extreme_frp"] is True


def test_temporal_analyzer_robust_stats():
    analyzer = TemporalAnalyzer(radius_meters=1500.0, lookback_days=30)
    current_dt = datetime.now(timezone.utc)

    current_event = {
        "id": 999,
        "frp": 120.0,
        "detected_at": current_dt.isoformat(),
        "confidence": 90,
        "distance": 0.0
    }
    cluster = [
        {"id": 1, "frp": 30.0, "detected_at": (current_dt - timedelta(hours=6)).isoformat(), "confidence": 80, "distance": 150.0},
        {"id": 2, "frp": 35.0, "detected_at": (current_dt - timedelta(hours=12)).isoformat(), "confidence": 82, "distance": 200.0},
        {"id": 3, "frp": 32.0, "detected_at": (current_dt - timedelta(days=2)).isoformat(), "confidence": 85, "distance": 220.0},
    ]

    result = analyzer.compute_metrics(current_event, cluster)
    assert result["status"] == "success"
    metrics = result["metrics"]

    # Verify median and MAD calculation
    assert "median_frp" in metrics
    assert "mad_frp" in metrics
    assert metrics["median_frp"] > 0
    assert metrics["mad_frp"] >= 0

    # Verify FRP acceleration
    assert "frp_acceleration_mw_per_hour" in metrics
    assert metrics["frp_acceleration_mw_per_hour"] > 0  # Spiked from 30 to 120

    # Verify stationary confidence
    assert "stationary_confidence" in metrics
    assert 0.0 <= metrics["stationary_confidence"] <= 1.0


def test_worldcover_cache_and_quantization():
    provider = WorldCoverProvider()

    # Query coordinate 1
    res1 = provider.get_land_cover(19.07601, 72.87771)
    assert res1 is not None
    assert "land_cover_class" in res1
    assert "tile_id" in res1

    # Query coordinate 2 within ~10m (should hit cache key)
    res2 = provider.get_land_cover(19.07604, 72.87774)
    assert res2 is not None
    assert res2["land_cover_class"] == res1["land_cover_class"]


def test_sentinel2_confidence_tiers():
    provider = Sentinel2Provider()
    target_dt = datetime(2026, 9, 20, 10, 0, 0, tzinfo=timezone.utc)

    # Fallback scene generation with acceptable clouds
    res = provider.search_imagery(19.0760, 72.8777, target_dt, max_cloud_cover=30.0)
    assert "satellite_confidence_tier" in res
    assert res["satellite_confidence_tier"] in [
        "SATELLITE_CONFIRMED",
        "SATELLITE_SUPPORTING",
        "SATELLITE_INCONCLUSIVE",
        "SATELLITE_UNAVAILABLE"
    ]


def test_ml_classifier_confidence_tiers_and_entropy():
    classifier = MLClassifier()
    if not classifier.is_operational():
        pytest.skip("ML model artifact not found on local path")

    features = ThermalFeatures(
        event_id=101,
        latitude=22.4632,
        longitude=70.0712,
        detected_at=datetime.now(timezone.utc),
        satellite="VIIRS",
        frp=250.0,
        confidence=95.0,
        brightness_temperature=380.0,
        detection_count=12,
        active_days=8,
        duration_hours=48.0,
        mean_frp=180.0,
        max_frp=300.0,
        frp_std=35.0,
        frp_deviation_ratio=1.38,
        spatial_spread_meters=180.0,
        detection_frequency=1.5,
        temporal_status="PERSISTENT",
        distance_to_industrial_facility=150.0,
        facility_type="Oil Refinery",
        nearest_facility_name="Jamnagar Complex",
        land_cover_class="Built-up",
        land_cover_code=50,
        land_cover_category="INDUSTRIAL/BUILT",
        is_industrial_land=True,
        has_satellite_data=True,
        cloud_coverage=5.0,
        ndvi=0.08,
        nbr=-0.12,
        swir_nir_ratio=1.85,
        burn_scar_detected=True,
        persistence_score=0.92,
        recurrence_score=0.85,
        abnormality_score=0.15
    )

    pred = classifier.classify(features)
    assert "confidence_tier" in pred
    assert pred["confidence_tier"] in ["HIGH_CONFIDENCE", "MEDIUM_CONFIDENCE", "LOW_CONFIDENCE", "UNCERTAIN"]
    assert "prediction_entropy" in pred
    assert 0.0 <= pred["prediction_entropy"] <= 1.0
    assert pred["inference_mode"] == "XGBOOST"
    assert pred["classification"] in classifier.classes


def test_risk_engine_reasons_and_tiers():
    eval_res = RiskEngine.evaluate_risk(
        features={"frp": 160.0, "model_probability": 0.92},
        classification="INDUSTRIAL_FIRE",
        spatial_context={"distance_meters": 120.0, "nearest_facility": {"name": "Refinery", "facility_type": "Oil Refinery"}},
        temporal_data={"status": "ABNORMAL", "frp_spike_ratio": 3.2, "mean_frp": 50.0, "active_days": 6},
        satellite_data={"available": True, "indices": {"burn_scar_indicator": True, "swir_nir_ratio": 1.6}}
    )

    assert eval_res["risk_score"] >= 75.0
    assert eval_res["risk_level"] == "CRITICAL"
    assert "risk_reasons" in eval_res
    reasons = eval_res["risk_reasons"]
    assert "CRITICAL_INDUSTRIAL_PROXIMITY" in reasons
    assert "EXTREME_THERMAL_INTENSITY" in reasons
    assert "ABNORMAL_FRP_SPIKE" in reasons
    assert "SPECTRAL_BURN_SCAR_CONFIRMED" in reasons


@pytest.mark.asyncio
async def test_websocket_envelope_schema():
    mgr = ConnectionManager()
    await mgr.broadcast_heartbeat()
    assert len(mgr.event_buffer) > 0
    latest = mgr.event_buffer[-1]
    assert latest["schema_version"] == "2.0"
    assert latest["event"] == "heartbeat"
    assert latest["payload"]["status"] == "HEALTHY"
