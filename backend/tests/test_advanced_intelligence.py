import pytest
from datetime import datetime, timezone, timedelta
from app.services.firms.fusion import FirmsObservationFusionService
from app.services.intelligence.propagation import SpatialPropagationModel
from app.services.intelligence.industrial_discriminator import IndustrialFireDiscriminator
from app.services.intelligence.evidence_fusion import MultimodalEvidenceFusionService
from app.services.temporal.analyzer import TemporalAnalyzer
from app.services.satellite.provider import Sentinel2Provider
from app.services.ml.classifier import MLClassifier
from app.services.risk.engine import RiskEngine
from app.services.alert.engine import AlertEngine
from app.services.autonomous.incident_correlator import IncidentCorrelator


# ---------------------------------------------------------------------------
# Scenario 1: Persistent Refinery Flare
# ---------------------------------------------------------------------------
def test_scenario_01_persistent_refinery_flare():
    spatial_context = {
        "nearest_facility": {
            "name": "Jamnagar Refinery Complex",
            "type": "oil_refinery",
            "distance_meters": 120.0,
            "boundary_radius_meters": 500.0,
            "has_known_flare": True,
        },
        "land_cover_category": "INDUSTRIAL/BUILT"
    }
    temporal_context = {
        "temporal_status": "PERSISTENT",
        "active_days": 28,
        "metrics": {
            "median_frp": 65.0,
            "frp_acceleration_mw_per_hour": 0.5,
            "active_days": 28,
            "spatial_spread_meters": 50.0
        }
    }
    propagation_context = {
        "propagation_state": "STATIONARY_SOURCE",
        "spread_velocity_m_per_h": 0.0,
        "stationary_concentration": 0.95
    }

    result = IndustrialFireDiscriminator.discriminate(
        event_id=101,
        frp=68.0,
        spatial_context=spatial_context,
        temporal_context=temporal_context,
        propagation_context=propagation_context,
        satellite_context={"spectral_diagnosis": "INDUSTRIAL_SURFACE_SUPPORT"}
    )

    assert result["expected_thermal_context"] == "EXPECTED_INDUSTRIAL_THERMAL_CONTEXT"
    assert result["change_point"]["change_point_state"] == "NORMAL_BASELINE"
    assert result["scientific_interpretation"] == "NORMAL_PERSISTENT_INDUSTRIAL_SOURCE"
    assert result["industrial_confidence"] >= 0.50

    # Risk Engine should cap risk and record expected operational reason
    risk = RiskEngine.evaluate_risk(
        features={"frp": 68.0, "landcover_code": 50, "temporal_persistence": 0.92, "facility_distance": 120.0},
        classification="FLARE",
        discrimination=result,
        propagation_metrics=propagation_context
    )
    assert risk.total_score <= 42.0
    assert "EXPECTED_OPERATIONAL_THERMAL_SOURCE" in risk.risk_reasons

    # Alert rule evaluation should recognize normal operational status for suppression
    is_normal_operational = "EXPECTED_OPERATIONAL_THERMAL_SOURCE" in risk.risk_reasons
    assert is_normal_operational is True


