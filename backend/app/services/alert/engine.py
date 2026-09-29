import logging
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, List, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.models.thermal_event import ThermalEvent
from app.models.risk_alert import Alert, AlertRule, AlertAuditLog, NotificationLog
from app.services.notification.in_app import InAppNotificationProvider
from app.services.routing.service import ResponseRoutingService

logger = logging.getLogger(__name__)


class AlertEngine:
    """
    Dedicated Alert & Incident Management Engine for InfernoX.
    Evaluates configured rules against thermal anomalies, enforces cooldown deduplication,
    manages the incident lifecycle, dispatches in-app notifications, and records audit logs.
    """

    VALID_TRANSITIONS: Dict[str, List[str]] = {
        "NEW": ["ACKNOWLEDGED", "INVESTIGATING", "ESCALATED"],
        "ACKNOWLEDGED": ["INVESTIGATING", "ESCALATED", "RESOLVED", "DISMISSED"],
        "INVESTIGATING": ["ESCALATED", "RESOLVED", "DISMISSED"],
        "ESCALATED": ["INVESTIGATING", "RESOLVED", "DISMISSED"],
        "RESOLVED": [],  # Terminal
        "DISMISSED": []  # Terminal
    }

    # Default Seed Rules for Out-of-the-Box Operation
    DEFAULT_RULES = [
        {
            "name": "CRITICAL_INDUSTRIAL_FIRE",
            "description": "Fires classified as industrial with critical analytical risk score",
            "severity": "CRITICAL",
            "cooldown_minutes": 60,
            "conditions": [
                {"field": "risk_score", "op": ">=", "value": 75.0},
                {"field": "classification", "op": "==", "value": "INDUSTRIAL_FIRE"}
            ]
        },
        {
            "name": "ABNORMAL_THERMAL_SURGE",
            "description": "Thermal anomalies exhibiting abnormal baseline deviation and high FRP",
            "severity": "HIGH",
            "cooldown_minutes": 60,
            "conditions": [
                {"field": "temporal_status", "op": "==", "value": "ABNORMAL"},
                {"field": "frp", "op": ">=", "value": 50.0}
            ]
        },
        {
            "name": "HAZARDOUS_INFRASTRUCTURE_PROXIMITY",
            "description": "Thermal activity occurring within direct perimeter of petrochemical/refinery facility",
            "severity": "HIGH",
            "cooldown_minutes": 60,
            "conditions": [
                {"field": "distance_to_facility_meters", "op": "<=", "value": 500.0},
                {"field": "risk_score", "op": ">=", "value": 50.0}
            ]
        },
        {
            "name": "PERSISTENT_UNREVIEWED_SOURCE",
            "description": "Long-term thermal activity active for 5+ days with moderate risk",
            "severity": "MODERATE",
            "cooldown_minutes": 120,
            "conditions": [
                {"field": "active_days", "op": ">=", "value": 5},
                {"field": "risk_score", "op": ">=", "value": 35.0}
            ]
        }
    ]

    @classmethod
    def seed_default_rules(cls, db: Session) -> List[AlertRule]:
        """
        Seeds default alert rules into the database if not present.
        """
        created = []
        for r_data in cls.DEFAULT_RULES:
            existing = db.query(AlertRule).filter(AlertRule.name == r_data["name"]).first()
            if not existing:
                rule = AlertRule(
                    name=r_data["name"],
                    description=r_data["description"],
                    severity=r_data["severity"],
                    cooldown_minutes=r_data["cooldown_minutes"],
                    conditions_json=r_data["conditions"],
                    enabled=True,
                    created_at=datetime.now(timezone.utc),
                    updated_at=datetime.now(timezone.utc)
                )
                db.add(rule)
                created.append(rule)
        if created:
            db.commit()
            for r in created:
                db.refresh(r)
        return created

    @classmethod
    def evaluate_condition(cls, field_val: Any, op: str, target_val: Any) -> bool:
        """
        Safely evaluates an atomic rule condition without executing arbitrary expressions.
        """
        if field_val is None:
            return False

        try:
            if op == "==":
                if isinstance(field_val, str) and isinstance(target_val, str):
                    return field_val.strip().upper() == target_val.strip().upper()
                return field_val == target_val
            elif op == "!=":
                if isinstance(field_val, str) and isinstance(target_val, str):
                    return field_val.strip().upper() != target_val.strip().upper()
                return field_val != target_val
            elif op == ">":
                return float(field_val) > float(target_val)
            elif op == ">=":
                return float(field_val) >= float(target_val)
            elif op == "<":
                return float(field_val) < float(target_val)
            elif op == "<=":
                return float(field_val) <= float(target_val)
            elif op == "in":
                if isinstance(target_val, list):
                    return field_val in target_val
                return str(field_val) in str(target_val)
            elif op == "contains":
                return str(target_val).lower() in str(field_val).lower()
        except (ValueError, TypeError) as e:
            logger.debug(f"Condition evaluation type error: {e}")
            return False

        return False

    @classmethod
    def match_rule(cls, rule: AlertRule, context: Dict[str, Any]) -> bool:
        """
        Determines whether all conditions in a rule are satisfied by the event context.
        """
        if not rule.enabled:
            return False

        conditions = rule.conditions_json or []
        if not conditions:
            return False

        for cond in conditions:
            field = cond.get("field")
            op = cond.get("op", "==")
            target = cond.get("value")
            field_val = context.get(field)

            if not cls.evaluate_condition(field_val, op, target):
                return False

        return True

    @classmethod
    def evaluate_event_alerts(
        cls,
        db: Session,
        event: ThermalEvent,
        risk_data: Dict[str, Any],
        classification: str,
        spatial_context: Optional[Dict[str, Any]] = None,
        temporal_data: Optional[Dict[str, Any]] = None,
        satellite_data: Optional[Dict[str, Any]] = None
    ) -> List[Alert]:
        """
        Evaluates all enabled alert rules against an event.
        Suppresses duplicate alerts within rule cooldown windows.
        Creates incident payloads, alerts, audit logs, and in-app notifications.
        """
        spatial_context = spatial_context or {}
        temporal_data = temporal_data or {}
        satellite_data = satellite_data or {}

        # 1. Flatten Context for Rule Matching
        nearest_fac = spatial_context.get("nearest_facility") or {}
        dist_m = spatial_context.get("distance_meters") or nearest_fac.get("distance_meters")

        context: Dict[str, Any] = {
            "event_id": event.id,
            "frp": event.frp,
            "confidence": event.confidence,
            "risk_score": risk_data.get("risk_score", 0.0),
            "risk_level": risk_data.get("risk_level", "LOW"),
            "classification": classification,
            "temporal_status": temporal_data.get("status", "NEW"),
            "active_days": temporal_data.get("active_days", 1),
            "persistence": temporal_data.get("status") == "PERSISTENT" or (temporal_data.get("active_days", 1) >= 5),
            "distance_to_facility_meters": dist_m,
            "facility_type": nearest_fac.get("facility_type"),
            "satellite_available": bool(satellite_data.get("available") or satellite_data.get("satellite_evidence_available")),
            "burn_scar": satellite_data.get("indices", {}).get("burn_scar_indicator", False) if isinstance(satellite_data.get("indices"), dict) else False
        }

        # 2. Query enabled rules
        rules = db.query(AlertRule).filter(AlertRule.enabled == True).all()
        created_alerts: List[Alert] = []

        now_utc = datetime.now(timezone.utc)

        # Check if event is a normal persistent operational flare (Section 19)
        risk_reasons = risk_data.get("risk_reasons") or []
        is_normal_operational = "EXPECTED_OPERATIONAL_THERMAL_SOURCE" in risk_reasons

        for rule in rules:
            if not cls.match_rule(rule, context):
                continue

            # Suppress non-critical alerts for verified normal persistent operational industrial sources
            if is_normal_operational and rule.name not in ["CRITICAL_INDUSTRIAL_FIRE"]:
                logger.info(f"Suppressed alert for event {event.id}: normal operational flare ({rule.name})")
                continue

            # 3. Deduplication Check (Cooldown Window)
            cooldown_delta = timedelta(minutes=rule.cooldown_minutes)
            cutoff = now_utc - cooldown_delta

            recent_alert = db.query(Alert).filter(
                Alert.event_id == event.id,
                Alert.rule_id == rule.id,
                Alert.created_at >= cutoff
            ).order_by(Alert.created_at.desc()).first()

            if recent_alert:
                sev_ranks = {"INFO": 0, "LOW": 1, "MODERATE": 2, "MEDIUM": 2, "HIGH": 3, "CRITICAL": 4}
                if sev_ranks.get(str(rule.severity).upper(), 0) <= sev_ranks.get(str(recent_alert.severity).upper(), 0):
                    logger.info(f"Suppressed duplicate alert for event {event.id} and rule {rule.name} (cooldown: {rule.cooldown_minutes}m)")
                    continue

            # 4. Resolve Recommended Recipient & Incident Payload
            routing = ResponseRoutingService.resolve_routing(
                db=db,
                classification=classification,
                severity=rule.severity,
                facility_info=nearest_fac
            )

            # Generate unique alert code
            alert_count = db.query(func.count(Alert.id)).scalar() or 0
            alert_code = f"ALT-2026-{(alert_count + 1):06d}"

            title = f"{rule.severity} Alert: {classification.replace('_', ' ').title()} near {nearest_fac.get('name', 'Industrial Area')}"
            message = (
                f"Thermal anomaly detected with {event.frp:.1f} MW FRP. "
                f"Analytical risk score: {risk_data.get('risk_score', 0):.0f}/100 ({risk_data.get('risk_level')}). "
                f"Recommended action: {routing['recommended_action']}"
            )

            what_changed = (
                "Abnormal thermal surge detected exceeding historical baseline"
                if "ABNORMAL_FRP_SPIKE" in risk_reasons or temporal_data.get("status") == "ABNORMAL"
                else "New thermal anomaly detection requiring initial evaluation"
            )

            incident_payload = {
                "incident_id": alert_code,
                "event_id": event.id,
                "event_code": f"INF-2026-{event.id:06d}",
                "why_alerted": f"Rule {rule.name} matched: {rule.description}",
                "what_changed": what_changed,
                "location": {
                    "latitude": event.latitude,

                    "longitude": event.longitude
                },
                "detection_time": event.detected_at.isoformat() if event.detected_at else now_utc.isoformat(),
                "classification": classification,
                "risk_score": risk_data.get("risk_score", 0.0),
                "risk_level": risk_data.get("risk_level", "LOW"),
                "frp": event.frp,
                "persistence": {
                    "status": temporal_data.get("status", "NEW"),
                    "active_days": temporal_data.get("active_days", 1),
                    "mean_frp": temporal_data.get("mean_frp", event.frp)
                },
                "facility": {
                    "name": nearest_fac.get("name"),
                    "facility_type": nearest_fac.get("facility_type"),
                    "distance_meters": dist_m
                },
                "satellite_evidence": {
                    "available": context["satellite_available"],
                    "burn_scar_indicator": context["burn_scar"],
                    "scene_id": satellite_data.get("scene_id")
                },
                "routing": routing,
                "risk_model_version": risk_data.get("risk_model_version", "risk-v1"),
                "rule_name": rule.name
            }

            alert = Alert(
                alert_code=alert_code,
                event_id=event.id,
                rule_id=rule.id,
                severity=rule.severity,
                title=title,
                message=message,
                status="NEW",
                incident_payload_json=incident_payload,
                created_at=now_utc
            )
            db.add(alert)
            db.commit()
            db.refresh(alert)

            # 5. Record Creation in Audit Log
            cls.log_action(
                db=db,
                alert_id=alert.id,
                actor="AlertEngine",
                action="CREATED",
                previous_status=None,
                new_status="NEW",
                comment=f"Alert generated by rule '{rule.name}'"
            )

            # 6. Dispatch In-App Notification
            try:
                InAppNotificationProvider().send_alert_notification(db, alert)
            except Exception as e:
                logger.error(f"Failed to dispatch in-app notification for alert {alert.id}: {e}")

            created_alerts.append(alert)

        return created_alerts

    @classmethod
    def transition_status(
        cls,
        db: Session,
        alert_id: int,
        target_status: str,
        actor: str = "analyst",
        comment: Optional[str] = None
    ) -> Alert:
        """
        Validates and executes an alert lifecycle status transition.
        """
        alert = db.query(Alert).filter(Alert.id == alert_id).first()
        if not alert:
            raise ValueError(f"Alert with ID {alert_id} not found")

        current_status = alert.status
        allowed = cls.VALID_TRANSITIONS.get(current_status, [])

        if target_status not in allowed:
            raise ValueError(
                f"Invalid transition from {current_status} to {target_status}. "
                f"Permitted next states: {allowed or 'None (Terminal)'}"
            )

        now_utc = datetime.now(timezone.utc)
        alert.status = target_status

        if target_status == "ACKNOWLEDGED":
            alert.acknowledged_at = now_utc
            alert.acknowledged_by = actor
        elif target_status == "ESCALATED":
            alert.escalated_at = now_utc
        elif target_status in ("RESOLVED", "DISMISSED"):
            alert.resolved_at = now_utc
            alert.resolved_by = actor

        db.commit()
        db.refresh(alert)

        # Append to audit trail
        cls.log_action(
            db=db,
            alert_id=alert.id,
            actor=actor,
            action=target_status,
            previous_status=current_status,
            new_status=target_status,
            comment=comment
        )

        return alert

    @classmethod
    def log_action(
        cls,
        db: Session,
        alert_id: int,
        actor: str,
        action: str,
        previous_status: Optional[str] = None,
        new_status: Optional[str] = None,
        comment: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> AlertAuditLog:
        """
        Appends an entry to the alert audit trail.
        """
        log = AlertAuditLog(
            alert_id=alert_id,
            actor=actor,
            action=action,
            previous_status=previous_status,
            new_status=new_status,
            comment=comment,
            metadata_json=metadata or {},
            timestamp=datetime.now(timezone.utc)
        )
        db.add(log)
        db.commit()
        db.refresh(log)
        return log

    @classmethod
    def check_and_escalate_timeouts(
        cls,
        db: Session,
        timeout_minutes: int = 15
    ) -> List[Alert]:
        """
        Auto-escalates unacknowledged CRITICAL or HIGH alerts exceeding the timeout threshold.
        """
        cutoff = datetime.now(timezone.utc) - timedelta(minutes=timeout_minutes)
        unacked = db.query(Alert).filter(
            Alert.status == "NEW",
            Alert.severity.in_(["CRITICAL", "HIGH"]),
            Alert.created_at <= cutoff
        ).all()

        escalated_alerts = []
        for alert in unacked:
            try:
                cls.transition_status(
                    db=db,
                    alert_id=alert.id,
                    target_status="ESCALATED",
                    actor="System-EscalationTimer",
                    comment=f"Auto-escalated: unacknowledged for > {timeout_minutes} minutes"
                )
                escalated_alerts.append(alert)
            except Exception as e:
                logger.error(f"Failed to auto-escalate alert {alert.id}: {e}")

        return escalated_alerts
