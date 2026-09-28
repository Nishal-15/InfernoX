from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Text, JSON, Float
from sqlalchemy.orm import relationship
from app.db.database import Base

def utc_now():
    return datetime.now(timezone.utc)

# ----------------------------------------------------
# 1. USER & IDENTITY
# ----------------------------------------------------
class User(Base):
    """
    Core User entity for InfernoX SaaS platform.
    Passwords are hashed using Argon2id.
    """
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(256), unique=True, nullable=False, index=True)
    name = Column(String(128), nullable=False)
    phone = Column(String(32), nullable=True)
    password_hash = Column(String(256), nullable=False)
    status = Column(String(32), default="ACTIVE", nullable=False, index=True)  # ACTIVE, PENDING, SUSPENDED
    email_verified = Column(Boolean, default=False, nullable=False)
    is_superadmin = Column(Boolean, default=False, nullable=False, index=True)
    
    last_login_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=utc_now, nullable=False)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now, nullable=False)

    # Relationships
    memberships = relationship("OrganizationMember", back_populates="user", cascade="all, delete-orphan")

    def __init__(self, **kwargs):
        if "full_name" in kwargs:
            kwargs["name"] = kwargs.pop("full_name")
        super().__init__(**kwargs)

    @property
    def full_name(self) -> str:
        return self.name

    @full_name.setter
    def full_name(self, value: str):
        self.name = value


# ----------------------------------------------------
# 2. ORGANIZATION / TENANT
# ----------------------------------------------------
class Organization(Base):
    """
    Tenant entity that encapsulates workspaces, members, proprietary facilities,
    custom alert rules, private reports, and billing subscriptions.
    """
    __tablename__ = "organizations"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(128), nullable=False)
    slug = Column(String(128), unique=True, nullable=False, index=True)
    status = Column(String(32), default="ACTIVE", nullable=False, index=True)  # ACTIVE, TRIAL, SUSPENDED, DEACTIVATED
    plan_tier = Column(String(32), default="FREE", nullable=False, index=True)  # FREE, PRO, ENTERPRISE
    custom_region = Column(String(256), nullable=True)
    settings = Column(JSON, nullable=True)
    
    billing_customer_id = Column(String(128), nullable=True)
    current_period_end = Column(DateTime, nullable=True)
    
    created_at = Column(DateTime, default=utc_now, nullable=False)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now, nullable=False)

    # Relationships
    members = relationship("OrganizationMember", back_populates="organization", cascade="all, delete-orphan")
    invitations = relationship("OrganizationInvitation", back_populates="organization", cascade="all, delete-orphan")
    api_keys = relationship("ApiKey", back_populates="organization", cascade="all, delete-orphan")
    webhooks = relationship("WebhookEndpoint", back_populates="organization", cascade="all, delete-orphan")
    subscription = relationship("Subscription", back_populates="organization", uselist=False, cascade="all, delete-orphan")

    def __init__(self, **kwargs):
        if "plan" in kwargs:
            kwargs["plan_tier"] = kwargs.pop("plan")
        if "slug" not in kwargs and "name" in kwargs:
            kwargs["slug"] = kwargs["name"].lower().replace(" ", "-")[:40]
        super().__init__(**kwargs)

    @property
    def plan(self) -> str:
        return self.plan_tier

    @plan.setter
    def plan(self, value: str):
        self.plan_tier = value


# ----------------------------------------------------
# 3. ORGANIZATION MEMBERSHIP & ROLES
# ----------------------------------------------------
class OrganizationMember(Base):
    """
    Associates users with organizations under strict RBAC roles:
    SUPER_ADMIN, ORG_ADMIN, ANALYST, OPERATOR, VIEWER, REPORT_MANAGER.
    """
    __tablename__ = "organization_members"

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    role = Column(String(32), default="ANALYST", nullable=False, index=True)
    status = Column(String(32), default="ACTIVE", nullable=False, index=True)  # ACTIVE, INVITED, SUSPENDED

    created_at = Column(DateTime, default=utc_now, nullable=False)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now, nullable=False)

    # Relationships
    organization = relationship("Organization", back_populates="members")
    user = relationship("User", back_populates="memberships")

    @property
    def user_email(self):
        return self.user.email if self.user else None

    @property
    def user_name(self):
        return self.user.name if self.user else None