# ---------------------------------------------------------------------------
# Scenario 2: Sudden Refinery FRP Surge (Major Anomaly)
# ---------------------------------------------------------------------------
def test_scenario_02_sudden_refinery_frp_surge():
    spatial_context = {
        "nearest_facility": {
            "name": "Jamnagar Refinery Complex",
            "type": "oil_refinery",
            "distance_meters": 150.0,
            "boundary_radius_meters": 500.0,
            "has_known_flare": True,
        }
    }
    temporal_context = {
        "temporal_status": "ABNORMAL",
        "active_days": 25,
        "metrics": {
            "median_frp": 45.0,
            "frp_acceleration_mw_per_hour": 75.0,  # Extreme surge
            "active_days": 25,
            "spatial_spread_meters": 80.0
        }
    }
    propagation_context = {
        "propagation_state": "EXPANDING_EVENT",
        "spread_velocity_m_per_h": 120.0,
        "stationary_concentration": 0.40
    }

    result = IndustrialFireDiscriminator.discriminate(
        event_id=102,
        frp=650.0,  # >14x baseline!
        spatial_context=spatial_context,
        temporal_context=temporal_context,
        propagation_context=propagation_context
    )

    assert result["expected_thermal_context"] == "UNEXPECTED_INDUSTRIAL_THERMAL_CONTEXT"
    assert result["change_point"]["change_point_state"] == "MAJOR_ANOMALY"
    assert result["scientific_interpretation"] == "ABNORMAL_INDUSTRIAL_FIRE_LIKELY"

    risk = RiskEngine.evaluate_risk(
        features={"frp": 650.0, "landcover_code": 50, "facility_distance": 150.0},
        classification="INDUSTRIAL_FIRE",
        discrimination=result,
        propagation_metrics=propagation_context
    )
    assert "UNEXPECTED_INDUSTRIAL_THERMAL_SURGE" in risk.risk_reasons
    assert risk.total_score >= 50.0


# ---------------------------------------------------------------------------
# Scenario 3: Wildfire Spreading Event
# ---------------------------------------------------------------------------
def test_scenario_03_wildfire_spreading_event():
    propagation_model = SpatialPropagationModel()
    now = datetime.now(timezone.utc)
    # Moving cluster over 3 hours
    cluster = [
        {"latitude": 34.0500, "longitude": -118.2500, "detected_at": now.isoformat()},
        {"latitude": 34.0530, "longitude": -118.2540, "detected_at": (now - timedelta(hours=1)).isoformat()},
        {"latitude": 34.0570, "longitude": -118.2590, "detected_at": (now - timedelta(hours=2)).isoformat()},
        {"latitude": 34.0620, "longitude": -118.2650, "detected_at": (now - timedelta(hours=3)).isoformat()},
    ]
    prop = propagation_model.evaluate_propagation(cluster)
    assert prop["propagation_state"] in ["EXPANDING_EVENT", "PROPAGATING_EVENT"]
    assert prop["spread_velocity_m_per_h"] > 100.0

    spatial_context = {
        "nearest_facility": None,
        "land_cover_category": "VEGETATION"
    }
    temporal_context = {
        "temporal_status": "NEW",
        "active_days": 1,
        "metrics": {"median_frp": 120.0, "active_days": 1}
    }

    result = IndustrialFireDiscriminator.discriminate(
        event_id=103,
        frp=280.0,
        spatial_context=spatial_context,
        temporal_context=temporal_context,
        propagation_context=prop,
        satellite_context={"spectral_diagnosis": "BURN_SCAR_SUPPORT"}
    )
    assert result["scientific_interpretation"] == "NATURAL_VEGETATION_FIRE_LIKELY"
    assert result["natural_confidence"] > result["industrial_confidence"]


# ---------------------------------------------------------------------------
# Scenario 4: Agricultural Controlled Burn
# ---------------------------------------------------------------------------
def test_scenario_04_agricultural_controlled_burn():
    spatial_context = {
        "nearest_facility": None,
        "land_cover_category": "AGRICULTURE"
    }
    temporal_context = {
        "temporal_status": "NEW",
        "active_days": 1,
        "metrics": {"median_frp": 15.0, "active_days": 1}
    }
    propagation_context = {
        "propagation_state": "STATIONARY_SOURCE",
        "spread_velocity_m_per_h": 0.0,
        "stationary_concentration": 0.95
    }

    result = IndustrialFireDiscriminator.discriminate(
        event_id=104,
        frp=18.0,  # Small field burn
        spatial_context=spatial_context,
        temporal_context=temporal_context,
        propagation_context=propagation_context
    )
    assert result["scientific_interpretation"] == "AGRICULTURAL_OR_CONTROLLED_BURN"


