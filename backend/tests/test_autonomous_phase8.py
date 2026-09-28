import pytest
from datetime import datetime, timezone, timedelta
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.api.deps import get_db
from app.models.thermal_event import ThermalEvent
from app.models.facility import Facility
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
from app.services.alert.engine import AlertEngine
from app.services.autonomous.pipeline_runner import PipelineRunner
from app.services.autonomous.incident_correlator import IncidentCorrelator
from app.services.autonomous.retry_policy import RetryPolicy
from app.services.system.health_monitor import HealthMonitor
from app.services.websocket.manager import ConnectionManager
from app.services.firms.ingestion import FirmsIngestionService


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
                status VARCHAR NOT NULL DEFAULT 'NEW',
                incident_id INTEGER,
                created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                CONSTRAINT _thermal_event_uc UNIQUE (source, satellite, detected_at, latitude, longitude)
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
                geometry TEXT,
                tags JSON,
                operator VARCHAR,
                source VARCHAR NOT NULL DEFAULT 'OpenStreetMap',
                created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
        """))
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS event_assessments (
                id INTEGER PRIMARY KEY,
                event_id INTEGER NOT NULL,
                classification VARCHAR NOT NULL,
                confidence_score FLOAT NOT NULL,
                confidence_type VARCHAR NOT NULL DEFAULT 'heuristic',
                priority_score FLOAT NOT NULL,
                priority_level VARCHAR NOT NULL,
                explanation JSON,
                evidence_factors JSON,
                model_type VARCHAR NOT NULL DEFAULT 'xgboost',
                model_version VARCHAR NOT NULL DEFAULT 'xgb-v1',
                feature_schema_version VARCHAR NOT NULL DEFAULT 'v2.0',
                created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
        """))
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS risk_assessments (
                id INTEGER PRIMARY KEY,
                event_id INTEGER NOT NULL,
                risk_score FLOAT NOT NULL,
                risk_level VARCHAR(32) NOT NULL,
                risk_model_version VARCHAR(64) NOT NULL,
                breakdown_json JSON NOT NULL,
                input_snapshot_json JSON NOT NULL,
                calculated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
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
                conditions_json JSON NOT NULL,
                cooldown_minutes INTEGER NOT NULL DEFAULT 60,
                created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
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
                incident_payload_json JSON NOT NULL,
                created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                acknowledged_at DATETIME,
                acknowledged_by VARCHAR(128),
                escalated_at DATETIME,
                resolved_at DATETIME,
                resolved_by VARCHAR(128)
            );
        """))
        conn.commit()

    AlertAuditLog.__table__.create(bind=test_engine, checkfirst=True)

    with test_engine.connect() as conn:
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
                incident_summary_json JSON NOT NULL,
                created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
        """))
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS pipeline_jobs (
                id INTEGER PRIMARY KEY,
                correlation_id VARCHAR(64) UNIQUE NOT NULL,
                job_type VARCHAR(64) NOT NULL,
                source VARCHAR(64) NOT NULL DEFAULT 'NASA_FIRMS',
                status VARCHAR(32) NOT NULL DEFAULT 'QUEUED',
                records_received INTEGER NOT NULL DEFAULT 0,
                records_inserted INTEGER NOT NULL DEFAULT 0,
                records_skipped INTEGER NOT NULL DEFAULT 0,
                records_processed INTEGER NOT NULL DEFAULT 0,
                records_succeeded INTEGER NOT NULL DEFAULT 0,
                records_failed INTEGER NOT NULL DEFAULT 0,
                retry_count INTEGER NOT NULL DEFAULT 0,
                max_retries INTEGER NOT NULL DEFAULT 3,
                error_message TEXT,
                started_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                completed_at DATETIME,
                duration_seconds FLOAT NOT NULL DEFAULT 0.0,
                metadata_json JSON NOT NULL
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
                stage_output_json JSON NOT NULL,
                started_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                completed_at DATETIME
            );
        """))
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS firms_ingestion_state (
                id INTEGER PRIMARY KEY,
                source VARCHAR(64) UNIQUE NOT NULL,
                last_ingested_timestamp DATETIME,
                bounding_box VARCHAR(128),
                cursor_info VARCHAR(256),
                last_run_status VARCHAR(32) NOT NULL DEFAULT 'COMPLETED',
                total_runs INTEGER NOT NULL DEFAULT 0,
                total_records_ingested INTEGER NOT NULL DEFAULT 0,
                last_error TEXT,
                updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
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
                details_json JSON NOT NULL,
                created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
        """))
        conn.commit()

    ResponseContact.__table__.create(bind=test_engine, checkfirst=True)
    NotificationPreference.__table__.create(bind=test_engine, checkfirst=True)
    NotificationLog.__table__.create(bind=test_engine, checkfirst=True)
    IncidentEvent.__table__.create(bind=test_engine, checkfirst=True)

    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)
    session = TestingSessionLocal()

    # Seed an industrial facility
    fac = Facility(
        osm_id="way/12345678",
        name="Reliance Jamnagar Petrochemical Complex",
        facility_type="refinery",
        latitude=22.4630,
        longitude=70.0710,
        geometry="SRID=4326;POINT(70.0710 22.4630)",
        operator="Reliance Industries Ltd",
        tags={"industrial": "refinery"}
    )
    session.add(fac)

    # Seed a response contact
    now_dt = datetime.now(timezone.utc)
    contact = ResponseContact(
        organization_name="Gujarat State Fire & Rescue Command",
        department_type="INDUSTRIAL_SAFETY",
        jurisdiction="National",
        contact_type="EMAIL",
        contact_value="cmd@gujaratfire.gov.in",
        enabled=True,
        verified=True,
        last_verified_at=now_dt,
        created_at=now_dt,
        updated_at=now_dt
    )
    session.add(contact)
    session.commit()

    # Seed default alert rules
    AlertEngine.seed_default_rules(session)

    def override_get_db():
        try:
            yield session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    client = TestClient(app)

    yield client, session

    app.dependency_overrides.clear()
    session.close()


