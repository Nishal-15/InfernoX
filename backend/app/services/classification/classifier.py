from abc import ABC, abstractmethod
import logging
from typing import List, Dict, Any, Tuple
from app.schemas.features import ThermalFeatures
from app.schemas.classification import ClassificationResponse

logger = logging.getLogger(__name__)

class ClassifierInterface(ABC):
    """
    Standard interface for thermal event classifiers.
    Phase 4 ML models (XGBoost, Random Forest) will adhere to this same contract.
    """
    @abstractmethod
    def classify(self, features: ThermalFeatures) -> Dict[str, Any]:
        pass

class PrototypeClassifier(ClassifierInterface):
    """
    Phase 3 Prototype Heuristic Classifier.
    Applies domain rules over physical, spatial, and temporal features
    to categorize events into standard classes with fact-based evidence.
    
    Explicitly labeled as a rule_based_prototype with heuristic confidence.
    """
    MODEL_TYPE = "rule_based_prototype"
    MODEL_VERSION = "phase3-v1.0"

    # Standard Phase 3 Classes
    CLASS_INDUSTRIAL_FIRE = "INDUSTRIAL_FIRE"
    CLASS_PERSISTENT_SOURCE = "PERSISTENT_INDUSTRIAL_THERMAL_SOURCE"
    CLASS_GAS_FLARE = "GAS_FLARE"
    CLASS_WILDFIRE = "WILDFIRE"
    CLASS_AGRICULTURAL_BURNING = "AGRICULTURAL_BURNING"
    CLASS_MINING_ACTIVITY = "MINING_ACTIVITY"
    CLASS_OTHER = "OTHER_THERMAL_ANOMALY"
    CLASS_UNKNOWN = "UNKNOWN"

    def classify(self, features: ThermalFeatures) -> Dict[str, Any]:
        """
        Classifies the thermal features into a standard class and generates evidence factors.
        """
        evidence_factors: List[str] = []
        explanation_items: List[Dict[str, str]] = [] # For backwards compatibility with Phase 2 frontend
        
        classification = self.CLASS_UNKNOWN
        heuristic_confidence = 50.0

        dist_fac = features.distance_to_industrial_facility
        is_near_facility = (dist_fac is not None and dist_fac <= 2000.0)
        is_very_near_fac = (dist_fac is not None and dist_fac <= 500.0)
        fac_type = (features.facility_type or "").lower()
        lc = (features.land_cover_class or "").lower()

        # 1. Evidence gathering from computed features
        evidence_factors.append(f"Thermal cluster has {features.detection_count} detections across {features.active_days} active days (duration: {features.duration_hours} hrs).")
        
        if is_near_facility:
            fac_name = features.nearest_facility_name or "Industrial Facility"
            evidence_factors.append(f"Located {int(dist_fac)}m from {fac_name} ({features.facility_type or 'Industrial site'}).")
            explanation_items.append({"feature": "Facility Proximity", "impact": "High", "text": f"Within {int(dist_fac)}m of {fac_name}"})

        if features.temporal_status == "ABNORMAL":
            evidence_factors.append(f"Thermal anomaly marked ABNORMAL: Current FRP ({features.frp} MW) is {features.frp_deviation_ratio}x historical baseline mean ({features.mean_frp} MW).")
            explanation_items.append({"feature": "FRP Deviation", "impact": "High", "text": f"Current FRP {features.frp} MW is {features.frp_deviation_ratio}x above mean baseline"})
        elif features.temporal_status == "PERSISTENT":
            evidence_factors.append(f"Stable persistent thermal signature detected across {features.active_days} days with FRP variation (std: {features.frp_std} MW).")
            explanation_items.append({"feature": "Persistence", "impact": "High", "text": f"Repeated detections on {features.active_days} separate dates"})

        if features.land_cover_class:
            evidence_factors.append(f"Land cover context classified as '{features.land_cover_class}'.")

        # 2. Heuristic Classification Decision Rules
        
        # Rule A: Industrial Fire (Abnormal spike at or near an industrial plant)
        if features.temporal_status == "ABNORMAL" and (is_near_facility or features.is_industrial_land):
            classification = self.CLASS_INDUSTRIAL_FIRE
            heuristic_confidence = min(96.0, 72.0 + (features.frp_deviation_ratio * 4.0))
            evidence_factors.append("Sudden high thermal intensity deviation co-located with industrial infrastructure indicates possible industrial incident.")

        # Rule B: Gas Flare / Stack (Highly localized, refinery/chemical/petrochemical, recurring/persistent)
        elif is_very_near_fac and ("refinery" in fac_type or "chemical" in fac_type or "petro" in fac_type or "oil" in fac_type) and features.spatial_spread_meters <= 400.0:
            classification = self.CLASS_GAS_FLARE
            heuristic_confidence = min(92.0, 75.0 + min(15.0, features.active_days * 1.5))
            evidence_factors.append(f"Tight spatial clustering ({features.spatial_spread_meters}m spread) at refinery/petrochemical facility is characteristic of flare stack operation.")

        # Rule C: Persistent Industrial Thermal Source (Continuous active days at industrial site)
        elif features.temporal_status == "PERSISTENT" and (is_near_facility or features.is_industrial_land):
            classification = self.CLASS_PERSISTENT_SOURCE
            heuristic_confidence = min(95.0, 80.0 + min(12.0, features.active_days * 0.8))
            evidence_factors.append("Long-term spatial and temporal stability confirms ongoing persistent industrial thermal operations.")

        # Rule D: Mining Activity
        elif is_near_facility and ("quarry" in fac_type or "mine" in fac_type or "kiln" in fac_type or "cement" in fac_type):
            classification = self.CLASS_MINING_ACTIVITY
            heuristic_confidence = 82.0
            evidence_factors.append("Observation spatial coordinates align with documented mining/quarry/kiln facility tags.")

        # Rule E: Agricultural Burning (Cropland land cover, short duration, low/moderate FRP)
        elif ("crop" in lc or "agri" in lc) and not is_near_facility and features.temporal_status in ["NEW", "RECURRING"]:
            classification = self.CLASS_AGRICULTURAL_BURNING
            heuristic_confidence = 78.0
            evidence_factors.append("Location matches agricultural cropland with moderate seasonal thermal signature.")
            explanation_items.append({"feature": "Land Cover", "impact": "Medium", "text": "Agricultural land cover signature"})

        # Rule F: Wildfire (Forest/woodland/shrubland, large spatial spread, high FRP)
        elif ("forest" in lc or "woodland" in lc or "shrub" in lc) and not is_near_facility:
            classification = self.CLASS_WILDFIRE
            heuristic_confidence = 80.0
            evidence_factors.append("Thermal signature located in forest/woodland cover with no nearby industrial facilities.")
            explanation_items.append({"feature": "Natural Setting", "impact": "Medium", "text": "Located in forest/woodland terrain"})

        # Rule G: General Industrial Proximity (Unconfirmed anomaly)
        elif is_near_facility and features.temporal_status == "NEW":
            if features.frp > 100.0:
                classification = self.CLASS_INDUSTRIAL_FIRE
                heuristic_confidence = 65.0
                evidence_factors.append("Initial high-intensity observation in immediate proximity to industrial installation requires investigation.")
            else:
                classification = self.CLASS_OTHER
                heuristic_confidence = 55.0
                evidence_factors.append("Low-intensity new thermal anomaly near industrial site with insufficient history to confirm baseline.")

        # Rule H: Unknown / Insufficient Data
        elif features.detection_count <= 1 and (features.confidence is None or features.confidence < 50.0):
            classification = self.CLASS_UNKNOWN
            heuristic_confidence = 40.0
            evidence_factors.append("Single observation with low satellite confidence score; insufficient evidence for positive classification.")
        else:
            classification = self.CLASS_OTHER
            heuristic_confidence = 50.0
            evidence_factors.append("Observation exhibits generic thermal anomaly characteristics without strong class alignment.")

        return {
            "classification": classification,
            "confidence_score": round(heuristic_confidence, 1),
            "confidence_type": "heuristic",
            "model_type": self.MODEL_TYPE,
            "model_version": self.MODEL_VERSION,
            "evidence_factors": evidence_factors,
            "explanation": explanation_items
        }
