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
from app.models.ai_models import EventAssessment, AnalystReview
from app.models.risk_alert import RiskAssessment, Alert, AlertRule
from app.models.reporting import GeneratedReport
from app.services.reporting.report_provenance import ReportProvenanceBuilder


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
                status VARCHAR DEFAULT 'NEW',
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            );
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
                source VARCHAR DEFAULT 'OpenStreetMap',
                tags TEXT,
                geometry TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            );
        """))
        conn.commit()

    EventAssessment.__table__.create(bind=test_engine, checkfirst=True)
    AnalystReview.__table__.create(bind=test_engine, checkfirst=True)
    RiskAssessment.__table__.create(bind=test_engine, checkfirst=True)
    AlertRule.__table__.create(bind=test_engine, checkfirst=True)
    Alert.__table__.create(bind=test_engine, checkfirst=True)
    GeneratedReport.__table__.create(bind=test_engine, checkfirst=True)

    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)
    session = TestingSessionLocal()

    now = datetime.now(timezone.utc)

    fac = Facility(
        id=1,
        osm_id="way/201",
        name="Gulf Petrochemical Refinery",
        facility_type="refinery",
        operator="Gulf Petrochem",
        latitude=29.3759,
        longitude=47.9774
    )
    session.add(fac)
    session.commit()

    ev = ThermalEvent(
        id=1,
        source="NASA_FIRMS",
        latitude=29.3762,
        longitude=47.9780,
        detected_at=now - timedelta(hours=2),
        satellite="VIIRS_SNPP",
        instrument="VIIRS",
        confidence=98.0,
        frp=145.0,
        status="ACTIVE"
    )
    session.add(ev)
    session.commit()

    ass = EventAssessment(
        id=1,
        event_id=1,
        classification="INDUSTRIAL_FLARE",
        confidence_score=0.96,
        priority_score=92.0,
        priority_level="CRITICAL"
    )
    session.add(ass)
    session.commit()

    risk = RiskAssessment(
        id=1,
        event_id=1,
        risk_score=92.0,
        risk_level="CRITICAL",
        risk_model_version="risk-v1",
        breakdown_json={"intensity": 98.0, "classification": 85.0},
        input_snapshot_json={"frp": 145.0},
        calculated_at=now - timedelta(hours=2)
    )
    session.add(risk)
    session.commit()

    alt = Alert(
        id=1,
        alert_code="ALT-2026-000099",
        event_id=1,
        severity="CRITICAL",
        title="Critical Petrochemical Excursion",
        message="Radiative heat surge detected at Gulf Refinery",
        status="ACKNOWLEDGED",
        incident_payload_json={"frp": 145.0},
        acknowledged_by="lead_analyst",
        acknowledged_at=now - timedelta(hours=1),
        created_at=now - timedelta(hours=2)
    )
    session.add(alt)
    session.commit()

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


def test_get_incident_report(client_and_session):
    client, _ = client_and_session
    response = client.get("/api/v1/reports/incident/1")
    assert response.status_code == 200
    data = response.json()
    assert "metadata" in data
    assert data["metadata"]["report_type"] == "INCIDENT"
    assert "summary" in data
    assert "sections" in data
    assert "provenance" in data
    assert data["provenance"]["model_version"] == "InfernoX-XGB-v1.0"
    assert data["provenance"]["risk_model_version"] == "risk-v1"


def test_get_facility_report(client_and_session):
    client, _ = client_and_session
    response = client.get("/api/v1/reports/facility/1?days=90")
    assert response.status_code == 200
    data = response.json()
    assert data["metadata"]["report_type"] == "FACILITY"
    assert "Gulf Petrochemical Refinery" in data["metadata"]["title"]
    assert "summary" in data
    assert "sections" in data


def test_get_executive_report(client_and_session):
    client, _ = client_and_session
    response = client.get("/api/v1/reports/executive")
    assert response.status_code == 200
    data = response.json()
    assert data["metadata"]["report_type"] == "EXECUTIVE"
    assert "summary" in data


def test_get_regional_report(client_and_session):
    client, _ = client_and_session
    response = client.get("/api/v1/reports/regional?region_name=Persian Gulf Corridor")
    assert response.status_code == 200
    data = response.json()
    assert data["metadata"]["report_type"] == "REGIONAL"
    assert "Persian Gulf Corridor" in data["metadata"]["title"]


def test_generate_pdf_report(client_and_session):
    client, _ = client_and_session
    payload = {
        "report_type": "INCIDENT",
        "target_id": "1",
        "format": "PDF"
    }
    response = client.post("/api/v1/reports/generate", json=payload)
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert response.content.startswith(b"%PDF")
    assert len(response.content) > 500


def test_generate_csv_report(client_and_session):
    client, _ = client_and_session
    payload = {
        "report_type": "INCIDENT",
        "target_id": "1",
        "format": "CSV"
    }
    response = client.post("/api/v1/reports/generate", json=payload)
    assert response.status_code == 200
    assert "text/csv" in response.headers["content-type"]
    content_str = response.content.decode("utf-8")
    assert "Report ID" in content_str
    assert "INCIDENT" in content_str


def test_generate_geojson_report(client_and_session):
    client, _ = client_and_session
    payload = {
        "report_type": "INCIDENT",
        "target_id": "1",
        "format": "GEOJSON"
    }
    response = client.post("/api/v1/reports/generate", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["type"] == "FeatureCollection"
    assert len(data["features"]) > 0


def test_report_history_audit(client_and_session):
    client, _ = client_and_session
    # First generate a report to store in history
    client.post("/api/v1/reports/generate", json={
        "report_type": "INCIDENT",
        "target_id": "1",
        "format": "JSON"
    })

    # Retrieve history
    response = client.get("/api/v1/reports/history")
    assert response.status_code == 200
    history = response.json()
    assert len(history) >= 1
    assert history[0]["report_type"] == "INCIDENT"


def test_provenance_builder():
    provenance = ReportProvenanceBuilder.get_provenance()
    assert provenance.model_version == "InfernoX-XGB-v1.0"
    assert provenance.risk_model_version == "risk-v1"
    assert provenance.analytics_version == "analytics-v1"
    assert len(provenance.data_sources) >= 4
    assert "NASA FIRMS" in provenance.data_sources[0]