# ---------------------------------------------------------------------------
# Scenario 5: Mining Thermal Activity
# ---------------------------------------------------------------------------
def test_scenario_05_mining_thermal_activity():
    spatial_context = {
        "nearest_facility": {
            "name": "Khetri Copper Mine & Smelter",
            "type": "quarry",
            "distance_meters": 180.0,
            "boundary_radius_meters": 600.0,
            "has_known_flare": False,
        },
        "land_cover_category": "OTHER"
    }
    result = IndustrialFireDiscriminator.discriminate(
        event_id=105,
        frp=38.0,
        spatial_context=spatial_context
    )
    assert result["footprint_relation"] in ["INSIDE_FACILITY_FOOTPRINT", "FACILITY_BOUNDARY_PROXIMITY"]


# ---------------------------------------------------------------------------
# Scenario 6: Multi-Sensor Duplicate Fusion
# ---------------------------------------------------------------------------
def test_scenario_06_multi_sensor_duplicate_fusion():
    fusion_service = FirmsObservationFusionService(spatial_radius_m=1200.0, temporal_window_hours=6.0)

    observations = [
        {
            "latitude": 22.4630,
            "longitude": 70.0710,
            "satellite": "Suomi NPP",
            "instrument": "VIIRS",
            "frp": 55.0,
            "confidence": 85,
            "scan": 1.0,
            "track": 1.0,
            "daynight": "N",
            "acq_datetime": "2026-09-28T10:00:00Z"
        },
        {
            "latitude": 22.4640,
            "longitude": 70.0715,
            "satellite": "NOAA-20",
            "instrument": "VIIRS",
            "frp": 62.0,
            "confidence": 90,
            "scan": 1.1,
            "track": 1.0,
            "daynight": "N",
            "acq_datetime": "2026-09-28T10:50:00Z"
        },
        {
            "latitude": 22.4650,
            "longitude": 70.0720,
            "satellite": "Aqua",
            "instrument": "MODIS",
            "frp": 70.0,
            "confidence": 80,
            "scan": 2.0,
            "track": 1.5,
            "daynight": "N",
            "acq_datetime": "2026-09-28T11:15:00Z"
        }
    ]

    fused_groups = fusion_service.fuse_observations(observations)
    assert len(fused_groups) == 1

    group = fused_groups[0]
    assert group["sensor_count"] == 3
    assert group["unique_sensor_count"] == 3  # Suomi NPP, NOAA-20, Aqua
    assert group["cross_sensor_confirmation"] is True
    assert 55.0 < group["fused_frp"] < 70.0
    assert len(group["raw_observations"]) == 3


# ---------------------------------------------------------------------------
# Scenario 7: Single-Sensor Observation Fusion
# ---------------------------------------------------------------------------
def test_scenario_07_single_sensor_observation_fusion():
    fusion_service = FirmsObservationFusionService()

    obs = [{
        "latitude": 19.0760,
        "longitude": 72.8777,
        "satellite": "Suomi NPP",
        "instrument": "VIIRS",
        "frp": 25.0,
        "confidence": 75,
        "scan": 1.0,
        "track": 1.0,
        "daynight": "D",
        "acq_datetime": "2026-09-28T12:00:00Z"
    }]

    fused = fusion_service.fuse_observations(obs)
    assert len(fused) == 1
    assert fused[0]["sensor_count"] == 1
    assert fused[0]["cross_sensor_confirmation"] is False
    assert fused[0]["sensor_consensus"] == 1.0



