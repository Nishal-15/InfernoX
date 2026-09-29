import pytest
import math
from datetime import datetime, timedelta, timezone

from app.services.intelligence.industrial_discriminator import IndustrialFireDiscriminator
from app.services.firms.fusion import FirmsObservationFusionService
from app.services.temporal.analyzer import TemporalAnalyzer
from app.services.intelligence.propagation import SpatialPropagationModel
from app.services.satellite.provider import Sentinel2Provider
from app.services.alert.engine import AlertEngine
from sqlalchemy import create_engine, text, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from app.models.risk_alert import AlertRule, Alert, AlertAuditLog, ResponseContact, NotificationPreference, NotificationLog
from app.models.thermal_event import ThermalEvent


# ===========================================================================
# Defect 1 Regression Test: Multi-Sensor Observation Fusion in Live Pipeline
# ===========================================================================
def test_defect_01_multi_sensor_fusion_service():
    service = FirmsObservationFusionService(spatial_radius_meters=1200.0, temporal_window_hours=6.0)
    now = datetime.now(timezone.utc)
    
    records = [
        {
            "id": 1001,
            "latitude": 22.4700,
            "longitude": 70.0500,
            "frp": 85.0,
            "confidence": 95,
            "satellite": "NOAA-20",
            "instrument": "VIIRS",
            "detected_at": now.isoformat()
        },
        {
            "id": 1002,
            "latitude": 22.4710,
            "longitude": 70.0508,
            "frp": 88.0,
            "confidence": 90,
            "satellite": "SUOMI NPP",
            "instrument": "VIIRS",
            "detected_at": (now - timedelta(hours=1)).isoformat()
        }
    ]

    fused = service.fuse_observations(records)
    assert len(fused) == 1
    grp = fused[0]
    assert grp["cross_sensor_confirmation"] is True
    assert grp["unique_sensor_count"] == 2
    assert "NOAA-20" in grp["sensors"]
    assert "SUOMI NPP" in grp["sensors"]
    assert grp["fused_frp"] > 80.0
    assert grp["fused_latitude"] is not None


# ===========================================================================
# Defect 2 Regression Test: Facility Geometry & Ray-Casting Footprint Relation
# ===========================================================================
def test_defect_02_facility_geometry_polygon_raycasting():
    # 1. Point geometry must NEVER claim INSIDE_FACILITY_FOOTPRINT without polygon proof
    point_geom = {"type": "Point", "coordinates": [70.05, 22.47]}
    rel_point_only = IndustrialFireDiscriminator.evaluate_footprint_relation(
        distance_meters=80.0,
        facility_geometry=point_geom,
        point_coords=(70.05, 22.47)
    )
    assert rel_point_only == "FACILITY_BOUNDARY_PROXIMITY"
    assert rel_point_only != "INSIDE_FACILITY_FOOTPRINT"
    assert rel_point_only != "PROCESS_AREA_PROXIMITY"

    # 2. No distance provided returns OUTSIDE_INDUSTRIAL_CONTEXT
    assert IndustrialFireDiscriminator.evaluate_footprint_relation(None) == "OUTSIDE_INDUSTRIAL_CONTEXT"

    # 3. Invalid geometry (e.g. empty or unclosed ring with < 3 points) returns INVALID_GEOMETRY
    invalid_geom = {"type": "Polygon", "coordinates": [[]]}
    assert IndustrialFireDiscriminator.evaluate_footprint_relation(50.0, facility_geometry=invalid_geom) == "INVALID_GEOMETRY"

    # 4. Valid Polygon: Point inside facility process area
    refinery_poly = {
        "type": "Polygon",
        "coordinates": [[
            [70.0400, 22.4600],
            [70.0600, 22.4600],
            [70.0600, 22.4800],
            [70.0400, 22.4800],
            [70.0400, 22.4600]
        ]]
    }
    inside_point = (70.0500, 22.4700)
    rel_inside_proc = IndustrialFireDiscriminator.evaluate_footprint_relation(
        distance_meters=0.0,
        facility_geometry=refinery_poly,
        point_coords=inside_point,
        facility_type="crude_distillation_process_unit"
    )
    assert rel_inside_proc == "PROCESS_AREA_PROXIMITY"

    # 5. Point inside general facility
    rel_inside_gen = IndustrialFireDiscriminator.evaluate_footprint_relation(
        distance_meters=0.0,
        facility_geometry=refinery_poly,
        point_coords=inside_point,
        facility_type="oil_refinery"
    )
    assert rel_inside_gen == "INSIDE_FACILITY_FOOTPRINT"

    # 6. Point outside polygon
    outside_point = (70.0800, 22.5000)
    rel_outside = IndustrialFireDiscriminator.evaluate_footprint_relation(
        distance_meters=4500.0,
        facility_geometry=refinery_poly,
        point_coords=outside_point,
        facility_type="oil_refinery"
    )
    assert rel_outside == "OUTSIDE_INDUSTRIAL_CONTEXT"


