import pytest
from datetime import datetime, timezone, timedelta
from app.services.temporal.analyzer import TemporalAnalyzer

def test_temporal_status_new():
    analyzer = TemporalAnalyzer()
    status = analyzer.determine_status(
        current_frp=25.0,
        cluster_detection_count=1,
        active_days=1,
        mean_frp=25.0
    )
    assert status == "NEW"

def test_temporal_status_recurring():
    analyzer = TemporalAnalyzer(persistence_min_days=5, recurring_min_detections=2)
    status = analyzer.determine_status(
        current_frp=30.0,
        cluster_detection_count=3,
        active_days=2, # < 5
        mean_frp=32.0
    )
    assert status == "RECURRING"

def test_temporal_status_persistent():
    analyzer = TemporalAnalyzer(persistence_min_days=5, recurring_min_detections=2)
    status = analyzer.determine_status(
        current_frp=40.0,
        cluster_detection_count=8,
        active_days=6, # >= 5
        mean_frp=42.0
    )
    assert status == "PERSISTENT"

def test_temporal_status_abnormal():
    analyzer = TemporalAnalyzer(abnormal_frp_multiplier=2.5)
    # Baseline mean is 50.0, current is 150.0 (3.0x > 2.5x)
    status = analyzer.determine_status(
        current_frp=150.0,
        cluster_detection_count=10,
        active_days=7,
        mean_frp=50.0
    )
    assert status == "ABNORMAL"

def test_compute_metrics_cluster():
    analyzer = TemporalAnalyzer()
    now = datetime(2026, 9, 23, 12, 0, tzinfo=timezone.utc)
    
    current_event = {
        "id": 100,
        "detected_at": now,
        "frp": 60.0,
        "confidence": 85.0
    }
    
    cluster_records = [
        {"id": 98, "detected_at": now - timedelta(days=2), "frp": 40.0, "confidence": 80.0, "distance": 120.0},
        {"id": 99, "detected_at": now - timedelta(days=1), "frp": 50.0, "confidence": 82.0, "distance": 150.0},
    ]
    
    res = analyzer.compute_metrics(current_event, cluster_records)
    assert res["status"] == "success"
    metrics = res["metrics"]
    
    assert metrics["event_count"] == 3
    assert metrics["active_days"] == 3
    assert metrics["duration_hours"] == 48.0
    assert metrics["mean_frp"] == 50.0 # (40+50+60)/3
    assert metrics["max_frp"] == 60.0
    assert metrics["frp_std"] == 10.0
    assert metrics["spatial_spread_meters"] == 150.0
    assert len(res["timeline"]) == 3
    assert res["timeline"][-1]["is_current"] is True

def test_compute_metrics_single_detection():
    analyzer = TemporalAnalyzer()
    now = datetime(2026, 9, 23, 12, 0, tzinfo=timezone.utc)
    
    current_event = {
        "id": 1,
        "detected_at": now,
        "frp": 30.0,
        "confidence": 75.0
    }
    
    res = analyzer.compute_metrics(current_event, [])
    assert res["temporal_status"] == "NEW"
    metrics = res["metrics"]
    assert metrics["event_count"] == 1
    assert metrics["active_days"] == 1
    assert metrics["duration_hours"] == 0.0
    assert metrics["mean_frp"] == 30.0
    assert metrics["frp_std"] == 0.0
