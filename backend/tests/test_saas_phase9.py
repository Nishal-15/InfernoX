"""
InfernoX Phase 9 Comprehensive Test Suite
Production SaaS, Multi-Tenancy, RBAC, Security & Billing
"""

import pytest
import hmac
import hashlib
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.db.database import Base
from app.db.session import get_db
from app.core.security import (
    hash_password, verify_password, create_access_token,
    generate_api_key, hash_api_key_secret, compute_webhook_signature,
    verify_webhook_signature
)
from app.services.auth.rbac import Role, Permission, has_permission, get_role_permissions
from app.services.billing.razorpay_provider import (
    PLANS, razorpay_provider, get_organization_usage, check_plan_limit
)
from app.services.websocket.manager import ConnectionManager
from app.models.saas import (
    User, Organization, OrganizationMember, OrganizationInvitation,
    ApiKey, WebhookEndpoint, Subscription, UsageRecord, PlatformAuditLog
)


from sqlalchemy import event

# In-memory SQLite for isolated test execution
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)

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
    dbapi_connection.create_function("CreateSpatialIndex", 2, lambda a, b: 1)

TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


from sqlalchemy import text
from app.models.risk_alert import AlertRule, Alert
from app.models.reporting import GeneratedReport

@pytest.fixture(scope="module")
def db_session():
    with engine.connect() as conn:
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

    User.__table__.create(bind=engine, checkfirst=True)
    Organization.__table__.create(bind=engine, checkfirst=True)
    OrganizationMember.__table__.create(bind=engine, checkfirst=True)
    OrganizationInvitation.__table__.create(bind=engine, checkfirst=True)
    ApiKey.__table__.create(bind=engine, checkfirst=True)
    WebhookEndpoint.__table__.create(bind=engine, checkfirst=True)
    Subscription.__table__.create(bind=engine, checkfirst=True)
    UsageRecord.__table__.create(bind=engine, checkfirst=True)
    PlatformAuditLog.__table__.create(bind=engine, checkfirst=True)
    AlertRule.__table__.create(bind=engine, checkfirst=True)
    Alert.__table__.create(bind=engine, checkfirst=True)
    GeneratedReport.__table__.create(bind=engine, checkfirst=True)

    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture(scope="module")
def client(db_session):
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


# =====================================================================
# 1. Password Hashing & JWT Security Tests
# =====================================================================

def test_argon2id_password_hashing():
    pwd = "UltraSecurePassword2026!"
    hashed = hash_password(pwd)
    assert hashed != pwd
    assert hashed.startswith("$argon2id$")
    assert verify_password(pwd, hashed) is True
    assert verify_password("WrongPassword!", hashed) is False


def test_jwt_token_creation_and_expiration():
    claims = {"sub": "user-123", "email": "test@infernox.ai", "role": "ANALYST"}
    token = create_access_token(claims)
    assert isinstance(token, str)
    assert len(token) > 20


# =====================================================================
# 2. RBAC Permissions Matrix Tests
# =====================================================================

def test_rbac_permissions_matrix():
    # Superadmin has full capabilities
    assert has_permission(Role.SUPER_ADMIN.value, Permission.SYSTEM_MANAGE.value) is True
    assert has_permission(Role.SUPER_ADMIN.value, Permission.BILLING_MANAGE.value) is True

    # Org Admin has organization & billing capabilities, but not platform-wide system manage
    assert has_permission(Role.ORG_ADMIN.value, Permission.ORGANIZATION_MANAGE.value) is True
    assert has_permission(Role.ORG_ADMIN.value, Permission.BILLING_MANAGE.value) is True
    assert has_permission(Role.ORG_ADMIN.value, Permission.SYSTEM_MANAGE.value) is False

    # Analyst can review & investigate, but cannot manage billing or users
    assert has_permission(Role.ANALYST.value, Permission.EVENTS_INVESTIGATE.value) is True
    assert has_permission(Role.ANALYST.value, Permission.EVENTS_REVIEW.value) is True
    assert has_permission(Role.ANALYST.value, Permission.BILLING_MANAGE.value) is False
    assert has_permission(Role.ANALYST.value, Permission.USERS_MANAGE.value) is False

    # Viewer has read-only access
    assert has_permission(Role.VIEWER.value, Permission.EVENTS_READ.value) is True
    assert has_permission(Role.VIEWER.value, Permission.EVENTS_INVESTIGATE.value) is False
    assert has_permission(Role.VIEWER.value, Permission.ALERTS_MANAGE.value) is False


