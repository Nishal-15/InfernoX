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

    # 1. Monitored Facilities
    fac1 = Facility(
        id=1,
        osm_id="way/101",
        name="Apex Refinery Complex",
        facility_type="refinery",
        operator="Apex Petroleum",
        latitude=28.6139,
        longitude=77.2090
    )
    fac2 = Facility(
        id=2,
        osm_id="way/102",
        name="Bayside Gas Processing",
        facility_type="gas_flare",
        operator="Bayside Energy",
        latitude=28.6500,
        longitude=77.2500
    )
    session.add_all([fac1, fac2])
    session.commit()

    # 2. Thermal Events
    ev1 = ThermalEvent(
        id=1,
        source="NASA_FIRMS",
        latitude=28.6140,
        longitude=77.2092,
        detected_at=now - timedelta(days=2),
        satellite="VIIRS_SNPP",
        instrument="VIIRS",
        confidence=95.0,
        frp=120.0,
        status="ACTIVE"
    )
    ev2 = ThermalEvent(
        id=2,
        source="NASA_FIRMS",
        latitude=28.6142,
        longitude=77.2095,
        detected_at=now - timedelta(days=1),
        satellite="VIIRS_NOAA20",
        instrument="VIIRS",
        confidence=90.0,
        frp=65.0,
        status="ACTIVE"
    )
    ev3 = ThermalEvent(
        id=3,
        source="NASA_FIRMS",
        latitude=28.6510,
        longitude=77.2510,
        detected_at=now - timedelta(hours=6),
        satellite="MODIS_TERRA",
        instrument="MODIS",
        confidence=80.0,
        frp=35.0,
        status="ACTIVE"
    )
    session.add_all([ev1, ev2, ev3])
    session.commit()

    # 3. AI Event Assessments
    ass1 = EventAssessment(
        id=1,
        event_id=1,
        classification="INDUSTRIAL_FLARE",
        confidence_score=0.95,
        priority_score=88.0,
        priority_level="CRITICAL"
    )
    ass2 = EventAssessment(
        id=2,
        event_id=2,
        classification="INDUSTRIAL_FLARE",
        confidence_score=0.91,
        priority_score=72.0,
        priority_level="HIGH"
    )
    ass3 = EventAssessment(
        id=3,
        event_id=3,
        classification="WILDFIRE",
        confidence_score=0.82,
        priority_score=45.0,
        priority_level="MEDIUM"
    )
    session.add_all([ass1, ass2, ass3])
    session.commit()

    # 4. Risk Assessments
    risk1 = RiskAssessment(
        id=1,
        event_id=1,
        risk_score=88.0,
        risk_level="CRITICAL",
        risk_model_version="risk-v1",
        breakdown_json={"intensity": 95.0, "classification": 80.0},
        input_snapshot_json={"frp": 120.0},
        calculated_at=now - timedelta(days=2)
    )
    risk2 = RiskAssessment(
        id=2,
        event_id=2,
        risk_score=72.0,
        risk_level="HIGH",
        risk_model_version="risk-v1",
        breakdown_json={"intensity": 70.0, "classification": 75.0},
        input_snapshot_json={"frp": 65.0},
        calculated_at=now - timedelta(days=1)
    )
    session.add_all([risk1, risk2])
    session.commit()

    # 5. Alerts
    alt1 = Alert(
        id=1,
        alert_code="ALT-2026-000001",
        event_id=1,
        severity="CRITICAL",
        title="Critical Industrial Thermal Flare",
        message="FRP excursion detected at Apex Refinery",
        status="RESOLVED",
        incident_payload_json={"frp": 120.0},
        acknowledged_by="analyst_1",
        acknowledged_at=now - timedelta(days=2, hours=-1),
        resolved_by="analyst_1",
        resolved_at=now - timedelta(days=2, hours=-2),
        created_at=now - timedelta(days=2)
    )
    alt2 = Alert(
        id=2,
        alert_code="ALT-2026-000002",
        event_id=2,
        severity="HIGH",
        title="High Heat Alert",
        message="Persistent flaring activity",
        status="ACKNOWLEDGED",
        incident_payload_json={"frp": 65.0},
        acknowledged_by="analyst_2",
        acknowledged_at=now - timedelta(days=1, hours=-1),
        created_at=now - timedelta(days=1)
    )
    session.add_all([alt1, alt2])
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