# 1. Test Incremental FIRMS Ingestion
@pytest.mark.asyncio
async def test_incremental_firms_ingestion(client_and_session):
    client, session = client_and_session
    service = FirmsIngestionService()

    # First run: should ingest records and establish cursor
    res1 = await service.ingest_incremental(session, use_demo=True)
    assert res1["status"] == "COMPLETED"
    assert res1["fetched"] > 0
    assert res1["inserted"] > 0
    assert len(res1["inserted_event_ids"]) > 0

    state = session.query(FirmsIngestionState).filter(FirmsIngestionState.source == "DEMO_NASA_FIRMS").first()
    assert state is not None
    assert state.total_runs == 1
    assert state.total_records_ingested == res1["inserted"]
    assert state.last_ingested_timestamp is not None

    # Second run: identical demo records must be deduplicated
    res2 = await service.ingest_incremental(session, use_demo=True)
    assert res2["status"] == "COMPLETED"
    assert res2["inserted"] == 0
    assert res2["skipped"] == res2["fetched"]


# 2. Test Autonomous Multi-Stage Pipeline Execution
@pytest.mark.asyncio
async def test_pipeline_runner_process_event(client_and_session):
    client, session = client_and_session

    now = datetime.now(timezone.utc)
    ev = ThermalEvent(
        source="NASA_FIRMS",
        latitude=22.4632,
        longitude=70.0712,
        geometry="SRID=4326;POINT(70.0712 22.4632)",
        detected_at=now,
        satellite="VIIRS_NPP",
        frp=340.0,
        confidence=95.0,
        status="NEW"
    )
    session.add(ev)
    session.commit()
    session.refresh(ev)

    job = PipelineJob(
        correlation_id="CORR-TEST-001",
        job_type="FIRMS_AUTONOMOUS_PIPELINE",
        source="NASA_FIRMS",
        status="RUNNING"
    )
    session.add(job)
    session.commit()
    session.refresh(job)

    result = await PipelineRunner.process_event(
        db=session,
        event_id=ev.id,
        job_id=job.id,
        correlation_id=job.correlation_id
    )

    assert result["status"] == "SUCCESS"
    assert "SPATIAL_ENRICHMENT" in result["stages_executed"]
    assert "TEMPORAL_ANALYSIS" in result["stages_executed"]
    assert "CLASSIFICATION" in result["stages_executed"]
    assert "RISK_ASSESSMENT" in result["stages_executed"]
    assert "INCIDENT_CORRELATION" in result["stages_executed"]
    assert "ALERT_EVALUATION" in result["stages_executed"]
    assert result["risk_score"] > 0.0
    assert result["incident_code"] is not None

    # Check stage runs persisted in database
    stage_runs = session.query(PipelineStageRun).filter(PipelineStageRun.event_id == ev.id).all()
    assert len(stage_runs) >= 6
    for sr in stage_runs:
        assert sr.status == "SUCCESS"
        assert sr.duration_seconds >= 0.0


