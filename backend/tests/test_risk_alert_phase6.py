import pytest
from datetime import datetime, timezone, timedelta
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.api.deps import get_db
from app.db.database import Base
from app.models.thermal_event import ThermalEvent
from app.models.facility import Facility
from app.models.risk_alert import (
    RiskAssessment,
    AlertRule,
    Alert,
    AlertAuditLog,
    ResponseContact,
    NotificationPreference,
    NotificationLog
)
from app.services.risk.engine import RiskEngine
from app.services.alert.engine import AlertEngine
from app.services.routing.service import ResponseRoutingService
from app.services.notification.in_app import InAppNotificationProvider
from app.services.notification.stubs import EmailNotificationProvider, SMSNotificationProvider, WebhookNotificationProvider


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

    RiskAssessment.__table__.create(bind=test_engine, checkfirst=True)
    AlertRule.__table__.create(bind=test_engine, checkfirst=True)
    Alert.__table__.create(bind=test_engine, checkfirst=True)
    AlertAuditLog.__table__.create(bind=test_engine, checkfirst=True)
    ResponseContact.__table__.create(bind=test_engine, checkfirst=True)
    NotificationPreference.__table__.create(bind=test_engine, checkfirst=True)
    NotificationLog.__table__.create(bind=test_engine, checkfirst=True)

    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)
    db = TestingSessionLocal()
    now = datetime.now(timezone.utc)

    # Seed events
    ev1 = ThermalEvent(
        id=201,
        source="NASA_FIRMS",
        latitude=22.30,
        longitude=69.80,
        detected_at=now,
        satellite="VIIRS_SNPP",
        confidence=98.0,
        frp=120.0,
        brightness_temperature=360.0,
        status="NEW"
    )
    ev2 = ThermalEvent(
        id=202,
        source="NASA_FIRMS",
        latitude=24.50,
        longitude=75.20,
        detected_at=now,
        satellite="MODIS",
        confidence=60.0,
        frp=12.0,
        brightness_temperature=310.0,
        status="NEW"
    )
    db.add_all([ev1, ev2])

    # Seed rules
    AlertEngine.seed_default_rules(db)

    # Seed contact
    contact = ResponseContact(
        organization_name="Gujarat State Fire & Rescue Command",
        department_type="FIRE_EMERGENCY",
        jurisdiction="Gujarat",
        contact_type="EMAIL",
        contact_value="cmd@gujaratfire.gov.in",
        enabled=True,
        verified=True,
        last_verified_at=now,
        created_at=now,
        updated_at=now
    )
    db.add(contact)
    db.commit()

    def override_get_db():
        session = TestingSessionLocal()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as client:
        yield client, db

    app.dependency_overrides.clear()
    db.close()


# ==========================================
# 1. Risk Engine Tests
# ==========================================

def test_risk_engine_critical_industrial_fire():
    assessment = RiskEngine.evaluate_risk(
        features={"frp": 160.0, "model_probability": 0.95},
        classification="INDUSTRIAL_FIRE",
        spatial_context={"distance_meters": 150.0, "nearest_facility": {"name": "Reliance Jamnagar Refinery", "facility_type": "oil_refinery"}},
        temporal_data={"status": "ABNORMAL", "frp_spike_ratio": 3.2, "active_days": 10},
        satellite_data={"available": True, "indices": {"burn_scar_indicator": True, "swir_nir_ratio": 2.1}}
    )

    assert assessment["risk_score"] >= 75.0
    assert assessment["risk_level"] == "CRITICAL"
    assert assessment["risk_model_version"] == "risk-v1"
    assert len(assessment["breakdown"]["factors"]) == 5


def test_risk_engine_low_anomaly():
    assessment = RiskEngine.evaluate_risk(
        features={"frp": 8.0, "model_probability": 0.5},
        classification="AGRICULTURAL_BURNING",
        spatial_context={"distance_meters": 12000.0},
        temporal_data={"status": "NEW", "active_days": 1},
        satellite_data={"available": False}
    )

    assert assessment["risk_score"] < 25.0
    assert assessment["risk_level"] == "LOW"


