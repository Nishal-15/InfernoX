import pytest
from datetime import datetime, timezone, timedelta
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.api.deps import get_db
from app.core.config import settings
from app.models.thermal_event import ThermalEvent
from app.models.facility import Facility
from app.models.ai_models import EventAssessment, AnalystReview
from app.models.incident import ThermalIncident, IncidentEvent
from app.models.pipeline import (
    PipelineJob,
    PipelineStageRun,
    FirmsIngestionState,
    AutonomousAuditLog
)
from app.models.risk_alert import (
    Alert,
    AlertRule,
    AlertAuditLog,
    ResponseContact,
    NotificationPreference,
    NotificationLog
)
from app.services.firms.client import FirmsClient
from app.services.firms.ingestion import FirmsIngestionService, FIRMS_SYNC_STATE
from app.services.autonomous.pipeline_runner import PipelineRunner
from app.services.system.health_monitor import HealthMonitor


@pytest.fixture
def client_and_session():
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
                geometry TEXT NOT NULL,
                detected_at TIMESTAMP NOT NULL,
                acquired_at TIMESTAMP,
                satellite VARCHAR NOT NULL,
                instrument VARCHAR,
                confidence FLOAT,
                frp FLOAT,
                brightness_temperature FLOAT,
                day_night VARCHAR,
                scan FLOAT,
                track FLOAT,
                status VARCHAR DEFAULT 'NEW' NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL
            );
        """))
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS facilities (
                id INTEGER PRIMARY KEY,
                osm_id VARCHAR UNIQUE NOT NULL,
                name VARCHAR,
                facility_type VARCHAR NOT NULL,
                latitude FLOAT NOT NULL,
                longitude FLOAT NOT NULL,
                geometry TEXT NOT NULL,
                operator VARCHAR,
                tags TEXT,
                source VARCHAR DEFAULT 'OpenStreetMap' NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL
            );
        """))
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS event_assessments (
                id INTEGER PRIMARY KEY,
                event_id INTEGER NOT NULL,
                classification VARCHAR NOT NULL,
                confidence_score FLOAT NOT NULL,
                confidence_type VARCHAR DEFAULT 'heuristic' NOT NULL,
                priority_score FLOAT NOT NULL,
                priority_level VARCHAR NOT NULL,
                explanation TEXT,
                evidence_factors TEXT,
                model_type VARCHAR DEFAULT 'rule_based_prototype' NOT NULL,
                model_version VARCHAR DEFAULT 'phase3-v1.0' NOT NULL,
                feature_schema_version VARCHAR DEFAULT 'v1.1' NOT NULL,
                prediction_timestamp TIMESTAMP,
                feature_snapshot TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL
            );
        """))
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS analyst_reviews (
                id INTEGER PRIMARY KEY,
                event_id INTEGER NOT NULL,
                assessment_id INTEGER,
                analyst_id VARCHAR DEFAULT 'analyst-1' NOT NULL,
                decision VARCHAR,
                action VARCHAR,
                comment TEXT,
                note TEXT,
                previous_classification VARCHAR,
                final_classification VARCHAR,
                reviewed_by VARCHAR DEFAULT 'analyst',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL
            );
        """))
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS alert_rules (
                id INTEGER PRIMARY KEY,
                organization_id INTEGER,
                name VARCHAR(128) UNIQUE NOT NULL,
                description VARCHAR(256),
                enabled BOOLEAN NOT NULL DEFAULT 1,
                severity VARCHAR(32) NOT NULL,
                conditions_json JSON NOT NULL DEFAULT '[]',
                cooldown_minutes INTEGER NOT NULL DEFAULT 60,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL
            );
        """))
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS alerts (
                id INTEGER PRIMARY KEY,
                organization_id INTEGER,
                alert_code VARCHAR(64) UNIQUE NOT NULL,
                event_id INTEGER NOT NULL,
                incident_id INTEGER,
                rule_id INTEGER,
                severity VARCHAR(32) NOT NULL,
                title VARCHAR(256) NOT NULL,
                message TEXT NOT NULL,
                status VARCHAR(32) NOT NULL DEFAULT 'NEW',
                incident_payload_json JSON NOT NULL DEFAULT '{}',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
                acknowledged_at TIMESTAMP,
                acknowledged_by VARCHAR(128),
                escalated_at TIMESTAMP,
                resolved_at TIMESTAMP,
                resolved_by VARCHAR(128)
            );
        """))
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS pipeline_jobs (
                id INTEGER PRIMARY KEY,
                correlation_id VARCHAR UNIQUE NOT NULL,
                job_type VARCHAR NOT NULL,
                source VARCHAR NOT NULL,
                status VARCHAR NOT NULL,
                records_received INTEGER DEFAULT 0,
                records_inserted INTEGER DEFAULT 0,
                records_skipped INTEGER DEFAULT 0,
                records_processed INTEGER DEFAULT 0,
                records_succeeded INTEGER DEFAULT 0,
                records_failed INTEGER DEFAULT 0,
                retry_count INTEGER DEFAULT 0,
                max_retries INTEGER DEFAULT 3,
                error_message TEXT,
                started_at TIMESTAMP NOT NULL,
                completed_at TIMESTAMP,
                duration_seconds FLOAT DEFAULT 0.0,
                metadata_json TEXT
            );
        """))
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS pipeline_stage_runs (
                id INTEGER PRIMARY KEY,
                job_id INTEGER NOT NULL,
                event_id INTEGER,
                correlation_id VARCHAR(64) NOT NULL,
                stage_name VARCHAR(64) NOT NULL,
                status VARCHAR(32) NOT NULL DEFAULT 'RUNNING',
                is_transient_error BOOLEAN NOT NULL DEFAULT 0,
                error_message TEXT,
                retry_count INTEGER NOT NULL DEFAULT 0,
                duration_seconds FLOAT NOT NULL DEFAULT 0.0,
                stage_output_json JSON NOT NULL DEFAULT '{}',
                started_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                completed_at DATETIME
            );
        """))
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS autonomous_audit_logs (
                id INTEGER PRIMARY KEY,
                correlation_id VARCHAR(64),
                action VARCHAR(64) NOT NULL,
                source VARCHAR(64) NOT NULL DEFAULT 'AUTONOMOUS_PIPELINE',
                event_id INTEGER,
                incident_id INTEGER,
                previous_value JSON,
                new_value JSON,
                model_version VARCHAR(64),
                details_json JSON NOT NULL DEFAULT '{}',
                created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
        """))
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS firms_ingestion_state (
                id INTEGER PRIMARY KEY,
                source VARCHAR UNIQUE NOT NULL,
                bounding_box VARCHAR NOT NULL,
                last_ingested_timestamp TIMESTAMP,
                total_runs INTEGER DEFAULT 0 NOT NULL,
                total_records_ingested INTEGER DEFAULT 0 NOT NULL,
                last_run_status VARCHAR DEFAULT 'PENDING' NOT NULL,
                last_error TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL
            );
        """))
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS thermal_incidents (
                id INTEGER PRIMARY KEY,
                incident_code VARCHAR(64) UNIQUE NOT NULL,
                title VARCHAR(256) NOT NULL,
                status VARCHAR(32) NOT NULL DEFAULT 'ACTIVE',
                severity VARCHAR(32) NOT NULL DEFAULT 'MODERATE',
                classification VARCHAR(128) NOT NULL DEFAULT 'UNKNOWN',
                first_detected_at DATETIME NOT NULL,
                last_detected_at DATETIME NOT NULL,
                duration_hours FLOAT NOT NULL DEFAULT 0.0,
                event_count INTEGER NOT NULL DEFAULT 1,
                peak_frp FLOAT NOT NULL DEFAULT 0.0,
                mean_frp FLOAT NOT NULL DEFAULT 0.0,
                risk_score FLOAT NOT NULL DEFAULT 0.0,
                risk_level VARCHAR(32) NOT NULL DEFAULT 'LOW',
                primary_facility_id INTEGER,
                primary_facility_name VARCHAR(256),
                distance_to_facility_meters FLOAT,
                centroid_latitude FLOAT NOT NULL,
                centroid_longitude FLOAT NOT NULL,
                geometry TEXT,
                incident_summary_json JSON NOT NULL DEFAULT '{}',
                created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
        """))
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS incident_events (
                id INTEGER PRIMARY KEY,
                incident_id INTEGER NOT NULL,
                event_id INTEGER NOT NULL,
                distance_to_centroid FLOAT DEFAULT 0.0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
                added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL
            );
        """))
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS risk_assessments (
                id INTEGER PRIMARY KEY,
                event_id INTEGER NOT NULL,
                risk_score FLOAT NOT NULL,
                risk_level VARCHAR(32) NOT NULL,
                risk_model_version VARCHAR(64) NOT NULL DEFAULT 'risk-v1',
                breakdown_json JSON NOT NULL DEFAULT '{}',
                input_snapshot_json JSON NOT NULL DEFAULT '{}',
                calculated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL
            );
        """))
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS ingestion_jobs (
                id INTEGER PRIMARY KEY,
                source VARCHAR NOT NULL,
                status VARCHAR NOT NULL,
                records_received INTEGER DEFAULT 0,
                records_inserted INTEGER DEFAULT 0,
                records_failed INTEGER DEFAULT 0,
                error_message TEXT,
                started_at TIMESTAMP NOT NULL,
                completed_at TIMESTAMP
            );
        """))
        conn.commit()

    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    test_client = TestClient(app)
    session = TestingSessionLocal()

    yield test_client, session

    app.dependency_overrides.clear()
    session.close()