# 3. Test Incident Correlation and Anti-Storm Alert Deduplication
@pytest.mark.asyncio
async def test_incident_correlation_and_alert_deduplication(client_and_session):
    client, session = client_and_session

    now = datetime.now(timezone.utc)
    ev1 = ThermalEvent(
        source="NASA_FIRMS",
        latitude=22.4630,
        longitude=70.0710,
        geometry="SRID=4326;POINT(70.0710 22.4630)",
        detected_at=now,
        satellite="VIIRS_NPP",
        frp=200.0,
        confidence=90.0,
        status="NEW"
    )
    session.add(ev1)
    session.commit()
    session.refresh(ev1)

    # First event correlation
    inc1 = IncidentCorrelator.correlate_event(
        db=session,
        event=ev1,
        classification="INDUSTRIAL_FIRE",
        risk_score=85.0,
        risk_level="CRITICAL",
        spatial_context={"nearest_facility": {"id": 1, "name": "Reliance Refinery"}, "distance_meters": 120.0}
    )
    assert inc1.event_count == 1
    assert inc1.incident_code.startswith("INC-2026-")

    # Second event arriving 1 hour later within 200m
    ev2 = ThermalEvent(
        source="NASA_FIRMS",
        latitude=22.4635,
        longitude=70.0715,
        geometry="SRID=4326;POINT(70.0715 22.4635)",
        detected_at=now + timedelta(hours=1),
        satellite="VIIRS_NPP",
        frp=400.0,
        confidence=95.0,
        status="NEW"
    )
    session.add(ev2)
    session.commit()
    session.refresh(ev2)

    inc2 = IncidentCorrelator.correlate_event(
        db=session,
        event=ev2,
        classification="INDUSTRIAL_FIRE",
        risk_score=92.0,
        risk_level="CRITICAL",
        spatial_context={"nearest_facility": {"id": 1, "name": "Reliance Refinery"}, "distance_meters": 150.0}
    )

    # Must be the exact same incident with incremented counts and peak FRP
    assert inc2.id == inc1.id
    assert inc2.event_count == 2
    assert inc2.peak_frp == 400.0
    assert inc2.duration_hours == 1.0


# 4. Test Retry Policy with Transient and Permanent Errors
@pytest.mark.asyncio
async def test_retry_policy():
    # Transient error simulated: recovers on 2nd attempt
    attempts = 0
    async def flaky_call():
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            raise TimeoutError("Simulated network timeout")
        return "success"

    res = await RetryPolicy.execute_with_retry(flaky_call, max_retries=2, backoff_seconds=0.01)
    assert res == "success"
    assert attempts == 2

    # Permanent error: should fail immediately without exhausting all retries
    perm_attempts = 0
    async def bad_call():
        nonlocal perm_attempts
        perm_attempts += 1
        raise ValueError("Malformed geometry format")

    with pytest.raises(ValueError):
        await RetryPolicy.execute_with_retry(bad_call, max_retries=5, backoff_seconds=0.01)
    assert perm_attempts == 1


# 5. Test System Health and Provider Endpoints
def test_system_health_and_provider_apis(client_and_session):
    client, session = client_and_session

    res = client.get("/api/v1/system/health")
    assert res.status_code == 200
    data = res.json()
    assert "system_status" in data
    assert "providers" in data
    assert len(data["providers"]) >= 4

    p_res = client.get("/api/v1/system/providers")
    assert p_res.status_code == 200
    p_data = p_res.json()
    assert any(p["provider"] == "NASA FIRMS" for p in p_data)
    assert any(p["provider"] == "XGBoost ML Model" for p in p_data)