# ===========================================================================
# Defect 3 Regression Test: Prevent Single-Linkage Runaway Chaining
# ===========================================================================
def test_defect_03_sensor_fusion_single_linkage_chaining_prevention():
    service = FirmsObservationFusionService(spatial_radius_meters=1200.0, temporal_window_hours=6.0)
    now = datetime.now(timezone.utc)

    # 3 points along a line where each step is 900m, but point 1 to point 3 is 1800m
    # Under single-linkage chaining (comparing only to c[-1]), point 3 would merge.
    # Under our centroid / max pairwise distance guard, point 3 MUST split into a new cluster.
    records = [
        {
            "id": 1,
            "latitude": 20.0000,
            "longitude": 75.0000,
            "frp": 50.0,
            "detected_at": now.isoformat()
        },
        {
            "id": 2,
            "latitude": 20.0080,  # ~888m north of point 1
            "longitude": 75.0000,
            "frp": 55.0,
            "detected_at": (now + timedelta(minutes=30)).isoformat()
        },
        {
            "id": 3,
            "latitude": 20.0240,  # ~1776m north of point 2, ~2664m north of point 1!
            "longitude": 75.0000,
            "frp": 60.0,
            "detected_at": (now + timedelta(minutes=60)).isoformat()
        }
    ]

    fused = service.fuse_observations(records)
    # Point 3 must NOT be merged into the same group as Point 1!
    assert len(fused) >= 2


# ===========================================================================
# Defect 4 Regression Test: Quality Weight Calculation Numerical Guards
# ===========================================================================
def test_defect_04_sensor_weighting_numerical_guards():
    # Pass NaN scan/track, negative values, and infinite confidence
    bad_record = {
        "satellite": "NOAA-20",
        "instrument": "VIIRS",
        "scan": float("nan"),
        "track": -2.0,
        "confidence": float("inf"),
        "daynight": "N"
    }
    weight, audit = FirmsObservationFusionService.calculate_sensor_weight(bad_record)
    assert not math.isnan(weight)
    assert not math.isinf(weight)
    assert weight > 0.0
    assert audit["footprint_factor"] == 1.0


