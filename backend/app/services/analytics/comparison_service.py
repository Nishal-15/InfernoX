from datetime import datetime
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session

from app.models.facility import Facility
from app.models.thermal_event import ThermalEvent
from app.models.risk_alert import RiskAssessment, Alert
from app.schemas.analytics import ComparisonResponse, ComparisonTarget


class ComparisonService:
    @staticmethod
    def compare_facilities(
        db: Session,
        facility_id_a: int,
        facility_id_b: int
    ) -> ComparisonResponse:
        """
        Factual side-by-side comparison between two industrial plants.
        """
        fac_a = db.query(Facility).filter(Facility.id == facility_id_a).first()
        fac_b = db.query(Facility).filter(Facility.id == facility_id_b).first()

        def get_fac_stats(fac: Optional[Facility]) -> Dict[str, Any]:
            if not fac:
                return {
                    "total_events": 0,
                    "avg_frp": 0.0,
                    "max_frp": 0.0,
                    "persistent_sources": 0,
                    "high_risk_events": 0
                }
            events = db.query(ThermalEvent).all()
            nearby = [e for e in events if abs(e.latitude - fac.latitude) <= 0.045 and abs(e.longitude - fac.longitude) <= 0.045]
            frps = [e.frp for e in nearby if e.frp is not None]
            avg_f = round(float(sum(frps) / len(frps)), 1) if frps else 0.0
            max_f = round(float(max(frps)), 1) if frps else 0.0
            persistent = sum(1 for e in nearby if (e.confidence or 0) > 80 and (e.frp or 0) > 40)
            high_risk = sum(1 for e in nearby if (e.frp or 0) >= 60)
            return {
                "total_events": len(nearby),
                "avg_frp": avg_f,
                "max_frp": max_f,
                "persistent_sources": persistent,
                "high_risk_events": high_risk
            }

        stats_a = get_fac_stats(fac_a)
        stats_b = get_fac_stats(fac_b)

        delta = {
            "event_count_diff": stats_a["total_events"] - stats_b["total_events"],
            "avg_frp_diff": round(stats_a["avg_frp"] - stats_b["avg_frp"], 1),
            "max_frp_diff": round(stats_a["max_frp"] - stats_b["max_frp"], 1),
            "persistent_sources_diff": stats_a["persistent_sources"] - stats_b["persistent_sources"],
            "high_risk_diff": stats_a["high_risk_events"] - stats_b["high_risk_events"]
        }

        narratives = [
            f"{fac_a.name if fac_a else 'Facility A'} recorded {stats_a['total_events']} nearby thermal events vs {stats_b['total_events']} for {fac_b.name if fac_b else 'Facility B'}.",
            f"Average FRP delta is {delta['avg_frp_diff']} MW; peak FRP delta is {delta['max_frp_diff']} MW.",
            f"Persistent thermal source delta: {delta['persistent_sources_diff']} sources."
        ]

        return ComparisonResponse(
            comparison_type="FACILITY",
            target_a=ComparisonTarget(
                label=fac_a.name if fac_a else "Facility A",
                identifier=str(facility_id_a),
                metrics=stats_a
            ),
            target_b=ComparisonTarget(
                label=fac_b.name if fac_b else "Facility B",
                identifier=str(facility_id_b),
                metrics=stats_b
            ),
            delta_metrics=delta,
            analysis_narrative=narratives
        )

    @staticmethod
    def compare_timeframes(
        db: Session,
        period_a_start: datetime,
        period_a_end: datetime,
        period_b_start: datetime,
        period_b_end: datetime
    ) -> ComparisonResponse:
        """
        Factual comparison between two distinct historical observation periods.
        """
        def get_period_stats(s: datetime, e: datetime) -> Dict[str, Any]:
            events = db.query(ThermalEvent).filter(
                ThermalEvent.detected_at >= s,
                ThermalEvent.detected_at <= e
            ).all()
            frps = [ev.frp for ev in events if ev.frp is not None]
            avg_f = round(float(sum(frps) / len(frps)), 1) if frps else 0.0
            max_f = round(float(max(frps)), 1) if frps else 0.0
            high_risk = sum(1 for ev in events if (ev.frp or 0) >= 60)
            return {
                "total_events": len(events),
                "avg_frp": avg_f,
                "max_frp": max_f,
                "high_risk_events": high_risk
            }

        stats_a = get_period_stats(period_a_start, period_a_end)
        stats_b = get_period_stats(period_b_start, period_b_end)

        delta = {
            "event_count_diff": stats_a["total_events"] - stats_b["total_events"],
            "avg_frp_diff": round(stats_a["avg_frp"] - stats_b["avg_frp"], 1),
            "max_frp_diff": round(stats_a["max_frp"] - stats_b["max_frp"], 1),
            "high_risk_diff": stats_a["high_risk_events"] - stats_b["high_risk_events"]
        }

        lbl_a = f"{period_a_start.strftime('%Y-%m-%d')} to {period_a_end.strftime('%Y-%m-%d')}"
        lbl_b = f"{period_b_start.strftime('%Y-%m-%d')} to {period_b_end.strftime('%Y-%m-%d')}"

        narratives = [
            f"Period A ({lbl_a}) had {stats_a['total_events']} events vs {stats_b['total_events']} in Period B ({lbl_b}).",
            f"Thermal energy disparity: Mean FRP delta of {delta['avg_frp_diff']} MW and peak FRP delta of {delta['max_frp_diff']} MW."
        ]

        return ComparisonResponse(
            comparison_type="TIME_PERIOD",
            target_a=ComparisonTarget(label=lbl_a, identifier="period_a", metrics=stats_a),
            target_b=ComparisonTarget(label=lbl_b, identifier="period_b", metrics=stats_b),
            delta_metrics=delta,
            analysis_narrative=narratives
        )