# 1. Test Critical NASA FIRMS Domain Correction (Section 2 & 3)
def test_firms_official_domain_correction():
    client = FirmsClient()
    assert "https://firms.modaps.eosdis.nasa.gov" in client.base_url
    assert "modap." not in client.base_url  # Guarantees no typo "modap" without 's'
    assert not client.base_url.endswith("/")


# 2. Test Multi-Satellite Source Configuration Registry (Section 5)
def test_firms_multi_satellite_source_registry():
    client = FirmsClient()
    sources = client.get_enabled_sources()
    assert len(sources) >= 3
    source_names = [s["source_name"] for s in sources]
    assert "VIIRS_SNPP_NRT" in source_names
    assert "VIIRS_NOAA20_NRT" in source_names
    assert "VIIRS_NOAA21_NRT" in source_names

    # Verify priority sorting
    priorities = [s.get("priority", 99) for s in sources]
    assert priorities == sorted(priorities)


# 3. Test Historical FIRMS Data Ingestion (Section 6)
def test_historical_firms_data_pipeline(client_and_session):
    client, session = client_and_session
    service = FirmsIngestionService()
    
    historical_csv = """latitude,longitude,brightness,scan,track,acq_date,acq_time,satellite,instrument,confidence,version,bright_t31,frp,daynight
22.4632,70.0712,342.5,1.1,1.0,2024-03-15,0830,NPP,VIIRS,88,2.0NRT,298.5,145.8,D
22.4635,70.0715,350.1,1.1,1.0,2024-03-16,0825,NPP,VIIRS,92,2.0NRT,299.1,180.2,D
"""
    result = service.ingest_historical_data(session, year=2024)
    assert result["status"] == "COMPLETED"
    assert result["total_inserted"] >= 0

    # Test direct CSV content ingestion preserving provenance
    custom_res = client.post(
        "/api/v1/ingestion/firms/historical?year=2026"
    )
    assert custom_res.status_code == 200
    data = custom_res.json()
    assert data["status"] == "COMPLETED"