# ===========================================================================
# Defect 5 Regression Test: Temporal Analyzer Out-of-Order & Zero-MAD Baseline
# ===========================================================================
def test_defect_05_temporal_out_of_order_and_zero_mad():
    analyzer = TemporalAnalyzer(radius_meters=1000.0)
    now = datetime.now(timezone.utc)

    # Subtest 5a: Zero-variance baseline (MAD = 0) with sudden FRP explosion
    cluster_records = [
        {"id": 1, "frp": 40.0, "detected_at": (now - timedelta(days=3)).isoformat()},
        {"id": 2, "frp": 40.0, "detected_at": (now - timedelta(days=2)).isoformat()},
        {"id": 3, "frp": 40.0, "detected_at": (now - timedelta(days=1)).isoformat()},
    ]
    current_event = {
        "id": 4,
        "frp": 600.0,  # Extreme surge
        "detected_at": now.isoformat()
    }

    res = analyzer.compute_metrics(current_event, cluster_records)
    metrics = res["metrics"]
    # MAD is 0 for identical 40 MW readings, but robust z-score must NOT be 0!
    assert metrics["mad_frp"] == 0.0
    assert metrics["robust_z_score"] > 20.0, f"Expected high z-score for 600MW surge, got {metrics['robust_z_score']}"

    # Subtest 5b: Out-of-order / backfilled event correctly finds chronological predecessor
    # Suppose current_event was detected yesterday, but cluster contains an event from today
    event_yesterday = {"id": 10, "frp": 120.0, "detected_at": (now - timedelta(days=1)).isoformat()}
    cluster_with_future = [
        {"id": 9, "frp": 40.0, "detected_at": (now - timedelta(days=2)).isoformat()},
        {"id": 11, "frp": 80.0, "detected_at": now.isoformat()},  # Future relative to event 10
    ]
    res_ooo = analyzer.compute_metrics(event_yesterday, cluster_with_future)
    # The predecessor for event 10 is event 9 (24 hours prior, delta FRP = +80 MW), not event 11
    accel = res_ooo["metrics"]["frp_acceleration_mw_per_hour"]
    assert accel > 0.0, f"Expected positive acceleration from event 9 -> 10, got {accel}"


# ===========================================================================
# Defect 6 Regression Test: Spatial Propagation Stationary Safety Guard
# ===========================================================================
def test_defect_06_spatial_propagation_stationary_guard():
    now = datetime.now(timezone.utc)
    # Stationary refinery flare cluster with small spread (< 250m) but high temporal density
    # (e.g. two passes 15 minutes apart with 120m GPS jitter)
    cluster = [
        {"latitude": 22.4700, "longitude": 70.0500, "detected_at": now.isoformat()},
        {"latitude": 22.4710, "longitude": 70.0505, "detected_at": (now - timedelta(minutes=15)).isoformat()},
        {"latitude": 22.4705, "longitude": 70.0502, "detected_at": (now - timedelta(minutes=30)).isoformat()},
    ]
    prop = SpatialPropagationModel.analyze_propagation(
        current_event=cluster[0],
        cluster_records=cluster[1:],
        duration_hours=0.5
    )
    # Under no circumstances can a stationary 120m cluster be called a PROPAGATING_EVENT wildfire!
    assert prop["propagation_state"] == "STATIONARY_SOURCE"
    assert prop["spread_radius_meters"] <= 350.0


# ===========================================================================
# Defect 7 Regression Test: Sentinel-2 Zero/Nodata and Water Burn Scar Guard
# ===========================================================================
def test_defect_07_sentinel2_nodata_and_water_burn_scar():
    # 1. Total black/nodata pixel (reflectance 0.0 across all bands)
    spec_nodata = Sentinel2Provider._calculate_spectral_indices(
        red=0.0, green=0.0, blue=0.0, nir=0.0, swir1=0.0, swir2=0.0
    )
    assert spec_nodata["burn_scar_indicator"] is False, "Black/nodata pixel must never trigger burn scar!"

    # 2. Water pixel (high NDWI, low NIR)
    spec_water = Sentinel2Provider._calculate_spectral_indices(
        red=0.05, green=0.20, blue=0.22, nir=0.02, swir1=0.01, swir2=0.01
    )
    assert spec_water["burn_scar_indicator"] is False, "Water pixel must not trigger burn scar!"

    # 3. Genuine severe burn scar (depressed NBR with genuine SWIR2 reflectance)
    spec_burn = Sentinel2Provider._calculate_spectral_indices(
        red=0.15, green=0.10, blue=0.08, nir=0.08, swir1=0.28, swir2=0.24
    )
    assert spec_burn["burn_scar_indicator"] is True, "Genuine burn scar must be detected!"


