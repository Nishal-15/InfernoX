import logging
from typing import Optional, List
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.models.incident import ThermalIncident, IncidentEvent
from app.models.thermal_event import ThermalEvent
from app.models.risk_alert import Alert
from app.models.pipeline import AutonomousAuditLog
from app.schemas.incident import (
    ThermalIncidentResponse,
    ThermalIncidentList,
    IncidentStatusUpdate
)
from app.services.websocket.manager import ws_manager

logger = logging.getLogger(__name__)
router = APIRouter()

@router.get("", response_model=ThermalIncidentList)
def list_incidents(
    status: Optional[str] = None,
    severity: Optional[str] = None,
    classification: Optional[str] = None,
    limit: int = Query(25, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db)
):
    """
    Returns paginated list of ThermalIncidents with status, severity, and classification filtering.
    """
    query = db.query(ThermalIncident)
    if status:
        query = query.filter(ThermalIncident.status == status.upper())
    if severity:
        query = query.filter(ThermalIncident.severity == severity.upper())
    if classification:
        query = query.filter(ThermalIncident.classification == classification)

    total = query.count()
    active_count = db.query(ThermalIncident).filter(ThermalIncident.status.in_(["ACTIVE", "MONITORING"])).count()
    critical_count = db.query(ThermalIncident).filter(ThermalIncident.severity == "CRITICAL", ThermalIncident.status != "RESOLVED").count()

    incidents = query.order_by(ThermalIncident.last_detected_at.desc()).offset(offset).limit(limit).all()

    return {
        "items": incidents,
        "total": total,
        "active_count": active_count,
        "critical_count": critical_count
    }

@router.get("/{incident_id}")
def get_incident_detail(incident_id: int, db: Session = Depends(get_db)):
    """
    Returns comprehensive incident dossier including all correlated thermal events and triggered alerts.
    """
    incident = db.query(ThermalIncident).filter(ThermalIncident.id == incident_id).first()
    if not incident:
        raise HTTPException(status_code=404, detail=f"Incident {incident_id} not found")

    events = (
        db.query(ThermalEvent)
        .join(IncidentEvent, IncidentEvent.event_id == ThermalEvent.id)
        .filter(IncidentEvent.incident_id == incident.id)
        .order_by(ThermalEvent.detected_at.asc())
        .all()
    )
    alerts = db.query(Alert).filter(Alert.incident_id == incident.id).order_by(Alert.created_at.desc()).all()

    return {
        "incident": ThermalIncidentResponse.model_validate(incident),
        "events": [
            {
                "id": e.id,
                "event_code": f"INF-2026-{e.id:06d}",
                "latitude": e.latitude,
                "longitude": e.longitude,
                "frp": e.frp,
                "confidence": e.confidence,
                "detected_at": e.detected_at.isoformat() if e.detected_at else None,
                "satellite": e.satellite,
                "status": e.status
            }
            for e in events
        ],
        "alerts": [
            {
                "id": a.id,
                "alert_code": a.alert_code,
                "severity": a.severity,
                "title": a.title,
                "status": a.status,
                "created_at": a.created_at.isoformat() if a.created_at else None
            }
            for a in alerts
        ]
    }

@router.patch("/{incident_id}/status", response_model=ThermalIncidentResponse)
async def update_incident_status(
    incident_id: int,
    req: IncidentStatusUpdate,
    db: Session = Depends(get_db)
):
    """
    Human-in-the-loop: Analyst updates the status of an incident (e.g. ACTIVE -> CONTAINED / RESOLVED).
    Records an auditable human action distinct from autonomous actions.
    """
    incident = db.query(ThermalIncident).filter(ThermalIncident.id == incident_id).first()
    if not incident:
        raise HTTPException(status_code=404, detail=f"Incident {incident_id} not found")

    old_status = incident.status
    incident.status = req.status.upper()
    incident.updated_at = datetime.now(timezone.utc)
    
    summary = dict(incident.incident_summary_json or {})
    if req.analyst_notes:
        notes_list = summary.get("analyst_notes", [])
        notes_list.append({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "status": incident.status,
            "note": req.analyst_notes,
            "analyst": "Analyst-01"
        })
        summary["analyst_notes"] = notes_list
        incident.incident_summary_json = summary

    db.commit()
    db.refresh(incident)

    # Record Human-in-the-loop audit trail
    audit = AutonomousAuditLog(
        action="INCIDENT_STATUS_ANALYST_UPDATE",
        source="HUMAN_ANALYST",
        incident_id=incident.id,
        previous_value={"status": old_status},
        new_value={"status": incident.status, "notes": req.analyst_notes},
        details_json={"updated_by": "Analyst-01"}
    )
    db.add(audit)
    db.commit()

    # Broadcast real-time update
    try:
        await ws_manager.broadcast("incident.updated", {
            "incident_id": incident.id,
            "incident_code": incident.incident_code,
            "status": incident.status,
            "severity": incident.severity,
            "event_count": incident.event_count,
            "risk_score": incident.risk_score
        })
    except Exception as e:
        logger.debug(f"Broadcast error on incident update: {e}")

    return incident
