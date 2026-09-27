from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, ForeignKey, Text, JSON
from sqlalchemy.orm import relationship
from app.db.database import Base


def utc_now():
    return datetime.now(timezone.utc)


class RiskAssessment(Base):
    __tablename__ = "risk_assessments"

    id = Column(Integer, primary_key=True, index=True)
    event_id = Column(Integer, ForeignKey("thermal_events.id", ondelete="CASCADE"), nullable=False, index=True)
    risk_score = Column(Float, nullable=False, index=True)
    risk_level = Column(String(32), nullable=False, index=True)  # LOW, MODERATE, HIGH, CRITICAL
    risk_model_version = Column(String(32), default="risk-v1", nullable=False)
    breakdown_json = Column(JSON, nullable=False, default=dict)
    input_snapshot_json = Column(JSON, nullable=False, default=dict)
    calculated_at = Column(DateTime, default=utc_now, nullable=False, index=True)

    # Relationships
    event = relationship("ThermalEvent", backref="risk_assessments")


class AlertRule(Base):
    __tablename__ = "alert_rules"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(128), unique=True, nullable=False, index=True)
    description = Column(String(256), nullable=True)
    enabled = Column(Boolean, default=True, nullable=False, index=True)
    severity = Column(String(32), nullable=False, index=True)  # CRITICAL, HIGH, MODERATE, LOW
    conditions_json = Column(JSON, nullable=False, default=list)
    cooldown_minutes = Column(Integer, default=60, nullable=False)
    created_at = Column(DateTime, default=utc_now, nullable=False)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now, nullable=False)


class Alert(Base):
    __tablename__ = "alerts"

    id = Column(Integer, primary_key=True, index=True)
    alert_code = Column(String(64), unique=True, nullable=False, index=True)  # e.g. ALT-2026-000001
    event_id = Column(Integer, ForeignKey("thermal_events.id", ondelete="CASCADE"), nullable=False, index=True)
    incident_id = Column(Integer, nullable=True, index=True) # Associated ThermalIncident id
    rule_id = Column(Integer, ForeignKey("alert_rules.id", ondelete="SET NULL"), nullable=True, index=True)
    severity = Column(String(32), nullable=False, index=True)  # CRITICAL, HIGH, MODERATE, LOW
    title = Column(String(256), nullable=False)
    message = Column(Text, nullable=False)
    status = Column(String(32), default="NEW", nullable=False, index=True)  # NEW, ACKNOWLEDGED, INVESTIGATING, ESCALATED, RESOLVED, DISMISSED
    incident_payload_json = Column(JSON, nullable=False, default=dict)
    created_at = Column(DateTime, default=utc_now, nullable=False, index=True)
    acknowledged_at = Column(DateTime, nullable=True)
    acknowledged_by = Column(String(128), nullable=True)
    escalated_at = Column(DateTime, nullable=True)
    resolved_at = Column(DateTime, nullable=True)
    resolved_by = Column(String(128), nullable=True)

    # Relationships
    event = relationship("ThermalEvent", backref="alerts")
    rule = relationship("AlertRule", backref="alerts")
    audit_logs = relationship("AlertAuditLog", backref="alert", cascade="all, delete-orphan", order_by="AlertAuditLog.timestamp.desc()")


class AlertAuditLog(Base):
    __tablename__ = "alert_audit_log"

    id = Column(Integer, primary_key=True, index=True)
    alert_id = Column(Integer, ForeignKey("alerts.id", ondelete="CASCADE"), nullable=False, index=True)
    actor = Column(String(128), nullable=False)
    action = Column(String(64), nullable=False, index=True)
    previous_status = Column(String(32), nullable=True)
    new_status = Column(String(32), nullable=True)
    comment = Column(Text, nullable=True)
    metadata_json = Column(JSON, nullable=True)
    timestamp = Column(DateTime, default=utc_now, nullable=False, index=True)


class ResponseContact(Base):
    __tablename__ = "response_contacts"

    id = Column(Integer, primary_key=True, index=True)
    organization_name = Column(String(256), nullable=False)
    department_type = Column(String(64), nullable=False, index=True)  # FIRE_EMERGENCY, DISASTER_MANAGEMENT, FOREST, ENVIRONMENT, INDUSTRIAL_SAFETY, FACILITY_OPERATOR, OTHER
    jurisdiction = Column(String(128), nullable=False, index=True)  # e.g. Gujarat, Maharashtra, National, GLOBAL
    contact_type = Column(String(32), nullable=False)  # EMAIL, SMS, WEBHOOK, PHONE
    contact_value = Column(String(256), nullable=False)
    enabled = Column(Boolean, default=True, nullable=False)
    verified = Column(Boolean, default=False, nullable=False)
    last_verified_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=utc_now, nullable=False)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now, nullable=False)


class NotificationPreference(Base):
    __tablename__ = "notification_preferences"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String(128), default="analyst-default", nullable=False, unique=True, index=True)
    subscribed_severities = Column(JSON, nullable=False, default=list)
    subscribed_categories = Column(JSON, nullable=False, default=list)
    in_app_enabled = Column(Boolean, default=True, nullable=False)
    email_enabled = Column(Boolean, default=False, nullable=False)
    webhook_url = Column(String(512), nullable=True)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now, nullable=False)


class NotificationLog(Base):
    __tablename__ = "notification_logs"

    id = Column(Integer, primary_key=True, index=True)
    alert_id = Column(Integer, ForeignKey("alerts.id", ondelete="CASCADE"), nullable=False, index=True)
    channel = Column(String(32), nullable=False, index=True)  # IN_APP, EMAIL, WEBHOOK, SMS
    recipient = Column(String(256), nullable=False)
    status = Column(String(32), default="DELIVERED", nullable=False, index=True)  # DELIVERED, PENDING, DISABLED, FAILED
    payload_json = Column(JSON, nullable=False, default=dict)
    created_at = Column(DateTime, default=utc_now, nullable=False, index=True)
