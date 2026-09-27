import logging
from typing import Dict, Any, Tuple
from app.schemas.features import ThermalFeatures

logger = logging.getLogger(__name__)

class PriorityEngine:
    """
    Dedicated Operational Urgency & Priority Engine for Phase 3.
    Separates 'What is this event?' (Classification) from
    'How urgently should an analyst investigate it?' (Priority/Risk).
    """

    CRITICAL_THRESHOLD = 80.0
    HIGH_THRESHOLD = 60.0
    MEDIUM_THRESHOLD = 30.0

    @classmethod
    def evaluate_priority(cls, features: ThermalFeatures, classification: str) -> Tuple[float, str]:
        """
        Calculates priority score (0.0 to 100.0) and assigns priority level
        (LOW, MEDIUM, HIGH, CRITICAL).
        """
        score = 10.0 # Base minimum score

        # 1. Temporal abnormality factor (max +35 pts)
        if features.temporal_status == "ABNORMAL":
            dev = features.frp_deviation_ratio
            score += min(35.0, 15.0 + (dev * 5.0))
        elif features.temporal_status == "NEW":
            score += 10.0 # New unclassified events warrant initial triage

        # 2. Industrial infrastructure proximity factor (max +25 pts)
        dist = features.distance_to_industrial_facility
        if dist is not None:
            if dist <= 300.0:
                score += 25.0
            elif dist <= 1000.0:
                score += 18.0
            elif dist <= 2500.0:
                score += 10.0

        # 3. FRP Magnitude factor (max +20 pts)
        frp = features.frp
        if frp >= 500.0:
            score += 20.0
        elif frp >= 200.0:
            score += 15.0
        elif frp >= 50.0:
            score += 8.0

        # 4. Classification-specific risk factor (max +20 pts / -15 pts)
        if classification == "INDUSTRIAL_FIRE":
            score += 20.0
        elif classification == "GAS_FLARE":
            # Routine industrial operations pose low immediate dispatch urgency
            score -= 15.0
        elif classification == "PERSISTENT_INDUSTRIAL_THERMAL_SOURCE":
            # Known persistent thermal source is monitored but lower urgency unless abnormal
            if features.temporal_status != "ABNORMAL":
                score -= 10.0
        elif classification == "AGRICULTURAL_BURNING":
            score -= 10.0

        # 5. Clamp score between 0.0 and 100.0
        score = max(0.0, min(100.0, round(score, 1)))

        # 6. Assign Level
        if score >= cls.CRITICAL_THRESHOLD:
            level = "CRITICAL"
        elif score >= cls.HIGH_THRESHOLD:
            level = "HIGH"
        elif score >= cls.MEDIUM_THRESHOLD:
            level = "MEDIUM"
        else:
            level = "LOW"

        return score, level
