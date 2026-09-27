from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.models.facility import Facility
from app.models.thermal_event import ThermalEvent
from app.models.risk_alert import Alert, RiskAssessment
from app.schemas.analytics import FacilityMetric, FacilityTimelineNode


class FacilityAnalyticsService:
    @staticmethod
    def get_facilities_ranking(
        db: Session,
        facility_type: Optional[str] = None,
        min_events: int = 0,
        limit: int = 50
    ) -> List[FacilityMetric]:
        """
        Rank industrial facilities by thermal activity, persistent sources, and high-risk events.
        """
        fac_query = db.query(Facility)
        if facility_type:
            fac_query = fac_query.filter(Facility.facility_type.ilike(f"%{facility_type}%"))

        facilities = fac_query.limit(100).all()
        if not facilities:
            return []

        all_events = db.query(
            ThermalEvent.id,
            ThermalEvent.latitude,
            ThermalEvent.longitude,
            ThermalEvent.frp,
            ThermalEvent.detected_at,
            ThermalEvent.confidence
        ).all()

        # Map risks and alerts
        high_risk_event_ids = set()
        risks = db.query(RiskAssessment.event_id, RiskAssessment.risk_level).all()
        for r_eid, r_lvl in risks:
            if (r_lvl or "").upper() in ("CRITICAL", "HIGH"):
                high_risk_event_ids.add(r_eid)

        alerts = db.query(Alert.event_id, Alert.severity).all()
        crit_alert_event_ids = set(a_eid for a_eid, sev in alerts if (sev or "").upper() == "CRITICAL")

        results: List[FacilityMetric] = []

        for fac in facilities:
            fac_lat = fac.latitude
            fac_lon = fac.longitude
            
            # 5km approx bounding box filter (~0.05 degrees)
            nearby = []
            for ev in all_events:
                eid, e_lat, e_lon, frp, dt, conf = ev
                if abs(e_lat - fac_lat) <= 0.045 and abs(e_lon - fac_lon) <= 0.045:
                    nearby.append(ev)

            nearby_count = len(nearby)
            if nearby_count < min_events:
                continue

            frps = [e[3] for e in nearby if e[3] is not None]
            avg_frp = round(float(sum(frps) / len(frps)), 2) if frps else 0.0
            max_frp = round(float(max(frps)), 2) if frps else 0.0
            
            persistent_count = sum(1 for e in nearby if (e[5] or 0) > 80 and (e[3] or 0) > 40)
            high_risk_count = sum(1 for e in nearby if e[0] in high_risk_event_ids or (e[3] or 0) >= 60)
            crit_alerts = sum(1 for e in nearby if e[0] in crit_alert_event_ids)

            latest_dt = None
            dts = [e[4] for e in nearby if e[4] is not None]
            if dts:
                latest_dt = max(dts).isoformat()

            results.append(
                FacilityMetric(
                    facility_id=fac.id,
                    osm_id=fac.osm_id,
                    name=fac.name or f"Industrial Facility #{fac.id}",
                    facility_type=fac.facility_type or "Industrial",
                    latitude=fac.latitude,
                    longitude=fac.longitude,
                    operator=fac.operator,
                    total_nearby_events=nearby_count,
                    avg_frp=avg_frp,
                    max_frp=max_frp,
                    persistent_sources=persistent_count,
                    high_risk_events=high_risk_count,
                    critical_alerts=crit_alerts,
                    last_detected_at=latest_dt
                )
            )

        results.sort(key=lambda x: (x.critical_alerts, x.high_risk_events, x.total_nearby_events), reverse=True)
        return results[:limit]

    @staticmethod
    def get_facility_thermal_timeline(
        db: Session,
        facility_id: int,
        days: int = 90
    ) -> List[FacilityTimelineNode]:
        """
        Chronological thermal detection history for a specific industrial plant.
        """
        fac = db.query(Facility).filter(Facility.id == facility_id).first()
        if not fac:
            return []

        since = datetime.now() - timedelta(days=days)
        events = db.query(ThermalEvent).filter(
            ThermalEvent.detected_at >= since
        ).all()

        nearby = []
        for e in events:
            if abs(e.latitude - fac.latitude) <= 0.045 and abs(e.longitude - fac.longitude) <= 0.045:
                nearby.append(e)

        nearby.sort(key=lambda x: x.detected_at or datetime.min)

        timeline: List[FacilityTimelineNode] = []
        for ev in nearby:
            date_str = ev.detected_at.strftime("%Y-%m-%d") if ev.detected_at else "Unknown"
            frp_val = float(ev.frp or 0.0)
            has_high_risk = frp_val >= 60.0
            st = "CRITICAL" if frp_val >= 80 else ("HIGH" if frp_val >= 50 else "MODERATE")
            desc = f"Thermal anomaly detected ({round(frp_val)} MW FRP) near {fac.name or 'facility'}."

            timeline.append(
                FacilityTimelineNode(
                    date=date_str,
                    event_count=1,
                    max_frp=round(frp_val, 1),
                    has_high_risk=has_high_risk,
                    status=st,
                    description=desc
                )
            )

        return timeline
