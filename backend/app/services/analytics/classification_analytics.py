from datetime import datetime
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.models.thermal_event import ThermalEvent
from app.models.ai_models import EventAssessment
from app.models.risk_alert import RiskAssessment
from app.schemas.analytics import ClassificationMetric, ClassificationAnalyticsResponse


class ClassificationAnalyticsService:
    @staticmethod
    def get_classification_breakdown(
        db: Session,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        risk_level: Optional[str] = None
    ) -> ClassificationAnalyticsResponse:
        """
        Aggregate thermal event intelligence by classification from actual database records.
        """
        # Join ThermalEvent with EventAssessment
        query = db.query(
            ThermalEvent.id,
            ThermalEvent.frp,
            ThermalEvent.confidence,
            EventAssessment.classification,
            EventAssessment.confidence_score,
            EventAssessment.priority_level
        ).outerjoin(
            EventAssessment, ThermalEvent.id == EventAssessment.event_id
        )

        if start_date:
            query = query.filter(ThermalEvent.detected_at >= start_date)
        if end_date:
            query = query.filter(ThermalEvent.detected_at <= end_date)

        rows = query.all()
        total_rows = len(rows)
        if total_rows == 0:
            return ClassificationAnalyticsResponse(items=[], total_classified=0)

        # Get risk levels
        event_ids = [r[0] for r in rows]
        risk_map = {}
        if event_ids:
            risks = db.query(RiskAssessment.event_id, RiskAssessment.risk_level).filter(
                RiskAssessment.event_id.in_(event_ids)
            ).all()
            for r_eid, r_lvl in risks:
                risk_map[r_eid] = (r_lvl or "LOW").upper()

        grouped: Dict[str, List[Any]] = {}
        for row in rows:
            eid, frp, conf, classification, ai_conf, priority_lvl = row
            cls_name = classification or "UNKNOWN"
            # Normalize class names
            cls_name = cls_name.replace("_", " ").title()
            if cls_name not in grouped:
                grouped[cls_name] = []
            
            # Determine effective risk level
            r_lvl = risk_map.get(eid) or (priority_lvl or "LOW").upper()
            if risk_level and r_lvl != risk_level.upper():
                continue

            grouped[cls_name].append({
                "frp": frp or 0.0,
                "confidence": ai_conf if ai_conf is not None else (conf or 0.0),
                "risk_level": r_lvl
            })

        items: List[ClassificationMetric] = []
        classified_count = sum(len(v) for v in grouped.values())

        for cls_name, records in sorted(grouped.items(), key=lambda x: len(x[1]), reverse=True):
            if not records:
                continue
            cnt = len(records)
            frp_vals = [r["frp"] for r in records]
            conf_vals = [r["confidence"] for r in records]

            avg_frp = round(float(sum(frp_vals) / cnt), 2) if cnt > 0 else 0.0
            max_frp = round(float(max(frp_vals)), 2) if cnt > 0 else 0.0
            avg_conf = round(float(sum(conf_vals) / cnt), 2) if cnt > 0 else 0.0
            pct = round(float((cnt / classified_count) * 100), 1) if classified_count > 0 else 0.0

            risk_dist = {"CRITICAL": 0, "HIGH": 0, "MODERATE": 0, "LOW": 0}
            for r in records:
                rl = r["risk_level"]
                risk_dist[rl] = risk_dist.get(rl, 0) + 1

            persistent_count = sum(1 for r in records if r["frp"] >= 40.0)

            items.append(
                ClassificationMetric(
                    classification=cls_name,
                    count=cnt,
                    percentage=pct,
                    avg_frp=avg_frp,
                    max_frp=max_frp,
                    avg_confidence=avg_conf,
                    risk_distribution=risk_dist,
                    persistent_count=persistent_count
                )
            )

        return ClassificationAnalyticsResponse(
            items=items,
            total_classified=classified_count
        )