# ----------------------------------------------------
# 4. INVITATION SYSTEM
# ----------------------------------------------------
class OrganizationInvitation(Base):
    """
    Secure one-time invitation token allowing new or existing users
    to join an organization under a predetermined role.
    """
    __tablename__ = "organization_invitations"

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    email = Column(String(256), nullable=False, index=True)
    role = Column(String(32), default="ANALYST", nullable=False)
    token = Column(String(128), unique=True, nullable=False, index=True)
    invited_by_user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    
    expires_at = Column(DateTime, nullable=False)
    accepted_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=utc_now, nullable=False)

    # Relationships
    organization = relationship("Organization", back_populates="invitations")

    def __init__(self, **kwargs):
        if "invited_by_id" in kwargs:
            kwargs["invited_by_user_id"] = kwargs.pop("invited_by_id")
        if "accepted" in kwargs:
            acc = kwargs.pop("accepted")
            if acc:
                kwargs["accepted_at"] = utc_now()
        super().__init__(**kwargs)

    @property
    def accepted(self) -> bool:
        return self.accepted_at is not None

    @accepted.setter
    def accepted(self, val: bool):
        if val and self.accepted_at is None:
            self.accepted_at = utc_now()
        elif not val:
            self.accepted_at = None


# ----------------------------------------------------
# 5. API KEY SYSTEM
# ----------------------------------------------------
class ApiKey(Base):
    """
    Hashed organization API credentials for programmatic headless ingestion,
    external alerting integrations, and automation pipelines.
    """
    __tablename__ = "api_keys"

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(128), nullable=False)
    key_prefix = Column(String(16), nullable=False, index=True)  # e.g., inf_live_4a1f
    hashed_secret = Column(String(256), nullable=False)  # SHA-256 hash of raw key
    permissions_json = Column(JSON, nullable=False, default=list)  # e.g. ["events.read", "alerts.read"]
    
    created_by_user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    last_used_at = Column(DateTime, nullable=True)
    expires_at = Column(DateTime, nullable=True)
    revoked_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=utc_now, nullable=False)

    # Relationships
    organization = relationship("Organization", back_populates="api_keys")

    def __init__(self, **kwargs):
        if "permissions" in kwargs:
            kwargs["permissions_json"] = kwargs.pop("permissions")
        if "created_by_id" in kwargs:
            kwargs["created_by_user_id"] = kwargs.pop("created_by_id")
        if "is_active" in kwargs:
            act = kwargs.pop("is_active")
            if not act and "revoked_at" not in kwargs:
                kwargs["revoked_at"] = utc_now()
        super().__init__(**kwargs)

    @property
    def permissions(self) -> list:
        return self.permissions_json or []

    @permissions.setter
    def permissions(self, val: list):
        self.permissions_json = val

    @property
    def is_active(self) -> bool:
        return self.revoked_at is None

    @is_active.setter
    def is_active(self, val: bool):
        if not val and self.revoked_at is None:
            self.revoked_at = utc_now()
        elif val:
            self.revoked_at = None


# ----------------------------------------------------
# 6. WEBHOOK SYSTEM
# ----------------------------------------------------
class WebhookEndpoint(Base):
    """
    Configurable outbound webhook notifications for tenant events,
    signed via HMAC-SHA256.
    """
    __tablename__ = "webhook_endpoints"

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    url = Column(String(512), nullable=False)
    secret = Column(String(128), nullable=False)  # Signing secret
    events_json = Column(JSON, nullable=False, default=list)  # ["incident.created", "alert.created"]
    is_active = Column(Boolean, default=True, nullable=False, index=True)
    description = Column(String(256), nullable=True)
    
    failure_count = Column(Integer, default=0, nullable=False)
    last_delivery_at = Column(DateTime, nullable=True)
    last_error = Column(Text, nullable=True)
    created_at = Column(DateTime, default=utc_now, nullable=False)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now, nullable=False)

    # Relationships
    organization = relationship("Organization", back_populates="webhooks")

    def __init__(self, **kwargs):
        if "subscribed_events" in kwargs:
            kwargs["events_json"] = kwargs.pop("subscribed_events")
        super().__init__(**kwargs)

    @property
    def subscribed_events(self) -> list:
        return self.events_json or []

    @subscribed_events.setter
    def subscribed_events(self, val: list):
        self.events_json = val

    @property
    def consecutive_failures(self) -> int:
        return self.failure_count

    @consecutive_failures.setter
    def consecutive_failures(self, val: int):
        self.failure_count = val

    @property
    def last_triggered_at(self):
        return self.last_delivery_at

    @last_triggered_at.setter
    def last_triggered_at(self, val):
        self.last_delivery_at = val