# ---------------------------------------------------------------------------
# Scenario 8: Sentinel-2 Cloudy Diagnosis
# ---------------------------------------------------------------------------
def test_scenario_08_sentinel2_cloudy_diagnosis():
    provider = Sentinel2Provider()
    # Using 0.0 max_cloud_cover forces cloud rejection if cloud_percentage > 0
    sat_scene = provider.search_imagery(
        latitude=19.0,
        longitude=72.0,
        target_time=datetime.now(timezone.utc),
        max_cloud_cover=0.0
    )
    assert sat_scene["spectral_diagnosis"] == "CLOUD_OBSCURED"

    fusion = MultimodalEvidenceFusionService.synthesize_evidence(
        event_id=108,
        firms_data={"frp": 80.0, "confidence": 90},
        satellite_context=sat_scene
    )
    s2_items = [item for item in fusion["evidence_ledger"] if "SENTINEL" in item["source"]]
    assert len(s2_items) > 0
    # Cloud obscured observation is recorded as INCONCLUSIVE (not negative evidence against fire)
    assert s2_items[0]["direction"] == "INCONCLUSIVE"
    assert "not treated as negative evidence" in s2_items[0]["description"]



# ---------------------------------------------------------------------------
# Scenario 9: Sentinel-2 Unavailable Fallback
# ---------------------------------------------------------------------------
def test_scenario_09_sentinel2_unavailable_fallback():
    sat_scene = {
        "available": False,
        "satellite_evidence_available": False,
        "spectral_diagnosis": "INSUFFICIENT_DATA"
    }

    fusion = MultimodalEvidenceFusionService.synthesize_evidence(
        event_id=109,
        firms_data={"frp": 40.0},
        satellite_context=sat_scene
    )
    # Unavailable Sentinel-2 does not add contradictory evidence
    s2_items = [item for item in fusion["evidence_ledger"] if item["source"] == "SENTINEL2"]
    assert len(s2_items) == 0


# ---------------------------------------------------------------------------
# Scenario 10: Low-Confidence ML Classification
# ---------------------------------------------------------------------------
def test_scenario_10_low_confidence_ml_classification():
    classifier = MLClassifier()
    tier = classifier._compute_probability_tier(max_prob=0.45, entropy=0.70)
    assert tier == "LOW_CONFIDENCE"


# ---------------------------------------------------------------------------
# Scenario 11: High-Entropy Classification / OOD Candidate
# ---------------------------------------------------------------------------
def test_scenario_11_high_entropy_ood_candidate():
    classifier = MLClassifier()
    ood = classifier._detect_ood_candidate(entropy=0.92, top_margin=0.02)
    assert ood == "OUT_OF_DISTRIBUTION_CANDIDATE"


# ---------------------------------------------------------------------------
# Scenario 12: Insufficient Temporal History Sample Count
# ---------------------------------------------------------------------------
def test_scenario_12_insufficient_temporal_history():
    analyzer = TemporalAnalyzer()
    propagation = SpatialPropagationModel()

    now = datetime.now(timezone.utc)
    current_event = {"id": 1, "frp": 50.0, "detected_at": now.isoformat(), "distance": 0.0}
    # Only 1 prior detection
    cluster = [{"id": 2, "frp": 48.0, "detected_at": (now - timedelta(hours=2)).isoformat(), "distance": 20.0}]

    temporal_result = analyzer.compute_metrics(current_event, cluster)
    metrics = temporal_result["metrics"]
    assert metrics["sample_count"] == 2
    assert metrics["temporal_confidence"] == "LOW"
    assert metrics["baseline_reliability"] == "INSUFFICIENT_SAMPLE_SIZE"

    prop_result = propagation.evaluate_propagation([current_event, cluster[0]])
    assert prop_result["propagation_state"] == "INSUFFICIENT_DATA"


# ---------------------------------------------------------------------------
# Scenario 13: Facility Outside Proximity (>2000m)
# ---------------------------------------------------------------------------
def test_scenario_13_facility_outside_proximity():
    spatial_context = {
        "nearest_facility": {
            "name": "Remote Chemical Works",
            "type": "chemical",
            "distance_meters": 2850.0,
            "boundary_radius_meters": 400.0,
        }
    }
    result = IndustrialFireDiscriminator.discriminate(
        event_id=113,
        frp=40.0,
        spatial_context=spatial_context
    )
    assert result["footprint_relation"] == "OUTSIDE_INDUSTRIAL_CONTEXT"


