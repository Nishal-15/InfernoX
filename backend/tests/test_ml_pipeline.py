import os
import pytest
from datetime import datetime, timezone
from app.schemas.features import ThermalFeatures
from app.services.ml.dataset import DatasetBuilder
from app.services.ml.trainer import MLTrainer
from app.services.ml.classifier import MLClassifier

def test_data_leakage_prevention():
    records = DatasetBuilder.build_dataset(version="test-v1.0")
    assert len(records) >= 8

    train_recs, test_recs, split_meta = DatasetBuilder.get_dataset_split(records, test_size=0.3, random_state=42)
    assert len(train_recs) > 0
    assert len(test_recs) > 0

    # Ensure no cluster_id in train exists in test (STRICT ANTI-LEAKAGE)
    train_clusters = set(r.cluster_id for r in train_recs if r.cluster_id)
    test_clusters = set(r.cluster_id for r in test_recs if r.cluster_id)
    overlap = train_clusters.intersection(test_clusters)
    assert len(overlap) == 0, f"Data leakage detected! Overlapping clusters: {overlap}"

def test_ml_trainer_and_evaluation():
    trainer = MLTrainer(model_version="xgb-test")
    res = trainer.train_and_evaluate(dataset_version="test-v1.0")
    
    assert res["status"] == "SUCCESS"
    assert res["model_version"] == "xgb-test"
    metrics = res["metrics"]
    assert "accuracy" in metrics
    assert "macro_f1" in metrics
    assert "per_class" in metrics
    assert "confusion_matrix" in metrics
    assert len(res["top_features"]) > 0
    assert os.path.exists(res["artifact_path"])
    assert os.path.exists(res["metadata_path"])

def test_ml_classifier_inference_complete_features():
    clf = MLClassifier(model_version="xgb-test")
    assert clf.is_operational()

    # Complete features with satellite and land cover
    features = ThermalFeatures(
        event_id=101,
        latitude=22.38,
        longitude=69.83,
        detected_at=datetime.now(timezone.utc),
        satellite="VIIRS_SNPP",
        frp=85.0,
        confidence=95.0,
        brightness_temperature=360.0,
        detection_count=35,
        active_days=30,
        duration_hours=750.0,
        mean_frp=80.0,
        max_frp=105.0,
        frp_std=7.5,
        frp_deviation_ratio=1.06,
        spatial_spread_meters=150.0,
        detection_frequency=0.85,
        temporal_status="PERSISTENT",
        distance_to_industrial_facility=180.0,
        facility_type="oil_refinery",
        nearest_facility_name="Jamnagar Refinery",
        land_cover_class="Built-up",
        land_cover_code=50,
        land_cover_category="INDUSTRIAL/BUILT",
        is_industrial_land=True,
        has_satellite_data=True,
        ndvi=0.12,
        nbr=0.45,
        swir_nir_ratio=1.30,
        burn_scar_detected=False
    )

    pred = clf.classify(features)
    assert pred["classification"] in clf.classes
    assert 0.0 <= pred["model_probability"] <= 1.0
    assert pred["confidence_type"] == "model_probability"
    assert pred["model_type"] == "xgboost"
    assert len(pred["top_contributing_features"]) > 0
    assert len(pred["evidence_factors"]) > 0
    assert pred["is_fallback"] is False

def test_ml_classifier_inference_missing_satellite_data():
    clf = MLClassifier(model_version="xgb-test")
    
    # Missing satellite data (has_satellite_data=False, ndvi=None, nbr=None)
    features = ThermalFeatures(
        event_id=102,
        latitude=18.98,
        longitude=72.85,
        detected_at=datetime.now(timezone.utc),
        satellite="VIIRS_SNPP",
        frp=250.0,
        confidence=99.0,
        mean_frp=50.0,
        max_frp=250.0,
        frp_deviation_ratio=5.0,
        temporal_status="ABNORMAL",
        distance_to_industrial_facility=200.0,
        has_satellite_data=False,
        ndvi=None,
        nbr=None,
        swir_nir_ratio=None,
        burn_scar_detected=None
    )

    # Must NOT raise exception despite missing satellite features
    pred = clf.classify(features)
    assert pred["classification"] in clf.classes
    assert pred["model_probability"] is not None

def test_ml_classifier_fallback():
    # Attempt loading nonexistent model with fallback enabled
    clf = MLClassifier(model_version="nonexistent-model-v999", fallback_to_prototype=True)
    assert not clf.is_operational()

    features = ThermalFeatures(
        event_id=103,
        latitude=19.0,
        longitude=72.8,
        detected_at=datetime.now(timezone.utc),
        satellite="VIIRS",
        frp=30.0
    )
    pred = clf.classify(features)
    assert pred["is_fallback"] is True
    assert "Prototype" in pred["classification_source"]