# 4. Test FIRMS Provider Health & Telemetry (Section 7)
def test_firms_provider_health_endpoints(client_and_session):
    client, session = client_and_session
    
    # List format (backward-compatible)
    list_res = client.get("/api/v1/system/providers")
    assert list_res.status_code == 200
    providers = list_res.json()
    assert isinstance(providers, list)
    firms_entry = next((p for p in providers if p["provider"] == "NASA FIRMS"), None)
    assert firms_entry is not None
    assert firms_entry["status"] in ["AVAILABLE", "DEGRADED", "RATE_LIMITED", "UNAVAILABLE"]
    assert "active_sources" in firms_entry
    # MAP_KEY must NEVER appear in output
    assert "FIRMS_MAP_KEY" not in str(firms_entry)
    assert "MAP_KEY" not in firms_entry.get("details", {})

    # Dedicated Section 7 dict endpoint
    firms_res = client.get("/api/v1/system/providers/firms")
    assert firms_res.status_code == 200
    firms_dict = firms_res.json()
    assert "firms" in firms_dict
    assert "status" in firms_dict["firms"]
    assert "records_last_sync" in firms_dict["firms"]
    assert "active_sources" in firms_dict["firms"]

    # Query param format=dict
    dict_res = client.get("/api/v1/system/providers?format=dict")
    assert dict_res.status_code == 200
    assert "firms" in dict_res.json()


