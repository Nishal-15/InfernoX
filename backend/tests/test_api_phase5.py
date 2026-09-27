import pytest
from fastapi.testclient import TestClient
from datetime import datetime, timezone, timedelta
from app.main import app
from app.api.deps import get_db
from sqlalchemy import create_engine, text
from sqlalchemy.pool import StaticPool
from sqlalchemy.orm import sessionmaker
from app.models.thermal_event import ThermalEvent
from app.models.facility import Facility
from app.models.ai_models import EventAssessment, AnalystReview
from app.models.ingestion_job import IngestionJob

@pytest.fixture
def client_with_db():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool
    )
    from sqlalchemy import event

    @event.listens_for(engine, "connect")
    def register_gis_functions(dbapi_connection, connection_record):
        dbapi_connection.create_function("GeomFromEWKT", 1, lambda x: x)
        dbapi_connection.create_function("RecoverGeometryColumn", 5, lambda a, b, c, d, e: 1)
        dbapi_connection.create_function("AsEWKT", 1, lambda x: x)
        dbapi_connection.create_function("AsEWKB", 1, lambda x: b"\x01\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00" if x else None)
        dbapi_connection.create_function("AsBinary", 1, lambda x: b"\x01\x01\x00\x00\x00" if x else None)
        dbapi_connection.create_function("ST_DWithin", 3, lambda a, b, c: 1)
        dbapi_connection.create_function("ST_Distance", 2, lambda a, b: 150.0)
        dbapi_connection.create_function("ST_GeomFromEWKT", 1, lambda x: x)

    with engine.connect() as conn:
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
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS facilities (
                id INTEGER PRIMARY KEY,
                osm_id VARCHAR UNIQUE,
                name VARCHAR,
                facility_type VARCHAR,
                operator VARCHAR,
                latitude FLOAT,
                longitude FLOAT,
                source VARCHAR,
                tags TEXT,
                geometry TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """))
        conn.commit()

    EventAssessment.__table__.create(bind=engine, checkfirst=True)
    AnalystReview.__table__.create(bind=engine, checkfirst=True)
    IngestionJob.__table__.create(bind=engine, checkfirst=True)
    
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = TestingSessionLocal()

    # Seed facility
    fac = Facility(
        id=1,
        osm_id="way/12345",
        name="Jamnagar Refinery Complex",
        facility_type="oil_refinery",
        operator="Reliance Industries",
        latitude=22.35,
        longitude=69.85,
        source="osm",
        geometry="POINT(69.85 22.35)"
    )
    db.add(fac)

    # Seed thermal events
    now = datetime.now(timezone.utc)
    ev1 = ThermalEvent(
        id=101,
        source="NASA_FIRMS",
        latitude=22.352,
        longitude=69.853,
        geometry="POINT(69.853 22.352)",
        detected_at=now - timedelta(days=2),
        satellite="VIIRS_SNPP",
        confidence=95.0,
        frp=68.5,
        brightness_temperature=345.2,
        status="NEW"
    )
    ev2 = ThermalEvent(
        id=102,
        source="NASA_FIRMS",
        latitude=22.354,
        longitude=69.851,
        geometry="POINT(69.851 22.354)",
        detected_at=now - timedelta(days=1),
        satellite="VIIRS_SNPP",
        confidence=92.0,
        frp=82.0,
        brightness_temperature=355.0,
        status="NEW"
    )
    ev3 = ThermalEvent(
        id=103,
        source="NASA_FIRMS",
        latitude=24.50,
        longitude=75.20,
        geometry="POINT(75.20 24.50)",
        detected_at=now,
        satellite="MODIS",
        confidence=70.0,
        frp=15.0,
        brightness_temperature=312.0,
        status="NEW"
    )
    db.add_all([ev1, ev2, ev3])
    db.commit()

    def override_get_db():
        session = TestingSessionLocal()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.clear()
    db.close()

def test_consolidated_investigation_endpoint(client_with_db):
    res = client_with_db.get("/api/v1/events/101/investigation")
    assert res.status_code == 200
    data = res.json()
    assert data["event"]["id"] == 101
    assert data["event"]["event_code"] == "INF-2026-000101"
    assert "classification" in data
    assert "temporal_analysis" in data
    assert "nearby_facilities" in data
    assert "satellite_evidence" in data
    assert "land_cover" in data
    assert "historical_events" in data
    assert "provenance" in data
    assert data["provenance"]["thermal_source"].startswith("NASA FIRMS")

def test_event_timeline_endpoint(client_with_db):
    res = client_with_db.get("/api/v1/events/101/timeline")
    assert res.status_code == 200
    data = res.json()
    assert data["event_id"] == 101
    assert "timeline" in data
    assert len(data["timeline"]) >= 1

def test_event_evidence_endpoint(client_with_db):
    res = client_with_db.get("/api/v1/events/101/evidence")
    assert res.status_code == 200
    data = res.json()
    assert "classification" in data
    assert "evidence_factors" in data
    assert "satellite_evidence" in data
    assert "land_cover" in data

def test_nearby_facilities_endpoint(client_with_db):
    res = client_with_db.get("/api/v1/events/101/nearby-facilities?radius_km=5.0")
    assert res.status_code == 200
    data = res.json()
    assert data["event_id"] == 101
    assert "facilities" in data
    assert len(data["facilities"]) >= 1
    assert data["facilities"][0]["name"] == "Jamnagar Refinery Complex"

def test_event_status_transition_enforcement(client_with_db):
    # Invalid transition: NEW directly to CLOSED
    bad_res = client_with_db.patch("/api/v1/events/101/status", json={"status": "CLOSED", "reason": "Attempt direct close"})
    assert bad_res.status_code == 400

    # Valid step 1: NEW -> INVESTIGATING
    res1 = client_with_db.patch("/api/v1/events/101/status", json={"status": "INVESTIGATING", "reason": "Analyst inspecting 3D view"})
    assert res1.status_code == 200
    assert res1.json()["status"] == "INVESTIGATING"

    # Valid step 2: INVESTIGATING -> CONFIRMED
    res2 = client_with_db.patch("/api/v1/events/101/status", json={"status": "CONFIRMED", "reason": "Ground truth verified"})
    assert res2.status_code == 200
    assert res2.json()["status"] == "CONFIRMED"

    # Valid step 3: CONFIRMED -> CLOSED
    res3 = client_with_db.patch("/api/v1/events/101/status", json={"status": "CLOSED", "reason": "Incident mitigated"})
    assert res3.status_code == 200
    assert res3.json()["status"] == "CLOSED"

def test_event_compare_endpoint(client_with_db):
    res = client_with_db.get("/api/v1/events/compare?id1=101&id2=103")
    assert res.status_code == 200
    data = res.json()
    assert "event_a" in data
    assert "event_b" in data
    assert data["event_a"]["id"] == 101
    assert data["event_b"]["id"] == 103
    assert "comparison_metrics" in data

def test_facility_investigation_and_timeline(client_with_db):
    inv_res = client_with_db.get("/api/v1/facilities/1/investigation")
    assert inv_res.status_code == 200
    inv_data = inv_res.json()
    assert inv_data["facility"]["name"] == "Jamnagar Refinery Complex"
    assert inv_data["metrics"]["total_thermal_events"] >= 2
    assert "risk_level" in inv_data["metrics"]

    time_res = client_with_db.get("/api/v1/facilities/1/timeline?days=30")
    assert time_res.status_code == 200
    time_data = time_res.json()
    assert time_data["facility_id"] == 1
    assert "weekly_activity" in time_data
    assert len(time_data["weekly_activity"]) >= 4

def test_global_search_multi_entity(client_with_db):
    # Search by facility name
    res_fac = client_with_db.get("/api/v1/search?query=Jamnagar")
    assert res_fac.status_code == 200
    data_fac = res_fac.json()
    assert len(data_fac["facilities"]) >= 1
    assert data_fac["facilities"][0]["name"] == "Jamnagar Refinery Complex"

    # Search by event ID
    res_ev = client_with_db.get("/api/v1/search?query=101")
    assert res_ev.status_code == 200
    data_ev = res_ev.json()
    assert any(e["id"] == 101 for e in data_ev["events"])
