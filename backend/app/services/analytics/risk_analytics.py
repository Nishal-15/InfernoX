from datetime import datetime
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.models.risk_alert import RiskAssessment
from app.models.thermal_event import ThermalEvent
from app.schemas.analytics import RiskAnalyticsResponse


class RiskAnalyticsService:
    @staticmethod
    def get_risk_analytics(
        db: Session,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> RiskAnalyticsResponse:
        """
        Aggregate analytical risk scores and severity tiers from real database records.
        """
        query = db.query(RiskAssessment)
        if start_date:
            query = query.filter(RiskAssessment.calculated_at >= start_date)
        if end_date:
            query = query.filter(RiskAssessment.calculated_at <= end_date)

        assessments = query.all()
        total = len(assessments)

        if total == 0:
            # Fallback check on thermal events FRP if no explicit risk assessment records exist yet
            ev_count = db.query(ThermalEvent).count()
            if ev_count > 0:
                events = db.query(ThermalEvent.frp).all()
                frps = [e[0] or 10.0 for e in events]
                sim_scores = [min(round(f * 1.2), 100) for f in frps]
                dist = {"CRITICAL": 0, "HIGH": 0, "MODERATE": 0, "LOW": 0}
                for s in sim_scores:
                    if s >= 75:
                        dist["CRITICAL"] += 1
                    elif s >= 50:
                        dist["HIGH"] += 1
                    elif s >= 25:
                        dist["MODERATE"] += 1
                    else:
                        dist["LOW"] += 1
                avg_s = round(float(sum(sim_scores) / len(sim_scores)), 2)
                max_s = round(float(max(sim_scores)), 2)
                ratio = round(float((dist["CRITICAL"] + dist["HIGH"]) / len(sim_scores)), 3)
                return RiskAnalyticsResponse(
                    distribution=dist,
                    avg_score=avg_s,
                    max_score=max_s,
                    high_critical_ratio=ratio,
                    history_recalculations_count=len(sim_scores)
                )

            return RiskAnalyticsResponse(
                distribution={"CRITICAL": 0, "HIGH": 0, "MODERATE": 0, "LOW": 0},
                avg_score=0.0,
                max_score=0.0,
                high_critical_ratio=0.0,
                history_recalculations_count=0
            )

        dist = {"CRITICAL": 0, "HIGH": 0, "MODERATE": 0, "LOW": 0}
        scores = []
        for a in assessments:
            lvl = (a.risk_level or "LOW").upper()
            dist[lvl] = dist.get(lvl, 0) + 1
            scores.append(float(a.risk_score or 0.0))

        avg_score = round(float(sum(scores) / len(scores)), 2) if scores else 0.0
        max_score = round(float(max(scores)), 2) if scores else 0.0
        high_crit = dist.get("CRITICAL", 0) + dist.get("HIGH", 0)
        ratio = round(float(high_crit / total), 3) if total > 0 else 0.0

        return RiskAnalyticsResponse(
            distribution=dist,
            avg_score=avg_score,
            max_score=max_score,
            high_critical_ratio=ratio,
            history_recalculations_count=total
        )