# ===========================================================================
# Defect 8 Regression Test: Alert Cooldown Severity Escalation Bypass
# ===========================================================================
def test_defect_08_alert_cooldown_escalation_bypass():
    test_engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool
    )

    @event.listens_for(test_engine, "connect")
    def register_gis_functions(dbapi_connection, connection_record):
        dbapi_connection.create_function("GeomFromEWKT", 1, lambda x: x)
        dbapi_connection.create_function("RecoverGeometryColumn", 5, lambda a, b, c, d, e: 1)
        dbapi_connection.create_function("AsEWKT", 1, lambda x: x)
        dbapi_connection.create_function("AsEWKB", 1, lambda x: b"\x01\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00" if x else None)
        dbapi_connection.create_function("AsBinary", 1, lambda x: b"\x01\x01\x00\x00\x00" if x else None)
        dbapi_connection.create_function("ST_DWithin", 3, lambda a, b, c: 1)
        dbapi_connection.create_function("ST_Distance", 2, lambda a, b: 150.0)
        dbapi_connection.create_function("ST_GeomFromEWKT", 1, lambda x: x)
        dbapi_connection.create_function("CreateSpatialIndex", 2, lambda a, b: 1)

    with test_engine.connect() as conn:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS thermal_events (
                id INTEGER PRIMARY KEY,
                source VARCHAR NOT NULL,
                source_id VARCHAR,
                latitude FLOAT NOT NULL,
                longitude FLOAT NOT NULL,
                geometry TEXT,
                detected_at DATETIME NOT NULL,
                acquired_at DATETIME,
                satellite VARCHAR NOT NULL,
                instrument VARCHAR,
                confidence FLOAT,
                frp FLOAT,
                brightness_temperature FLOAT,
                day_night VARCHAR,
                scan FLOAT,
                track FLOAT,
                status VARCHAR DEFAULT 'NEW',
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """))
        conn.commit()

    AlertRule.__table__.create(bind=test_engine, checkfirst=True)
    Alert.__table__.create(bind=test_engine, checkfirst=True)
    AlertAuditLog.__table__.create(bind=test_engine, checkfirst=True)
    ResponseContact.__table__.create(bind=test_engine, checkfirst=True)
    NotificationPreference.__table__.create(bind=test_engine, checkfirst=True)
    NotificationLog.__table__.create(bind=test_engine, checkfirst=True)

    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)
    db = TestingSessionLocal()
    now = datetime.now(timezone.utc)

    try:
        # Create a mock event
        ev = ThermalEvent(
            id=501,
            latitude=22.4700,
            longitude=70.0500,
            frp=650.0,
            confidence=98.0,
            source="TEST",
            satellite="VIIRS_NOAA20",
            status="NEW",
            detected_at=now
        )
        db.add(ev)
        db.commit()

        # Create a CRITICAL rule
        crit_rule = AlertRule(
            id=1,
            name="TEST_CRITICAL_RULE",
            description="Test critical rule",
            severity="CRITICAL",
            enabled=True,
            cooldown_minutes=60,
            conditions_json=[{"field": "risk_score", "op": ">=", "value": 75.0}]
        )
        db.add(crit_rule)
        db.commit()

        # Simulate an existing LOW severity alert created 10 minutes ago
        recent_low_alert = Alert(
            id=1,
            alert_code="ALT-TEST-LOW-001",
            event_id=ev.id,
            rule_id=crit_rule.id,
            severity="LOW",
            status="NEW",
            title="Low Warning",
            message="Initial detection",
            incident_payload_json={"risk_score": 25.0},
            created_at=now - timedelta(minutes=10)
        )
        db.add(recent_low_alert)
        db.commit()

        # Evaluate alerts for a sudden CRITICAL surge (Risk 92.0)
        alerts = AlertEngine.evaluate_event_alerts(
            db=db,
            event=ev,
            risk_data={"risk_score": 92.0, "risk_level": "CRITICAL"},
            classification="INDUSTRIAL_FIRE",
            spatial_context={"nearest_facility": {"name": "Test Refinery", "facility_type": "oil_refinery", "distance_meters": 100.0}}
        )

        # The CRITICAL escalation MUST NOT be suppressed by the prior LOW alert!
        crit_fired = any(a.severity == "CRITICAL" for a in alerts)
        assert crit_fired is True, "Critical escalation must bypass cooldown!"

    finally:
        db.close()
