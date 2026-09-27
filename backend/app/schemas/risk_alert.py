from datetime import datetime
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field, ConfigDict


# ==========================================
# Risk Schemas
# ==========================================

class RiskFactorBreakdown(BaseModel):
    category: str
    contribution_points: float
    max_points: float
    description: str


class RiskAssessmentResponse(BaseModel):
    id: Optional[int] = None
    event_id: int
    risk_score: float = Field(..., ge=0.0, le=100.0)
    risk_level: str  # LOW, MODERATE, HIGH, CRITICAL
    risk_model_version: str = "risk-v1"
    breakdown: Dict[str, Any]
    input_snapshot: Dict[str, Any]
    calculated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ==========================================
# Alert Rule Schemas
# ==========================================

class AlertRuleCondition(BaseModel):
    field: str
    op: str  # ==, !=, >, >=, <, <=, in, contains
    value: Any


class AlertRuleBase(BaseModel):
    name: str
    description: Optional[str] = None
    enabled: bool = True
    severity: str = "HIGH"  # CRITICAL, HIGH, MODERATE, LOW
    conditions: List[Dict[str, Any]] = []
    cooldown_minutes: int = 60


class AlertRuleCreate(AlertRuleBase):
    pass


class AlertRuleUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    enabled: Optional[bool] = None
    severity: Optional[str] = None
    conditions: Optional[List[Dict[str, Any]]] = None
    cooldown_minutes: Optional[int] = None


class AlertRuleResponse(AlertRuleBase):
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ==========================================
# Alert Schemas
# ==========================================

class AlertAuditLogResponse(BaseModel):
    id: int
    alert_id: int
    actor: str
    action: str
    previous_status: Optional[str] = None
    new_status: Optional[str] = None
    comment: Optional[str] = None
    metadata_json: Optional[Dict[str, Any]] = None
    timestamp: datetime

    model_config = ConfigDict(from_attributes=True)


class AlertActionRequest(BaseModel):
    actor: str = "analyst"
    comment: Optional[str] = None


class AlertResponse(BaseModel):
    id: int
    alert_code: str
    event_id: int
    rule_id: Optional[int] = None
    severity: str  # CRITICAL, HIGH, MODERATE, LOW
    title: str
    message: str
    status: str  # NEW, ACKNOWLEDGED, INVESTIGATING, ESCALATED, RESOLVED, DISMISSED
    incident_payload: Dict[str, Any] = Field(default_factory=dict, alias="incident_payload_json")
    created_at: datetime
    acknowledged_at: Optional[datetime] = None
    acknowledged_by: Optional[str] = None
    escalated_at: Optional[datetime] = None
    resolved_at: Optional[datetime] = None
    resolved_by: Optional[str] = None
    audit_logs: Optional[List[AlertAuditLogResponse]] = None

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class AlertListResponse(BaseModel):
    total: int
    items: List[AlertResponse]


class AlertStatsSummary(BaseModel):
    total_alerts: int
    critical_count: int
    high_count: int
    moderate_count: int
    low_count: int
    new_count: int
    acknowledged_count: int
    investigating_count: int
    escalated_count: int
    resolved_count: int
    avg_acknowledgement_minutes: Optional[float] = None


# ==========================================
# Response Contact Schemas
# ==========================================

class ResponseContactBase(BaseModel):
    organization_name: str
    department_type: str  # FIRE_EMERGENCY, DISASTER_MANAGEMENT, FOREST, ENVIRONMENT, INDUSTRIAL_SAFETY, FACILITY_OPERATOR, OTHER
    jurisdiction: str
    contact_type: str = "EMAIL"  # EMAIL, SMS, WEBHOOK, PHONE
    contact_value: str
    enabled: bool = True
    verified: bool = False


class ResponseContactCreate(ResponseContactBase):
    pass


class ResponseContactResponse(ResponseContactBase):
    id: int
    last_verified_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ==========================================
# Notification Preferences Schemas
# ==========================================

class NotificationPreferenceBase(BaseModel):
    subscribed_severities: List[str] = ["CRITICAL", "HIGH", "MODERATE"]
    subscribed_categories: List[str] = ["INDUSTRIAL_FIRE", "GAS_FLARE", "WILDFIRE", "PERSISTENT_INDUSTRIAL_THERMAL_SOURCE"]
    in_app_enabled: bool = True
    email_enabled: bool = False
    webhook_url: Optional[str] = None


class NotificationPreferenceResponse(NotificationPreferenceBase):
    id: int
    user_id: str
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

