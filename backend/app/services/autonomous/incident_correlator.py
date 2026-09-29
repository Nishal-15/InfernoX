import math
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional, Tuple, List
from sqlalchemy.orm import Session
from sqlalchemy import text, func

from app.models.thermal_event import ThermalEvent
from app.models.incident import ThermalIncident, IncidentEvent
from app.models.pipeline import AutonomousAuditLog
from app.core.config import settings

logger = logging.getLogger(__name__)

class IncidentCorrelator:
    """
    Geospatial Thermal Incident Correlation Engine.
    Correlates continuous FIRMS thermal detections into high-level ThermalIncidents.
    Prevents alert storms by clustering observations within spatial proximity (1.5 km),
    temporal activity window (48 hours), or identical industrial facility footprint.
    """

    def __init__(
        self,
        spatial_threshold_m: float = 1500.0,
        temporal_window_hours: float = 48.0
    ):
        self.spatial_threshold_m = spatial_threshold_m
        self.temporal_window_hours = temporal_window_hours

    def correlate_in_memory(
        self,
        event: Dict[str, Any],
        existing_incidents: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """
        Pure algorithmic correlation without active database requirement.
        """
        existing_incidents = existing_incidents or []
        ev_fac = event.get("facility_id")
        ev_lat = float(event.get("latitude") or 0.0)
        ev_lon = float(event.get("longitude") or 0.0)

        # 1. Facility footprint match
        if ev_fac is not None:
            for inc in existing_incidents:
                if inc.get("facility_id") == ev_fac:
                    return {
                        "is_new_incident": False,
                        "incident_id": inc.get("id"),
                        "correlation_confidence": 0.95,
                        "correlation_reason": "facility_footprint_match"
                    }

        # 2. Spatial proximity match
        for inc in existing_incidents:
            c_lat = float(inc.get("centroid_latitude") or 0.0)
            c_lon = float(inc.get("centroid_longitude") or 0.0)
            dlat = (c_lat - ev_lat) * 111000.0
            dlon = (c_lon - ev_lon) * 111000.0 * math.cos(math.radians(ev_lat))
            dist = math.sqrt(dlat**2 + dlon**2)
            if dist <= self.spatial_threshold_m:
                return {
                    "is_new_incident": False,
                    "incident_id": inc.get("id"),
                    "correlation_confidence": 0.85,
                    "correlation_reason": "spatial_cluster_proximity"
                }

        # 3. New incident
        return {
            "is_new_incident": True,
            "incident_id": None,
            "correlation_confidence": 1.0,
            "correlation_reason": "new_incident_created"
        }

    @classmethod
    def correlate_event(
        cls,
        db: Any = None,
        event: Any = None,
        classification: str = "UNKNOWN",
        risk_score: float = 0.0,
        risk_level: str = "LOW",
        spatial_context: Optional[Dict[str, Any]] = None,
        correlation_id: Optional[str] = None,
        *args,
        **kwargs
    ) -> Any:
        """
        Dual entrypoint:
          1. DB pipeline: correlate_event(db, event, classification, risk_score, risk_level, ...)
          2. In-memory:   correlate_event(event, existing_incidents)
        """
        # In-memory check: if db is not a database Session
        if db is not None and (isinstance(db, dict) or not hasattr(db, "query")):
            inst = cls()
            existing_incidents = event if isinstance(event, list) else kwargs.get("existing_incidents", [])
            return inst.correlate_in_memory(db, existing_incidents)

        spatial_context = spatial_context or {}

        nearest_fac = spatial_context.get("nearest_facility") or {}
        fac_id = nearest_fac.get("id")
        fac_name = nearest_fac.get("name")
        dist_m = spatial_context.get("distance_meters") or nearest_fac.get("distance_meters")

        radius_m = settings.INCIDENT_CORRELATION_RADIUS_METERS
        lookback_hrs = settings.INCIDENT_CORRELATION_HOURS
        cutoff_time = (event.detected_at or datetime.now(timezone.utc)) - timedelta(hours=lookback_hrs)

        # 1. Search for matching active incident
        existing_incident: Optional[ThermalIncident] = None
        correlation_reason = "NEW_SPATIAL_CLUSTER_INITIATED"

        # Check by facility first if within 500m
        if fac_id and dist_m is not None and dist_m <= 500.0:
            existing_incident = db.query(ThermalIncident).filter(
                ThermalIncident.primary_facility_id == fac_id,
                ThermalIncident.status.in_(["ACTIVE", "MONITORING"]),
                ThermalIncident.last_detected_at >= cutoff_time
            ).order_by(ThermalIncident.last_detected_at.desc()).first()
            if existing_incident:
                correlation_reason = "FACILITY_FOOTPRINT_MATCH"

        # If not found by facility, search by PostGIS / Haversine spatial proximity
        if not existing_incident:
            point_geom = f"SRID=4326;POINT({event.longitude} {event.latitude})"
            try:
                existing_incident = db.query(ThermalIncident).filter(
                    ThermalIncident.status.in_(["ACTIVE", "MONITORING"]),
                    ThermalIncident.last_detected_at >= cutoff_time,
                    text(f"ST_DWithin(geometry::geography, ST_GeomFromEWKT('{point_geom}')::geography, {radius_m})")
                ).order_by(ThermalIncident.last_detected_at.desc()).first()
                if existing_incident:
                    correlation_reason = "SPATIAL_CLUSTER_PROXIMITY"
            except Exception:
                # SQLite fallback
                active_incidents = db.query(ThermalIncident).filter(
                    ThermalIncident.status.in_(["ACTIVE", "MONITORING"]),
                    ThermalIncident.last_detected_at >= cutoff_time
                ).all()
                
                for inc in active_incidents:
                    dlat = (inc.centroid_latitude - event.latitude) * 111000
                    dlon = (inc.centroid_longitude - event.longitude) * 111000 * math.cos(math.radians(event.latitude))
                    dist = math.sqrt(dlat**2 + dlon**2)
                    if dist <= radius_m:
                        existing_incident = inc
                        correlation_reason = "SPATIAL_CLUSTER_PROXIMITY"
                        break

        # 2. Update existing incident or create new
        now_utc = datetime.now(timezone.utc)
        ev_frp = float(event.frp or 0.0)

        if existing_incident:
            # Update incident aggregates
            old_count = existing_incident.event_count
            new_count = old_count + 1
            existing_incident.event_count = new_count
            
            if event.detected_at and event.detected_at > existing_incident.last_detected_at:
                existing_incident.last_detected_at = event.detected_at
            
            duration_secs = (existing_incident.last_detected_at - existing_incident.first_detected_at).total_seconds()
            existing_incident.duration_hours = round(max(0.0, duration_secs / 3600.0), 1)
            
            existing_incident.peak_frp = max(existing_incident.peak_frp, ev_frp)
            existing_incident.mean_frp = round(((existing_incident.mean_frp * old_count) + ev_frp) / new_count, 1)
            
            if risk_score > existing_incident.risk_score:
                existing_incident.risk_score = risk_score
                existing_incident.risk_level = risk_level
            
            # Elevate severity if high risk
            if risk_level == "CRITICAL":
                existing_incident.severity = "CRITICAL"
            elif risk_level == "HIGH" and existing_incident.severity not in ["CRITICAL"]:
                existing_incident.severity = "HIGH"

            # Recalculate centroid
            existing_incident.centroid_latitude = round((existing_incident.centroid_latitude * old_count + event.latitude) / new_count, 6)
            existing_incident.centroid_longitude = round((existing_incident.centroid_longitude * old_count + event.longitude) / new_count, 6)
            
            # Correlation confidence rating
            corr_conf = 0.95 if correlation_reason == "FACILITY_FOOTPRINT_MATCH" else 0.85

            # Update incident summary with latest correlation reason and confidence
            summary = dict(existing_incident.incident_summary_json or {})
            summary["latest_correlation_reason"] = correlation_reason
            summary["correlation_confidence"] = corr_conf
            summary["last_correlated_event_id"] = event.id
            existing_incident.incident_summary_json = summary

            existing_incident.updated_at = now_utc

            # Link event via IncidentEvent association
            existing_assoc = db.query(IncidentEvent).filter(
                IncidentEvent.incident_id == existing_incident.id,
                IncidentEvent.event_id == event.id
            ).first()
            if not existing_assoc:
                db.add(IncidentEvent(incident_id=existing_incident.id, event_id=event.id))
            event.incident_id = existing_incident.id
            db.commit()
            db.refresh(existing_incident)

            # Audit log
            audit = AutonomousAuditLog(
                correlation_id=correlation_id,
                action="INCIDENT_CORRELATED",
                source="AUTONOMOUS_PIPELINE",
                event_id=event.id,
                incident_id=existing_incident.id,
                new_value={"event_count": new_count, "peak_frp": existing_incident.peak_frp, "risk_score": existing_incident.risk_score},
                details_json={
                    "incident_code": existing_incident.incident_code,
                    "correlation_reason": correlation_reason,
                    "correlation_confidence": corr_conf
                }
            )
            db.add(audit)
            db.commit()

            logger.info(f"Correlated event {event.id} into incident {existing_incident.incident_code} ({correlation_reason}, conf: {corr_conf}, total events: {new_count})")
            return existing_incident



        else:
            # Create new Incident
            inc_count = db.query(func.count(ThermalIncident.id)).scalar() or 0
            inc_code = f"INC-2026-{(inc_count + 1):06d}"
            
            title = f"Thermal Incident: {classification.replace('_', ' ').title()}"
            if fac_name:
                title += f" near {fac_name}"

            new_incident = ThermalIncident(
                incident_code=inc_code,
                title=title,
                status="ACTIVE",
                severity=risk_level if risk_level in ["CRITICAL", "HIGH", "MODERATE", "LOW"] else "MODERATE",
                classification=classification,
                first_detected_at=event.detected_at or now_utc,
                last_detected_at=event.detected_at or now_utc,
                duration_hours=0.0,
                event_count=1,
                peak_frp=ev_frp,
                mean_frp=ev_frp,
                risk_score=risk_score,
                risk_level=risk_level,
                primary_facility_id=fac_id,
                primary_facility_name=fac_name,
                distance_to_facility_meters=round(float(dist_m), 1) if dist_m is not None else None,
                centroid_latitude=event.latitude,
                centroid_longitude=event.longitude,
                geometry=f"SRID=4326;POINT({event.longitude} {event.latitude})",
                incident_summary_json={
                    "initial_event_id": event.id,
                    "satellite": event.satellite,
                    "confidence": event.confidence,
                    "correlation_reason": "NEW_SPATIAL_CLUSTER_INITIATED",
                    "correlation_confidence": 1.0,
                    "created_by": "AUTONOMOUS_PIPELINE"
                },
                created_at=now_utc,
                updated_at=now_utc

            )
            db.add(new_incident)
            db.commit()
            db.refresh(new_incident)

            # Link event via IncidentEvent association
            db.add(IncidentEvent(incident_id=new_incident.id, event_id=event.id))
            event.incident_id = new_incident.id
            db.commit()

            # Audit log
            audit = AutonomousAuditLog(
                correlation_id=correlation_id,
                action="INCIDENT_CREATED",
                source="AUTONOMOUS_PIPELINE",
                event_id=event.id,
                incident_id=new_incident.id,
                new_value={"incident_code": inc_code, "risk_score": risk_score, "severity": new_incident.severity},
                details_json={"classification": classification, "facility": fac_name}
            )
            db.add(audit)
            db.commit()

            logger.info(f"Created new incident {inc_code} for event {event.id}")
            return new_incident
