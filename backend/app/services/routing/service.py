from typing import Dict, Any, Optional, List
from sqlalchemy.orm import Session
from app.models.risk_alert import ResponseContact


class ResponseRoutingService:
    """
    Determines recommended department/recipient routing for an incident based on
    geographic jurisdiction, classification, facility type, and configured contacts.
    """

    DEFAULT_CATEGORY_MAPPINGS = {
        "INDUSTRIAL_FIRE": "FIRE_EMERGENCY",
        "WILDFIRE": "FOREST",
        "GAS_FLARE": "INDUSTRIAL_SAFETY",
        "PERSISTENT_INDUSTRIAL_THERMAL_SOURCE": "FACILITY_OPERATOR",
        "MINING_ACTIVITY": "INDUSTRIAL_SAFETY",
        "AGRICULTURAL_BURNING": "ENVIRONMENT",
        "OTHER_THERMAL_ANOMALY": "DISASTER_MANAGEMENT",
        "UNKNOWN": "DISASTER_MANAGEMENT"
    }

    ACTION_RECOMMENDATIONS = {
        "CRITICAL": "Immediate incident commander triage. Notify on-site emergency coordinator and verify aerial/satellite confirmation.",
        "HIGH": "Priority investigation. Contact facility safety desk and initiate thermal persistence monitoring.",
        "MODERATE": "Standard operational assessment. Verify spectral indices and proximity boundaries within 2 hours.",
        "LOW": "Routine record. Log anomaly for baseline temporal correlation."
    }

    @classmethod
    def resolve_routing(
        cls,
        db: Session,
        classification: str,
        severity: str,
        facility_info: Optional[Dict[str, Any]] = None,
        jurisdiction: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Calculates recommended recipient, routing reason, and routing status.
        """
        facility_info = facility_info or {}
        class_key = classification.upper() if classification else "UNKNOWN"
        target_department = cls.DEFAULT_CATEGORY_MAPPINGS.get(class_key, "OTHER")

        # 1. Search for configured contact matching jurisdiction and department type
        query = db.query(ResponseContact).filter(
            ResponseContact.enabled == True,
            ResponseContact.department_type == target_department
        )

        if jurisdiction:
            jur_query = query.filter(ResponseContact.jurisdiction.ilike(f"%{jurisdiction}%"))
            contact = jur_query.first()
        else:
            contact = None

        if not contact:
            # Fallback to general/national jurisdiction for that department
            contact = query.filter(ResponseContact.jurisdiction.in_(["National", "GLOBAL", "Default"])).first()

        if not contact:
            # Fallback to any enabled contact
            contact = db.query(ResponseContact).filter(ResponseContact.enabled == True).first()

        # Build response payload
        recommended_action = cls.ACTION_RECOMMENDATIONS.get(severity, cls.ACTION_RECOMMENDATIONS["MODERATE"])

        if contact:
            is_verified = bool(contact.verified)
            routing_status = "CONFIGURED_VERIFIED" if is_verified else "CONFIGURED_UNVERIFIED"
            recipient_name = f"{contact.organization_name} ({contact.department_type})"
            routing_reason = (
                f"Matched configured {contact.department_type} directory entry for {classification} "
                f"in jurisdiction '{contact.jurisdiction}'."
            )
            contact_details = {
                "id": contact.id,
                "organization": contact.organization_name,
                "department": contact.department_type,
                "channel": contact.contact_type,
                "verified": contact.verified
            }
        else:
            routing_status = "DEFAULT_FALLBACK"
            recipient_name = f"Default {target_department} Coordinator"
            routing_reason = f"No configured contact found for {target_department}. Routed to default operational queue."
            contact_details = None

        return {
            "department_type": target_department,
            "recommended_recipient": recipient_name,
            "routing_reason": routing_reason,
            "routing_status": routing_status,
            "recommended_action": recommended_action,
            "contact_details": contact_details
        }
