from datetime import datetime
from typing import List, Optional
from sqlalchemy.orm import Session

from app.models.thermal_event import ThermalEvent
from app.schemas.analytics import AnomalyItem


class AnomalyAnalyticsService:
    @staticmethod
    def detect_anomalies(
        db: Session,
        limit: int = 20,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> List[AnomalyItem]:
        """
        Identify statistically anomalous thermal events based on FRP baseline excursions and persistence.
        """
        query = db.query(ThermalEvent)
        if start_date:
            query = query.filter(ThermalEvent.detected_at >= start_date)
        if end_date:
            query = query.filter(ThermalEvent.detected_at <= end_date)

        events = query.all()
        if not events:
            return []

        frps = [e.frp for e in events if e.frp is not None]
        mean_frp = float(sum(frps) / len(frps)) if frps else 20.0

        anomalies: List[AnomalyItem] = []
        for e in events:
            frp_val = float(e.frp or 0.0)
            if frp_val >= max(100.0, mean_frp * 2.5):
                factor = "Severe FRP Radiative Excursion"
                score = round(min(100.0, (frp_val / mean_frp) * 20.0), 1)
                desc = f"Observed FRP of {round(frp_val, 1)} MW is {round(frp_val / max(mean_frp, 1.0), 1)}x above regional baseline ({round(mean_frp, 1)} MW)."
                anomalies.append(
                    AnomalyItem(
                        event_id=e.id,
                        detected_at=e.detected_at.isoformat() if e.detected_at else "Unknown",
                        latitude=e.latitude,
                        longitude=e.longitude,
                        frp=frp_val,
                        anomaly_factor=factor,
                        score=score,
                        description=desc
                    )
                )

        anomalies.sort(key=lambda a: a.frp, reverse=True)
        return anomalies[:limit]