def test_risk_engine_missing_features_tolerance():
    # Calling evaluate_risk with completely empty inputs should return valid LOW/MODERATE score without throwing
    assessment = RiskEngine.evaluate_risk()
    assert isinstance(assessment["risk_score"], float)
    assert assessment["risk_level"] in ["LOW", "MODERATE"]
    assert assessment["breakdown"] is not None


def test_risk_engine_persistence(client_and_session):
    _, db = client_and_session
    rec = RiskEngine.record_risk_assessment(
        db=db,
        event_id=201,
        features={"frp": 110.0},
        classification="INDUSTRIAL_FIRE"
    )
    assert rec.id is not None
    assert rec.event_id == 201
    assert rec.risk_level in ["HIGH", "CRITICAL"]

    # Verify queryable from DB
    persisted = db.query(RiskAssessment).filter(RiskAssessment.id == rec.id).first()
    assert persisted is not None
    assert persisted.risk_score == rec.risk_score


# ==========================================
# 2. Alert Engine & Rule Evaluation Tests
# ==========================================

def test_alert_rule_matching_and_deduplication(client_and_session):
    _, db = client_and_session
    event = db.query(ThermalEvent).filter(ThermalEvent.id == 201).first()

    risk_data = {
        "risk_score": 85.0,
        "risk_level": "CRITICAL",
        "risk_model_version": "risk-v1"
    }

    # 1. Evaluate alerts
    created = AlertEngine.evaluate_event_alerts(
        db=db,
        event=event,
        risk_data=risk_data,
        classification="INDUSTRIAL_FIRE",
        spatial_context={"nearest_facility": {"name": "Jamnagar", "facility_type": "refinery"}, "distance_meters": 200.0}
    )

    assert len(created) >= 1
    alert = created[0]
    assert alert.severity in ["CRITICAL", "HIGH"]
    assert alert.status == "NEW"
    assert alert.alert_code.startswith("ALT-2026-")

    # 2. Deduplication check: re-evaluating immediately should NOT create duplicate alert
    re_evaluated = AlertEngine.evaluate_event_alerts(
        db=db,
        event=event,
        risk_data=risk_data,
        classification="INDUSTRIAL_FIRE",
        spatial_context={"nearest_facility": {"name": "Jamnagar", "facility_type": "refinery"}, "distance_meters": 200.0}
    )
    assert len(re_evaluated) == 0


def test_disabled_rule_ignored(client_and_session):
    _, db = client_and_session
    rule = db.query(AlertRule).filter(AlertRule.name == "CRITICAL_INDUSTRIAL_FIRE").first()
    rule.enabled = False
    db.commit()

    context = {
        "risk_score": 90.0,
        "classification": "INDUSTRIAL_FIRE"
    }
    assert not AlertEngine.match_rule(rule, context)


# ==========================================
# 3. State Machine Transitions & Audit Trail
# ==========================================

def test_alert_lifecycle_valid_flow(client_and_session):
    _, db = client_and_session
    alert = Alert(
        alert_code="ALT-TEST-001",
        event_id=201,
        severity="HIGH",
        title="Test Anomaly Alert",
        message="Testing lifecycle transitions",
        status="NEW",
        incident_payload_json={"test": True}
    )
    db.add(alert)
    db.commit()
    db.refresh(alert)

    # NEW -> ACKNOWLEDGED
    a1 = AlertEngine.transition_status(db, alert.id, "ACKNOWLEDGED", actor="analyst_1", comment="Acknowledged receipt")
    assert a1.status == "ACKNOWLEDGED"
    assert a1.acknowledged_by == "analyst_1"
    assert a1.acknowledged_at is not None

    # ACKNOWLEDGED -> INVESTIGATING
    a2 = AlertEngine.transition_status(db, alert.id, "INVESTIGATING", actor="analyst_1")
    assert a2.status == "INVESTIGATING"

    # INVESTIGATING -> RESOLVED
    a3 = AlertEngine.transition_status(db, alert.id, "RESOLVED", actor="analyst_1", comment="Fire suppressed by plant crew")
    assert a3.status == "RESOLVED"
    assert a3.resolved_by == "analyst_1"
    assert a3.resolved_at is not None

    # Verify audit trail
    logs = db.query(AlertAuditLog).filter(AlertAuditLog.alert_id == alert.id).order_by(AlertAuditLog.id.asc()).all()
    assert len(logs) == 3
    assert logs[0].action == "ACKNOWLEDGED"
    assert logs[1].action == "INVESTIGATING"
    assert logs[2].action == "RESOLVED"