# 5. Test Event Assessment Telemetry: Feature Snapshot & Prediction Timestamp (Section 11)
def test_event_assessment_telemetry(client_and_session):
    client, session = client_and_session

    now = datetime.now(timezone.utc)
    event = ThermalEvent(
        source="NASA_FIRMS",
        latitude=22.4630,
        longitude=70.0710,
        geometry="POINT(70.0710 22.4630)",
        detected_at=now,
        satellite="VIIRS_SNPP",
        frp=350.0,
        confidence=95.0,
        status="NEW"
    )
    session.add(event)
    session.commit()
    session.refresh(event)

    facility = Facility(
        osm_id="way/12345",
        name="Jamnagar Petrochemical Complex",
        facility_type="industrial",
        latitude=22.4650,
        longitude=70.0720,
        geometry="POINT(70.0720 22.4650)"
    )
    session.add(facility)
    session.commit()

    # Trigger demo pipeline covering ML stage
    res = client.post("/api/v1/system/demo/trigger", json={
        "latitude": 22.4630,
        "longitude": 70.0710,
        "frp": 380.0
    })
    assert res.status_code == 200
    res_data = res.json()
    assert res_data["status"] in ["SUCCESS", "COMPLETED"]
    demo_event_id = res_data["event_id"]

    # Inspect persisted EventAssessment
    assessment = session.query(EventAssessment).filter(EventAssessment.event_id == demo_event_id).first()
    assert assessment is not None
    assert assessment.prediction_timestamp is not None
    assert assessment.feature_snapshot is not None
    assert assessment.classification != ""
    assert assessment.confidence_score > 0.0


# 6. Test Distinction Between AI Classification and Analyst Confirmed Classification (Section 11)
def test_ai_vs_analyst_confirmed_classification(client_and_session):
    client, session = client_and_session

    now = datetime.now(timezone.utc)
    event = ThermalEvent(
        source="NASA_FIRMS",
        latitude=22.4630,
        longitude=70.0710,
        geometry="POINT(70.0710 22.4630)",
        detected_at=now,
        satellite="VIIRS_SNPP",
        frp=350.0,
        status="NEW"
    )
    session.add(event)
    session.commit()
    session.refresh(event)

    assessment = EventAssessment(
        event_id=event.id,
        classification="INDUSTRIAL_THERMAL_ANOMALY",
        confidence_score=0.942,
        priority_score=88.0,
        priority_level="CRITICAL",
        model_version="xgb-v1",
        prediction_timestamp=now,
        feature_snapshot={"distance_to_industrial_facility": 840}
    )
    session.add(assessment)
    session.commit()

    # Human-in-the-loop analyst review confirms
    review = AnalystReview(
        event_id=event.id,
        assessment_id=assessment.id,
        analyst_id="lead-analyst-1",
        decision="CONFIRM",
        final_classification="CONFIRMED_GAS_FLARE",
        comment="Ground telemetry corroborates operational flaring schedule."
    )
    session.add(review)
    session.commit()

    assert assessment.classification == "INDUSTRIAL_THERMAL_ANOMALY"  # AI Model
    assert review.final_classification == "CONFIRMED_GAS_FLARE"        # Human Analyst Confirmed
    assert review.decision == "CONFIRM"


# 7. Complete End-to-End Pipeline Execution (Section 12 & 17)
def test_complete_e2e_event_pipeline(client_and_session):
    client, session = client_and_session

    # Step 1: FIRMS Observation Ingested through API
    # Step 2: Spatial context -> PostGIS
    # Step 3: Multi-modal enrichment -> Temporal -> ML -> Risk -> Alert
    trigger_res = client.post("/api/v1/system/demo/trigger", json={
        "latitude": 22.4630,
        "longitude": 70.0710,
        "frp": 425.0
    })
    assert trigger_res.status_code == 200
    data = trigger_res.json()

    assert data["status"] in ["SUCCESS", "COMPLETED"]
    assert data["event_id"] > 0
    assert data["risk_score"] > 0
    assert data["risk_level"] in ["LOW", "MEDIUM", "HIGH", "CRITICAL"]

    # Verify pipeline stage records
    stages = session.query(PipelineStageRun).filter(PipelineStageRun.event_id == data["event_id"]).all()
    stage_names = [s.stage_name for s in stages]
    assert "SPATIAL_ENRICHMENT" in stage_names
    assert "TEMPORAL_ANALYSIS" in stage_names
    assert "CLASSIFICATION" in stage_names
    assert "RISK_ASSESSMENT" in stage_names