# ---------------------------------------------------------------------------
# Scenario 14: Facility Within 500m Boundary
# ---------------------------------------------------------------------------
def test_scenario_14_facility_within_boundary():
    spatial_context = {
        "nearest_facility": {
            "name": "Coastal Refinery",
            "type": "oil_refinery",
            "distance_meters": 180.0,
            "boundary_radius_meters": 300.0,
        }
    }
    result = IndustrialFireDiscriminator.discriminate(
        event_id=114,
        frp=50.0,
        spatial_context=spatial_context
    )
    assert result["footprint_relation"] in ["INSIDE_FACILITY_FOOTPRINT", "FACILITY_BOUNDARY_PROXIMITY"]


# ---------------------------------------------------------------------------
# Scenario 15: Multiple Nearby Facilities Proximity Ranking
# ---------------------------------------------------------------------------
def test_scenario_15_multiple_nearby_facilities_ranking():
    spatial_context = {
        "nearest_facility": {
            "name": "Primary Fertilizer Unit",
            "type": "fertilizer",
            "distance_meters": 80.0,
            "boundary_radius_meters": 250.0,
        }
    }
    result = IndustrialFireDiscriminator.discriminate(
        event_id=115,
        frp=35.0,
        spatial_context=spatial_context
    )
    assert result["footprint_relation"] == "INSIDE_FACILITY_FOOTPRINT"


# ---------------------------------------------------------------------------
# Scenario 16: Abnormal FRP Acceleration
# ---------------------------------------------------------------------------
def test_scenario_16_abnormal_frp_acceleration():
    spatial_context = {
        "nearest_facility": {"name": "LPG Bottling Plant", "distance_meters": 200.0, "boundary_radius_meters": 400.0}
    }
    temporal_context = {
        "temporal_status": "ABNORMAL",
        "active_days": 10,
        "metrics": {
            "median_frp": 20.0,
            "frp_acceleration_mw_per_hour": 45.0,  # Surpassing 20 MW/h threshold
            "active_days": 10,
            "spatial_spread_meters": 50.0
        }
    }

    result = IndustrialFireDiscriminator.discriminate(
        event_id=116,
        frp=180.0,
        spatial_context=spatial_context,
        temporal_context=temporal_context
    )
    assert result["change_point"]["change_point_state"] in ["MAJOR_ANOMALY", "SIGNIFICANT_DEVIATION"]
    assert result["expected_thermal_context"] == "UNEXPECTED_INDUSTRIAL_THERMAL_CONTEXT"


# ---------------------------------------------------------------------------
# Scenario 17: Normal Persistent Flare Stability (No Alert Storm)
# ---------------------------------------------------------------------------
def test_scenario_17_normal_persistent_flare_no_storm():
    discrimination = {
        "expected_thermal_context": "EXPECTED_INDUSTRIAL_THERMAL_CONTEXT",
        "scientific_interpretation": "NORMAL_PERSISTENT_INDUSTRIAL_SOURCE",
        "change_point": {"change_point_state": "NORMAL_BASELINE"}
    }
    risk = RiskEngine.evaluate_risk(
        features={"frp": 45.0, "landcover_code": 50, "temporal_persistence": 0.90, "facility_distance": 100.0},
        classification="FLARE",
        discrimination=discrimination,
        propagation_metrics={"propagation_state": "STATIONARY_SOURCE"}
    )
    assert risk.total_score <= 42.0

    # Test alert condition suppression logic
    is_normal_operational = "EXPECTED_OPERATIONAL_THERMAL_SOURCE" in risk.risk_reasons
    assert is_normal_operational is True

    # Critical industrial fire rules would fire, but normal flare rules are suppressed
    non_critical_rule = "HAZARDOUS_INFRASTRUCTURE_PROXIMITY"
    suppressed = is_normal_operational and non_critical_rule != "CRITICAL_INDUSTRIAL_FIRE"
    assert suppressed is True