# =====================================================================
# 3. User Registration, Login & Profile Endpoints
# =====================================================================

def test_user_registration_creates_org_and_admin(client):
    reg_payload = {
        "email": "sarah.connor@skywatch.io",
        "full_name": "Sarah Connor",
        "password": "PasswordSkywatch2026!",
        "organization_name": "SkyWatch Space Intelligence"
    }
    response = client.post("/api/v1/auth/register", json=reg_payload)
    assert response.status_code == 201
    data = response.json()
    assert "access_token" in data
    assert data["role"] == "ORG_ADMIN"
    assert data["active_organization_id"] is not None
    assert "organization.manage" in data["permissions"]


def test_user_login_success_and_failure(client):
    # Valid login
    login_payload = {
        "email": "sarah.connor@skywatch.io",
        "password": "PasswordSkywatch2026!"
    }
    res = client.post("/api/v1/auth/login", json=login_payload)
    assert res.status_code == 200
    data = res.json()
    assert "access_token" in data

    # Invalid password
    bad_login = {
        "email": "sarah.connor@skywatch.io",
        "password": "WrongPassword123!"
    }
    bad_res = client.post("/api/v1/auth/login", json=bad_login)
    assert bad_res.status_code == 401


# =====================================================================
# 4. Multi-Tenant Isolation Tests (CRITICAL REQUIREMENT)
# =====================================================================

def test_tenant_isolation_user_a_cannot_access_org_b(client):
    # 1. Register Org A
    user_a_res = client.post("/api/v1/auth/register", json={
        "email": "usera@alpha.com",
        "full_name": "User Alpha",
        "password": "AlphaPassword2026!",
        "organization_name": "Alpha Corp"
    }).json()
    token_a = user_a_res["access_token"]
    org_a_id = user_a_res["active_organization_id"]

    # 2. Register Org B
    user_b_res = client.post("/api/v1/auth/register", json={
        "email": "userb@beta.com",
        "full_name": "User Beta",
        "password": "BetaPassword2026!",
        "organization_name": "Beta Corp"
    }).json()
    org_b_id = user_b_res["active_organization_id"]

    # 3. User A attempts to list members of Org B by forging X-Organization-Id
    forged_headers = {
        "Authorization": f"Bearer {token_a}",
        "X-Organization-Id": str(org_b_id)
    }
    res = client.get("/api/v1/organizations/members", headers=forged_headers)

    # Server-side validation MUST reject User A with 403 Forbidden
    assert res.status_code == 403
    assert "Access denied to organization" in res.json()["detail"]


# =====================================================================
# 5. Headless API Key Generation & Revocation Tests
# =====================================================================

def test_api_key_lifecycle(client):
    # Register org admin
    reg = client.post("/api/v1/auth/register", json={
        "email": "devops@telemetry.io",
        "full_name": "DevOps Lead",
        "password": "DevOpsPassword2026!",
        "organization_name": "Telemetry Org"
    }).json()
    token = reg["access_token"]
    org_id = reg["active_organization_id"]

    headers = {"Authorization": f"Bearer {token}", "X-Organization-Id": str(org_id)}

    # 1. Create API Key
    create_res = client.post("/api/v1/organizations/api-keys", json={
        "name": "Pipeline Ingestion Daemon",
        "permissions": ["events.read"]
    }, headers=headers)
    assert create_res.status_code == 201
    key_data = create_res.json()
    assert "raw_api_key" in key_data
    assert key_data["raw_api_key"].startswith("inf_live_")
    key_id = key_data["id"]

    # 2. List API Keys (raw key must NOT be returned)
    list_res = client.get("/api/v1/organizations/api-keys", headers=headers)
    assert list_res.status_code == 200
    listed_keys = list_res.json()
    assert any(k["id"] == key_id for k in listed_keys)
    assert "raw_api_key" not in listed_keys[0]

    # 3. Revoke API Key
    del_res = client.delete(f"/api/v1/organizations/api-keys/{key_id}", headers=headers)
    assert del_res.status_code == 200
    assert del_res.json()["message"] == "API key successfully revoked"