# ----------------------------------------------------
# 7. SUBSCRIPTION & BILLING (RAZORPAY)
# ----------------------------------------------------
class Subscription(Base):
    """
    Tenant subscription status backed by Razorpay payments / webhooks.
    """
    __tablename__ = "subscriptions"

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id", ondelete="CASCADE"), unique=True, nullable=False)
    plan_tier = Column(String(32), default="FREE", nullable=False)  # FREE, PRO, ENTERPRISE
    status = Column(String(32), default="ACTIVE", nullable=False, index=True)  # ACTIVE, PAST_DUE, CANCELLED, TRIALING
    billing_email = Column(String(256), nullable=True)
    
    razorpay_subscription_id = Column(String(128), nullable=True, index=True)
    razorpay_plan_id = Column(String(128), nullable=True)
    razorpay_customer_id = Column(String(128), nullable=True)
    
    current_start = Column(DateTime, default=utc_now, nullable=False)
    current_end = Column(DateTime, nullable=True)
    cancel_at_period_end = Column(Boolean, default=False, nullable=False)
    
    created_at = Column(DateTime, default=utc_now, nullable=False)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now, nullable=False)

    # Relationships
    organization = relationship("Organization", back_populates="subscription")

    def __init__(self, **kwargs):
        if "plan" in kwargs:
            kwargs["plan_tier"] = kwargs.pop("plan")
        if "current_period_start" in kwargs:
            kwargs["current_start"] = kwargs.pop("current_period_start")
        if "current_period_end" in kwargs:
            kwargs["current_end"] = kwargs.pop("current_period_end")
        super().__init__(**kwargs)

    @property
    def plan(self) -> str:
        return self.plan_tier

    @plan.setter
    def plan(self, value: str):
        self.plan_tier = value

    @property
    def current_period_start(self):
        return self.current_start

    @current_period_start.setter
    def current_period_start(self, val):
        self.current_start = val

    @property
    def current_period_end(self):
        return self.current_end

    @current_period_end.setter
    def current_period_end(self, val):
        self.current_end = val


# ----------------------------------------------------
# 8. USAGE METERING
# ----------------------------------------------------
class UsageRecord(Base):
    """
    Aggregates verifiable operational usage metrics per organization.
    """
    __tablename__ = "usage_records"

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    metric = Column(String(64), nullable=False, index=True)  # events_processed, active_facilities, alerts_generated, reports_generated, api_requests
    count = Column(Integer, default=0, nullable=False)
    period_date = Column(String(10), nullable=False, index=True)  # YYYY-MM
    
    created_at = Column(DateTime, default=utc_now, nullable=False)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now, nullable=False)

    def __init__(self, **kwargs):
        if "metric_name" in kwargs:
            kwargs["metric"] = kwargs.pop("metric_name")
        if "quantity" in kwargs:
            kwargs["count"] = kwargs.pop("quantity")
        if "billing_period" in kwargs:
            kwargs["period_date"] = kwargs.pop("billing_period")
        super().__init__(**kwargs)

    @property
    def metric_name(self) -> str:
        return self.metric

    @metric_name.setter
    def metric_name(self, val: str):
        self.metric = val

    @property
    def quantity(self) -> int:
        return self.count

    @quantity.setter
    def quantity(self, val: int):
        self.count = val

    @property
    def billing_period(self) -> str:
        return self.period_date

    @billing_period.setter
    def billing_period(self, val: str):
        self.period_date = val


# ----------------------------------------------------
# 9. PLATFORM AUDIT LOG
# ----------------------------------------------------
class PlatformAuditLog(Base):
    """
    Comprehensive security and administrative audit record
    tracking authentication, invitations, roles, API keys, and billing.
    """
    __tablename__ = "platform_audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, nullable=True, index=True)
    user_id = Column(Integer, nullable=True, index=True)
    action = Column(String(64), nullable=False, index=True)  # USER_LOGIN, ROLE_CHANGED, API_KEY_CREATED, etc.
    actor_email = Column(String(256), nullable=True)
    ip_address = Column(String(64), nullable=True)
    resource_type = Column(String(64), nullable=True)
    resource_id = Column(String(64), nullable=True)
    details_json = Column(JSON, nullable=False, default=dict)
    
    created_at = Column(DateTime, default=utc_now, nullable=False, index=True)

    def __init__(self, **kwargs):
        if "actor_id" in kwargs:
            val = kwargs.pop("actor_id")
            kwargs["user_id"] = int(val) if val and str(val).isdigit() else None
        if "details" in kwargs:
            kwargs["details_json"] = kwargs.pop("details")
        super().__init__(**kwargs)

    @property
    def actor_id(self):
        return str(self.user_id) if self.user_id is not None else None

    @actor_id.setter
    def actor_id(self, val):
        self.user_id = int(val) if val and str(val).isdigit() else None

    @property
    def details(self):
        return self.details_json

    @details.setter
    def details(self, val):
        self.details_json = val