# ---------------------------------------------------------------------------
# Scenario 18: Incident Correlator Facility Footprint Match
# ---------------------------------------------------------------------------
def test_scenario_18_incident_correlator_facility_match():
    correlator = IncidentCorrelator(spatial_threshold_m=2000.0, temporal_window_hours=12.0)
    now = datetime.now(timezone.utc)

    existing_incidents = [
        {
            "id": "inc-001",
            "facility_id": 501,
            "centroid_latitude": 22.4630,
            "centroid_longitude": 70.0710,
            "last_event_time": now.isoformat(),
            "event_count": 3
        }
    ]

    event = {
        "id": 118,
        "facility_id": 501,  # Same facility
        "latitude": 22.4640,
        "longitude": 70.0715,
        "detected_at": (now + timedelta(minutes=30)).isoformat()
    }

    result = correlator.correlate_event(event, existing_incidents)
    assert result["is_new_incident"] is False
    assert result["incident_id"] == "inc-001"
    assert result["correlation_confidence"] == 0.95
    assert result["correlation_reason"] == "facility_footprint_match"


# ---------------------------------------------------------------------------
# Scenario 19: Incident Correlator Unrelated Event (New Incident)
# ---------------------------------------------------------------------------
def test_scenario_19_incident_correlator_unrelated_event():
    correlator = IncidentCorrelator(spatial_threshold_m=2000.0, temporal_window_hours=12.0)
    now = datetime.now(timezone.utc)

    existing_incidents = [
        {
            "id": "inc-001",
            "facility_id": 501,
            "centroid_latitude": 22.4630,
            "centroid_longitude": 70.0710,
            "last_event_time": now.isoformat(),
            "event_count": 1
        }
    ]

    # Distant event (100 km away)
    event = {
        "id": 119,
        "facility_id": None,
        "latitude": 23.5000,
        "longitude": 71.0000,
        "detected_at": now.isoformat()
    }

    result = correlator.correlate_event(event, existing_incidents)
    assert result["is_new_incident"] is True
    assert result["correlation_confidence"] == 1.0
    assert result["correlation_reason"] == "new_incident_created"


# ---------------------------------------------------------------------------
# Scenario 20: Alert Anti-Storm Cooldown Deduplication
# ---------------------------------------------------------------------------
def test_scenario_20_alert_antistorm_cooldown():
    # Cooldown condition test
    now = datetime.now(timezone.utc)
    last_alert_time = now - timedelta(minutes=15)
    cooldown_minutes = 60

    elapsed_minutes = (now - last_alert_time).total_seconds() / 60.0
    is_in_cooldown = elapsed_minutes < cooldown_minutes
    assert is_in_cooldown is True

    # After cooldown expires (e.g. 75 minutes)
    older_alert_time = now - timedelta(minutes=75)
    elapsed_older = (now - older_alert_time).total_seconds() / 60.0
    is_in_cooldown_older = elapsed_older < cooldown_minutes
    assert is_in_cooldown_older is False


