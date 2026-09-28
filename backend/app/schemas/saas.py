"""
InfernoX Phase 9: Production SaaS Pydantic Schemas
Multi-tenancy, RBAC, API Keys, Webhooks, Billing & Audit Logging
"""

from datetime import datetime
from typing import Optional, List, Dict, Any, Union
from pydantic import BaseModel, ConfigDict, EmailStr, Field


# ---------------------------------------------------------
# User Schemas
# ---------------------------------------------------------

class UserBase(BaseModel):
    email: EmailStr
    full_name: str
    phone: Optional[str] = None


class UserCreate(UserBase):
    password: str = Field(..., min_length=8, description="Password must be at least 8 characters")
    organization_name: Optional[str] = Field(None, description="Optional initial organization name")


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserResponse(UserBase):
    id: Union[int, str]
    status: str
    email_verified: bool
    is_superadmin: bool
    created_at: datetime
    last_login_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    phone: Optional[str] = None
    password: Optional[str] = Field(None, min_length=8)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserResponse
    active_organization_id: Optional[Union[int, str]] = None
    role: Optional[str] = None
    permissions: List[str] = []


# ---------------------------------------------------------
# Organization Schemas
# ---------------------------------------------------------

class OrganizationBase(BaseModel):
    name: str
    slug: Optional[str] = None


class OrganizationCreate(OrganizationBase):
    plan: str = "free"


class OrganizationUpdate(BaseModel):
    name: Optional[str] = None
    custom_region: Optional[str] = None
    settings: Optional[Dict[str, Any]] = None


class OrganizationResponse(OrganizationBase):
    id: Union[int, str]
    slug: Optional[str] = None
    status: str
    plan: str
    custom_region: Optional[str] = None
    settings: Optional[Dict[str, Any]] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------
# Organization Membership & Invitations
# ---------------------------------------------------------

class OrganizationMemberOut(BaseModel):
    id: Union[int, str]
    user_id: Union[int, str]
    organization_id: Union[int, str]
    role: str
    status: str
    user_email: Optional[str] = None
    user_name: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class MemberRoleUpdate(BaseModel):
    role: str = Field(..., pattern="^(SUPER_ADMIN|ORG_ADMIN|ANALYST|OPERATOR|VIEWER|REPORT_MANAGER)$")


class InvitationCreate(BaseModel):
    email: EmailStr
    role: str = Field(default="ANALYST", pattern="^(ORG_ADMIN|ANALYST|OPERATOR|VIEWER|REPORT_MANAGER)$")


class InvitationResponse(BaseModel):
    id: Union[int, str]
    organization_id: Union[int, str]
    email: EmailStr
    role: str
    token: str
    expires_at: datetime
    accepted: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class InvitationAccept(BaseModel):
    token: str
    full_name: str
    password: str = Field(..., min_length=8)


# ---------------------------------------------------------
# API Key Schemas
# ---------------------------------------------------------

class ApiKeyCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=64)
    permissions: List[str] = Field(default=["events.read", "analytics.read"])
    expires_in_days: Optional[int] = Field(365, ge=1, le=730)


class ApiKeyResponse(BaseModel):
    id: Union[int, str]
    organization_id: Union[int, str]
    name: str
    key_prefix: str
    permissions: List[str]
    is_active: bool
    created_at: datetime
    expires_at: Optional[datetime] = None
    last_used_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class ApiKeyCreatedResponse(ApiKeyResponse):
    raw_api_key: str = Field(..., description="Copy this secret key immediately. It cannot be shown again.")


# ---------------------------------------------------------
# Webhook Schemas
# ---------------------------------------------------------

class WebhookCreate(BaseModel):
    url: str = Field(..., pattern="^https?://.*", description="Target destination URL")
    subscribed_events: List[str] = Field(
        default=["alert.created", "alert.escalated", "incident.created"],
        description="List of event types to forward"
    )
    description: Optional[str] = None


class WebhookUpdate(BaseModel):
    url: Optional[str] = None
    subscribed_events: Optional[List[str]] = None
    is_active: Optional[bool] = None
    description: Optional[str] = None


class WebhookResponse(BaseModel):
    id: Union[int, str]
    organization_id: Union[int, str]
    url: str
    subscribed_events: List[str]
    is_active: bool
    created_at: datetime
    last_triggered_at: Optional[datetime] = None
    consecutive_failures: int

    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------
# Billing & Razorpay Schemas
# ---------------------------------------------------------

class PlanTier(BaseModel):
    id: str
    name: str
    price_inr_monthly: int
    price_inr_annual: int
    features: List[str]
    limits: Dict[str, Any]


class SubscriptionResponse(BaseModel):
    id: Union[int, str]
    organization_id: Union[int, str]
    plan: str
    status: str
    current_period_start: Optional[datetime] = None
    current_period_end: Optional[datetime] = None
    cancel_at_period_end: bool
    billing_email: Optional[str] = None
    razorpay_subscription_id: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class RazorpayOrderCreate(BaseModel):
    plan: str = Field(..., pattern="^(free|pro|enterprise)$")
    billing_cycle: str = Field(default="monthly", pattern="^(monthly|annual)$")


class RazorpayCheckoutResponse(BaseModel):
    order_id: str
    razorpay_key_id: str
    amount: int
    currency: str
    plan: str
    billing_cycle: str
    organization_id: Union[int, str]
    prefill_name: str
    prefill_email: str


class RazorpayPaymentVerify(BaseModel):
    razorpay_payment_id: str
    razorpay_order_id: str
    razorpay_signature: str
    plan: str


class UsageMetricSummary(BaseModel):
    metric_name: str
    current_value: int
    limit_value: int
    usage_percent: float


class UsageResponse(BaseModel):
    organization_id: Union[int, str]
    plan: str
    metrics: Dict[str, UsageMetricSummary]
    billing_period: str


# ---------------------------------------------------------
# Platform Audit Log Schemas
# ---------------------------------------------------------

class PlatformAuditLogOut(BaseModel):
    id: Union[int, str]
    actor_id: Optional[Union[int, str]] = None
    actor_email: Optional[str] = None
    organization_id: Optional[Union[int, str]] = None
    action: str
    resource_type: str
    resource_id: Optional[str] = None
    details: Optional[Dict[str, Any]] = None
    ip_address: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