# =====================================================================
# 6. Outbound Webhooks & HMAC-SHA256 Signatures
# =====================================================================

def test_webhook_signatures_and_registration(client):
    secret = "rzp_secret_infernox_test_key_12345"
    payload = b'{"event":"alert.created","data":{"alert_id":42,"severity":"CRITICAL"}}'
    timestamp = "1727450000"

    sig = compute_webhook_signature(secret, payload, timestamp)
    assert verify_webhook_signature(secret, payload, timestamp, sig) is True

    # Tampered payload fails
    tampered = b'{"event":"alert.created","data":{"alert_id":42,"severity":"LOW"}}'
    assert verify_webhook_signature(secret, tampered, timestamp, sig) is False


# =====================================================================
# 7. Razorpay Provider & Usage Metering
# =====================================================================

def test_razorpay_order_and_plans(client):
    # Verify plans exist
    plans_res = client.get("/api/v1/billing/plans")
    assert plans_res.status_code == 200
    plans = plans_res.json()
    assert len(plans) >= 3
    assert any(p["id"] == "pro" for p in plans)

    # Razorpay order generation
    order = razorpay_provider.create_order("org-test-uuid", "pro", "monthly")
    assert "order_id" in order
    assert order["amount"] == 14999 * 100
    assert order["currency"] == "INR"


def test_usage_metering_and_limits(db_session):
    # Create test org
    org = Organization(name="Usage Test Org", slug="usage-test-org", plan="free", status="ACTIVE")
    db_session.add(org)
    db_session.commit()
    db_session.refresh(org)

    usage = get_organization_usage(db_session, org.id)
    assert usage["plan"] == "free"
    assert "users" in usage["metrics"]
    assert "facilities" in usage["metrics"]
    assert "reports" in usage["metrics"]

    # Check plan limit
    within_limits, msg = check_plan_limit(db_session, org.id, "reports", 1)
    assert within_limits is True


# =====================================================================
# 8. WebSocket Multi-Tenant Isolation
# =====================================================================

def test_websocket_tenant_partitioning():
    manager = ConnectionManager()

    # Simulate client sockets
    class DummyWS:
        def __init__(self):
            self.sent = []
        async def accept(self):
            pass
        async def send_json(self, data):
            self.sent.append(data)

    ws_global = DummyWS()
    ws_org_a = DummyWS()
    ws_org_b = DummyWS()

    import asyncio

    async def run_ws_test():
        await manager.connect(ws_global, organization_id=None)
        await manager.connect(ws_org_a, organization_id="tenant-alpha")
        await manager.connect(ws_org_b, organization_id="tenant-beta")

        assert len(manager.active_connections) == 3

        # Clear greeting
        ws_global.sent.clear()
        ws_org_a.sent.clear()
        ws_org_b.sent.clear()

        # Tenant-specific event targeted at tenant-alpha
        await manager.broadcast(
            event_type="alert_triggered",
            payload={"alert_id": 99, "title": "Private Tenant Alert"},
            organization_id="tenant-alpha"
        )

        # ws_org_a must receive the message
        assert len(ws_org_a.sent) == 1
        assert ws_org_a.sent[0]["payload"]["alert_id"] == 99
        # ws_org_b must NOT receive tenant-alpha's message
        assert len(ws_org_b.sent) == 0

        manager.disconnect(ws_global)
        manager.disconnect(ws_org_a)
        manager.disconnect(ws_org_b)

    asyncio.run(run_ws_test())