def test_alert_lifecycle_invalid_transition(client_and_session):
    _, db = client_and_session
    alert = Alert(
        alert_code="ALT-TEST-002",
        event_id=201,
        severity="LOW",
        title="Test Terminal Alert",
        message="Testing invalid transitions",
        status="RESOLVED",
        incident_payload_json={}
    )
    db.add(alert)
    db.commit()
    db.refresh(alert)

    # Transitioning from terminal RESOLVED to NEW should raise ValueError
    with pytest.raises(ValueError):
        AlertEngine.transition_status(db, alert.id, "NEW")


# ==========================================
# 4. Response Routing & Notification Tests
# ==========================================

def test_response_routing_service_matching(client_and_session):
    _, db = client_and_session
    res = ResponseRoutingService.resolve_routing(
        db=db,
        classification="INDUSTRIAL_FIRE",
        severity="CRITICAL",
        jurisdiction="Gujarat"
    )

    assert res["department_type"] == "FIRE_EMERGENCY"
    assert "Gujarat State Fire" in res["recommended_recipient"]
    assert res["routing_status"] == "CONFIGURED_VERIFIED"
    assert "Immediate incident commander triage" in res["recommended_action"]


def test_response_routing_fallback_when_unmatched(client_and_session):
    _, db = client_and_session
    res = ResponseRoutingService.resolve_routing(
        db=db,
        classification="AGRICULTURAL_BURNING",
        severity="LOW",
        jurisdiction="Antarctica"
    )

    assert res["department_type"] == "ENVIRONMENT"
    assert res["routing_status"] in ["DEFAULT_FALLBACK", "CONFIGURED_UNVERIFIED", "CONFIGURED_VERIFIED"]


def test_in_app_notification_creation(client_and_session):
    _, db = client_and_session
    alert = Alert(
        alert_code="ALT-NOTIF-001",
        event_id=201,
        severity="CRITICAL",
        title="Critical Notification Test",
        message="In-app notification verification",
        status="NEW",
        incident_payload_json={}
    )
    db.add(alert)
    db.commit()

    provider = InAppNotificationProvider()
    log = provider.send_alert_notification(db, alert)
    assert log.id is not None
    assert log.status == "DELIVERED"
    assert log.channel == "IN_APP"


def test_disabled_external_provider_guard(client_and_session):
    _, db = client_and_session
    alert = Alert(
        alert_code="ALT-NOTIF-002",
        event_id=201,
        severity="HIGH",
        title="Email Guard Test",
        message="Verifying external provider safety guard",
        status="NEW",
        incident_payload_json={}
    )
    db.add(alert)
    db.commit()

    email_provider = EmailNotificationProvider(integration_enabled=False)
    log = email_provider.send_alert_notification(db, alert, recipient="test@example.com")
    assert log.status == "DISABLED"


# ==========================================
# 5. REST API Endpoints Verification
# ==========================================