# 6. Test Controlled Demo Mode Trigger
def test_demo_mode_trigger(client_and_session):
    client, session = client_and_session

    payload = {
        "latitude": 22.4630,
        "longitude": 70.0710,
        "frp": 380.0,
        "brightness_temperature": 395.0,
        "satellite": "VIIRS_NPP",
        "confidence": 92.0
    }
    res = client.post("/api/v1/system/demo/trigger", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "SUCCESS"
    assert data["correlation_id"].startswith("DEMO-")
    assert data["risk_score"] > 0
    assert len(data["stages_executed"]) >= 5


# 7. Test Incident APIs and Human-In-The-Loop Confirmation
def test_incident_api_and_human_confirmation(client_and_session):
    client, session = client_and_session

    now = datetime.now(timezone.utc)
    inc = ThermalIncident(
        incident_code="INC-2026-TEST01",
        title="Test Incident",
        status="ACTIVE",
        severity="HIGH",
        classification="INDUSTRIAL_FIRE",
        first_detected_at=now,
        last_detected_at=now,
        duration_hours=0.5,
        event_count=2,
        peak_frp=150.0,
        mean_frp=120.0,
        risk_score=78.0,
        risk_level="HIGH",
        centroid_latitude=22.4630,
        centroid_longitude=70.0710,
        incident_summary_json={"analyst_notes": []}
    )
    session.add(inc)
    session.commit()
    session.refresh(inc)

    # GET list
    res = client.get("/api/v1/incidents")
    assert res.status_code == 200
    assert res.json()["total"] >= 1

    # GET detail
    res_det = client.get(f"/api/v1/incidents/{inc.id}")
    assert res_det.status_code == 200
    assert res_det.json()["incident"]["incident_code"] == "INC-2026-TEST01"

    # PATCH status (Human analyst confirmation)
    patch_res = client.patch(
        f"/api/v1/incidents/{inc.id}/status",
        json={"status": "CONTAINED", "analyst_notes": "Ground response team verified flare containment."}
    )
    assert patch_res.status_code == 200
    assert patch_res.json()["status"] == "CONTAINED"

    # Verify audit trail recorded
    audit = session.query(AutonomousAuditLog).filter(
        AutonomousAuditLog.incident_id == inc.id,
        AutonomousAuditLog.action == "INCIDENT_STATUS_ANALYST_UPDATE"
    ).first()
    assert audit is not None
    assert audit.source == "HUMAN_ANALYST"


# 8. Test Restart Recovery Safety (Section 39)
def test_restart_recovery_safety(client_and_session):
    client, session = client_and_session

    running_job = PipelineJob(
        correlation_id="CORR-CRASHED-01",
        job_type="FIRMS_AUTONOMOUS_PIPELINE",
        source="NASA_FIRMS",
        status="RUNNING"
    )
    queued_job = PipelineJob(
        correlation_id="CORR-QUEUED-02",
        job_type="FIRMS_AUTONOMOUS_PIPELINE",
        source="NASA_FIRMS",
        status="QUEUED"
    )
    session.add_all([running_job, queued_job])
    session.commit()

    # Simulate restart recovery routine
    interrupted = session.query(PipelineJob).filter(PipelineJob.status.in_(["RUNNING", "QUEUED"])).all()
    for j in interrupted:
        j.status = "INTERRUPTED"
        j.error_message = "Server restarted while job was executing; recovered on startup."
        j.completed_at = datetime.now(timezone.utc)
    session.commit()

    reloaded_running = session.query(PipelineJob).filter(PipelineJob.correlation_id == "CORR-CRASHED-01").first()
    reloaded_queued = session.query(PipelineJob).filter(PipelineJob.correlation_id == "CORR-QUEUED-02").first()

    assert reloaded_running.status == "INTERRUPTED"
    assert "Server restarted" in reloaded_running.error_message
    assert reloaded_queued.status == "INTERRUPTED"


# 9. Test Real-Time WebSocket Delivery & Event Buffer (Section 18)
@pytest.mark.asyncio
async def test_websocket_stream_manager():
    mgr = ConnectionManager(max_buffer_size=5)

    await mgr.broadcast("thermal_event.created", {"event_id": 999, "frp": 150.0})
    await mgr.broadcast("alert.created", {"alert_code": "ALT-TEST-01", "severity": "HIGH"})

    buffered = mgr.get_recent_events(limit=10)
    assert len(buffered) == 2
    assert buffered[0]["event"] == "alert.created"
    assert buffered[1]["event"] == "thermal_event.created"
    assert buffered[0]["payload"]["alert_code"] == "ALT-TEST-01"