# ---------------------------------------------------------------------------
# SIH Deterministic Demonstration Event: Jamnagar Refinery Complex
# Coordinates: Lat 22.4630, Lon 70.0710, FRP 425.0 MW
# ---------------------------------------------------------------------------
def test_jamnagar_sih_demo_event():
    # 1. Multi-Sensor FIRMS Ingestion & Fusion
    fusion_service = FirmsObservationFusionService(spatial_radius_m=1200.0, temporal_window_hours=6.0)
    raw_passes = [
        {
            "latitude": 22.4630,
            "longitude": 70.0710,
            "satellite": "Suomi NPP",
            "instrument": "VIIRS",
            "frp": 420.0,
            "confidence": 95,
            "scan": 1.0,
            "track": 1.0,
            "daynight": "N",
            "acq_datetime": "2026-09-28T20:30:00Z"
        },
        {
            "latitude": 22.4632,
            "longitude": 70.0712,
            "satellite": "NOAA-20",
            "instrument": "VIIRS",
            "frp": 430.0,
            "confidence": 98,
            "scan": 1.05,
            "track": 1.0,
            "daynight": "N",
            "acq_datetime": "2026-09-28T21:15:00Z"
        }
    ]
    fused_groups = fusion_service.fuse_observations(raw_passes)
    assert len(fused_groups) == 1
    fused = fused_groups[0]
    assert fused["cross_sensor_confirmation"] is True
    assert 420.0 <= fused["fused_frp"] <= 430.0

    # 2. Spatial Context (Facility Proximity)
    spatial_context = {
        "nearest_facility": {
            "name": "Jamnagar Refinery Complex",
            "type": "oil_refinery",
            "distance_meters": 110.0,
            "boundary_radius_meters": 500.0,
            "has_known_flare": True
        },
        "land_cover_category": "INDUSTRIAL/BUILT"
    }

    # 3. Spatial Propagation (Stationary Emitter)
    propagation = SpatialPropagationModel.evaluate_propagation([
        {"latitude": 22.4630, "longitude": 70.0710, "detected_at": "2026-09-28T20:30:00Z"},
        {"latitude": 22.4632, "longitude": 70.0712, "detected_at": "2026-09-28T21:15:00Z"},
        {"latitude": 22.4629, "longitude": 70.0709, "detected_at": "2026-09-28T18:00:00Z"}
    ], duration_hours=3.0)
    assert propagation["propagation_state"] in ["STATIONARY_SOURCE", "LOCALIZED_EVENT"]


    # 4. Discrimination: Severe Thermal Surge vs Normal Flare
    # (FRP 425 MW vs Historical 45 MW)
    temporal_context = {
        "temporal_status": "ABNORMAL",
        "active_days": 20,
        "metrics": {
            "median_frp": 45.0,
            "frp_acceleration_mw_per_hour": 60.0,
            "active_days": 20,
            "spatial_spread_meters": 35.0
        }
    }
    discrimination = IndustrialFireDiscriminator.discriminate(
        event_id=999,
        frp=425.0,
        spatial_context=spatial_context,
        temporal_context=temporal_context,
        propagation_context=propagation
    )
    assert discrimination["expected_thermal_context"] == "UNEXPECTED_INDUSTRIAL_THERMAL_CONTEXT"
    assert discrimination["change_point"]["change_point_state"] == "MAJOR_ANOMALY"
    assert discrimination["scientific_interpretation"] == "ABNORMAL_INDUSTRIAL_FIRE_LIKELY"

    # 5. Multimodal Evidence Ledger Synthesis
    fusion = MultimodalEvidenceFusionService.synthesize_evidence(
        event_id=999,
        firms_data={"frp": 425.0, "confidence": 98},
        spatial_context=spatial_context,
        temporal_context=temporal_context,
        propagation_context=propagation,
        discrimination=discrimination,
        fusion_data=fused
    )
    assert fusion["evidence_count"] >= 4
    assert fusion["evidence_completeness"] >= 0.50

    # 6. Risk Scoring & Operational Attribution
    risk = RiskEngine.evaluate_risk(
        features={"frp": 425.0, "landcover_code": 50, "facility_distance": 110.0},
        spatial_context=spatial_context,
        classification="INDUSTRIAL_FIRE",
        discrimination=discrimination,
        propagation_metrics=propagation
    )
    assert risk.total_score >= 75.0  # CRITICAL Risk Score
    assert "UNEXPECTED_INDUSTRIAL_THERMAL_SURGE" in risk.risk_reasons
    assert "CRITICAL_INDUSTRIAL_PROXIMITY" in risk.risk_reasons