def test_api_alerts_endpoints(client_and_session):
    client, db = client_and_session

    # Create alert
    alert = Alert(
        alert_code="ALT-API-001",
        event_id=201,
        severity="CRITICAL",
        title="API Test Alert",
        message="Testing HTTP routes",
        status="NEW",
        incident_payload_json={"risk_score": 85.0}
    )
    db.add(alert)
    db.commit()
    db.refresh(alert)

    # 1. List alerts
    res = client.get("/api/v1/alerts")
    assert res.status_code == 200
    data = res.json()
    assert data["total"] >= 1
    assert any(a["alert_code"] == "ALT-API-001" for a in data["items"])

    # 2. Alert stats summary
    res_stats = client.get("/api/v1/alerts/stats/summary")
    assert res_stats.status_code == 200
    stats = res_stats.json()
    assert stats["critical_count"] >= 1

    # 3. Get single alert
    res_single = client.get(f"/api/v1/alerts/{alert.id}")
    assert res_single.status_code == 200
    assert res_single.json()["alert_code"] == "ALT-API-001"

    # 4. Acknowledge alert via API
    res_ack = client.post(f"/api/v1/alerts/{alert.id}/acknowledge", json={"actor": "analyst_bob", "comment": "Reviewing"})
    assert res_ack.status_code == 200
    assert res_ack.json()["status"] == "ACKNOWLEDGED"

    # 5. Escalate alert via API
    res_esc = client.post(f"/api/v1/alerts/{alert.id}/escalate", json={"actor": "analyst_bob", "comment": "Escalating"})
    assert res_esc.status_code == 200
    assert res_esc.json()["status"] == "ESCALATED"

    # 6. Resolve alert via API
    res_res = client.post(f"/api/v1/alerts/{alert.id}/resolve", json={"actor": "lead_alice", "comment": "Resolved"})
    assert res_res.status_code == 200
    assert res_res.json()["status"] == "RESOLVED"


def test_api_risk_endpoints(client_and_session):
    client, _ = client_and_session

    res = client.get("/api/v1/events/201/risk")
    assert res.status_code == 200
    data = res.json()
    assert "risk_score" in data
    assert "risk_level" in data
    assert "breakdown" in data
    assert data["risk_model_version"] == "risk-v1"

    # History
    res_hist = client.get("/api/v1/events/201/risk/history")
    assert res_hist.status_code == 200
    hist = res_hist.json()
    assert len(hist) >= 1


def test_api_alert_rules_crud(client_and_session):
    client, _ = client_and_session

    # List rules
    res = client.get("/api/v1/alert-rules")
    assert res.status_code == 200
    rules = res.json()
    assert len(rules) >= 1

    # Create new rule
    new_rule = {
        "name": "CUSTOM_PETROCHEM_HAZARD",
        "description": "High risk alerts in petrochemical zones",
        "severity": "CRITICAL",
        "cooldown_minutes": 45,
        "conditions": [{"field": "risk_score", "op": ">=", "value": 80}]
    }
    res_post = client.post("/api/v1/alert-rules", json=new_rule)
    assert res_post.status_code == 201
    created_id = res_post.json()["id"]

    # Patch rule
    res_patch = client.patch(f"/api/v1/alert-rules/{created_id}", json={"enabled": False, "cooldown_minutes": 30})
    assert res_patch.status_code == 200
    assert res_patch.json()["enabled"] is False
    assert res_patch.json()["cooldown_minutes"] == 30


def test_api_routing_and_contacts(client_and_session):
    client, _ = client_and_session

    # Event routing evaluation
    res_route = client.get("/api/v1/events/201/routing")
    assert res_route.status_code == 200
    data = res_route.json()
    assert "routing" in data
    assert "recommended_recipient" in data["routing"]

    # List contacts
    res_contacts = client.get("/api/v1/response-contacts")
    assert res_contacts.status_code == 200
    assert len(res_contacts.json()) >= 1


def test_api_notifications_and_preferences(client_and_session):
    client, _ = client_and_session

    # Get preferences
    res_pref = client.get("/api/v1/notifications/preferences?user_id=analyst_1")
    assert res_pref.status_code == 200
    assert res_pref.json()["in_app_enabled"] is True

    # Update preferences
    res_update = client.put(
        "/api/v1/notifications/preferences?user_id=analyst_1",
        json={
            "subscribed_severities": ["CRITICAL"],
            "subscribed_categories": ["INDUSTRIAL_FIRE"],
            "in_app_enabled": True,
            "email_enabled": False
        }
    )
    assert res_update.status_code == 200
    assert res_update.json()["subscribed_severities"] == ["CRITICAL"]

    # List in-app notifications
    res_notifs = client.get("/api/v1/notifications")
    assert res_notifs.status_code == 200
    assert isinstance(res_notifs.json(), list)