def test_analytics_overview(client_and_session):
    client, _ = client_and_session
    response = client.get("/api/v1/analytics/overview?range_preset=30d")
    assert response.status_code == 200
    data = response.json()
    assert data["total_events"] == 3
    assert data["max_frp"] == 120.0
    assert data["critical_risk_count"] == 1
    assert data["high_risk_count"] == 1
    assert data["total_alerts"] == 2


def test_analytics_timeseries(client_and_session):
    client, _ = client_and_session
    response = client.get("/api/v1/analytics/timeseries?interval=day&range_preset=30d")
    assert response.status_code == 200
    data = response.json()
    assert data["interval"] == "day"
    assert "points" in data
    assert len(data["points"]) > 0
    p = data["points"][0]
    assert "timestamp" in p
    assert "event_count" in p
    assert "avg_frp" in p


def test_analytics_classifications(client_and_session):
    client, _ = client_and_session
    response = client.get("/api/v1/analytics/classifications?range_preset=30d")
    assert response.status_code == 200
    data = response.json()
    assert data["total_classified"] == 3
    assert len(data["items"]) >= 1
    item = data["items"][0]
    assert "classification" in item
    assert "count" in item
    assert "percentage" in item


def test_analytics_risk(client_and_session):
    client, _ = client_and_session
    response = client.get("/api/v1/analytics/risk?range_preset=30d")
    assert response.status_code == 200
    data = response.json()
    assert "distribution" in data
    assert data["distribution"]["CRITICAL"] == 1
    assert data["distribution"]["HIGH"] == 1
    assert data["avg_score"] > 70


def test_analytics_alerts(client_and_session):
    client, _ = client_and_session
    response = client.get("/api/v1/analytics/alerts?range_preset=30d")
    assert response.status_code == 200
    data = response.json()
    assert data["total_alerts"] == 2
    assert "by_severity" in data
    assert "by_status" in data
    assert data["by_severity"]["CRITICAL"] == 1
    assert data["by_status"]["RESOLVED"] == 1


def test_analytics_facilities(client_and_session):
    client, _ = client_and_session
    response = client.get("/api/v1/analytics/facilities?limit=10")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 1
    fac = data[0]
    assert "facility_id" in fac
    assert "name" in fac
    assert "total_nearby_events" in fac


def test_analytics_geospatial(client_and_session):
    client, _ = client_and_session
    response = client.get("/api/v1/analytics/geospatial?resolution_deg=0.25&range_preset=30d")
    assert response.status_code == 200
    data = response.json()
    assert data["cell_count"] > 0
    assert "geojson" in data
    assert data["geojson"]["type"] == "FeatureCollection"


def test_analytics_comparison(client_and_session):
    client, _ = client_and_session
    response = client.get("/api/v1/analytics/comparison?comparison_type=FACILITY&id_a=1&id_b=2")
    assert response.status_code == 200
    data = response.json()
    assert data["comparison_type"] == "FACILITY"
    assert "target_a" in data
    assert "target_b" in data
    assert "delta_metrics" in data


def test_analytics_trends(client_and_session):
    client, _ = client_and_session
    response = client.get("/api/v1/analytics/trends?range_preset=30d")
    assert response.status_code == 200
    data = response.json()
    assert "event_volume" in data
    assert "state" in data["event_volume"]
    assert data["event_volume"]["state"] in ["STABLE", "INCREASING", "DECREASING", "VOLATILE", "EMERGING"]


def test_analytics_anomalies(client_and_session):
    client, _ = client_and_session
    response = client.get("/api/v1/analytics/anomalies?limit=10&range_preset=30d")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
