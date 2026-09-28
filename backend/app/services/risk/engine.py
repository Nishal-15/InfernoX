from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Tuple
from sqlalchemy.orm import Session

from app.models.risk_alert import RiskAssessment


class RiskEngine:
    """
    Dedicated analytical Risk Engine for InfernoX.
    Computes a normalized 0–100 risk score and factor breakdown from multimodal
    thermal telemetry, spatial context, temporal behavior, and satellite evidence.
    
    Categories:
      0–24:   LOW
      25–49:  MODERATE
      50–74:  HIGH
      75–100: CRITICAL
    """
    MODEL_VERSION = "risk-v1"

    # Default Configurable Thresholds
    THRESHOLDS = {
        "LOW": (0.0, 24.9),
        "MODERATE": (25.0, 49.9),
        "HIGH": (50.0, 74.9),
        "CRITICAL": (75.0, 100.0)
    }

    # Classification Base Risk Weights (Max 35 pts)
    CLASSIFICATION_WEIGHTS: Dict[str, float] = {
        "INDUSTRIAL_FIRE": 35.0,
        "WILDFIRE": 28.0,
        "GAS_FLARE": 14.0,
        "PERSISTENT_INDUSTRIAL_THERMAL_SOURCE": 16.0,
        "MINING_ACTIVITY": 15.0,
        "AGRICULTURAL_BURNING": 10.0,
        "OTHER_THERMAL_ANOMALY": 8.0,
        "UNKNOWN": 5.0
    }

    @classmethod
    def evaluate_risk(
        cls,
        features: Optional[Dict[str, Any]] = None,
        classification: str = "UNKNOWN",
        spatial_context: Optional[Dict[str, Any]] = None,
        temporal_data: Optional[Dict[str, Any]] = None,
        satellite_data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Calculates normalized risk score (0-100), risk level, and detailed explanation breakdown.
        Safe against missing or partial feature inputs.
        """
        features = features or {}
        spatial_context = spatial_context or {}
        temporal_data = temporal_data or {}
        satellite_data = satellite_data or {}

        breakdown_factors: List[Dict[str, Any]] = []

        # 1. Classification Contribution (Max 35 points)
        class_key = classification.upper() if classification else "UNKNOWN"
        class_pts = cls.CLASSIFICATION_WEIGHTS.get(class_key, 5.0)
        
        # Scale slightly with classification probability if available
        prob = features.get("model_probability")
        if prob is not None and isinstance(prob, (int, float)):
            confidence_factor = max(0.5, min(1.0, float(prob)))
            class_pts = round(class_pts * confidence_factor, 1)

        breakdown_factors.append({
            "category": "Classification Contribution",
            "contribution_points": class_pts,
            "max_points": 35.0,
            "description": f"Event evaluated as {class_key}"
        })

        # 2. Thermal Intensity / FRP (Max 25 points)
        # Normalized: 0 to 200+ MW
        frp = features.get("frp")
        if frp is None:
            frp = temporal_data.get("mean_frp", 0.0)
        frp = float(frp) if frp is not None else 0.0

        if frp >= 150.0:
            thermal_pts = 25.0
            thermal_desc = f"Extreme thermal intensity ({frp:.1f} MW)"
        elif frp >= 80.0:
            thermal_pts = 20.0
            thermal_desc = f"Very high thermal intensity ({frp:.1f} MW)"
        elif frp >= 40.0:
            thermal_pts = 14.0
            thermal_desc = f"Elevated thermal intensity ({frp:.1f} MW)"
        elif frp >= 15.0:
            thermal_pts = 8.0
            thermal_desc = f"Moderate thermal intensity ({frp:.1f} MW)"
        else:
            thermal_pts = max(1.0, round(frp / 5.0, 1))
            thermal_desc = f"Low thermal intensity ({frp:.1f} MW)"

        breakdown_factors.append({
            "category": "Thermal Intensity",
            "contribution_points": thermal_pts,
            "max_points": 25.0,
            "description": thermal_desc
        })

        # 3. Temporal Behavior & Persistence (Max 20 points)
        temporal_status = temporal_data.get("status") or features.get("temporal_status") or "NEW"
        active_days = temporal_data.get("active_days") or features.get("active_days") or 1
        active_days = int(active_days)
        frp_spike_ratio = temporal_data.get("frp_spike_ratio") or 1.0

        temporal_pts = 0.0
        temporal_desc_parts = []

        if temporal_status == "ABNORMAL" or frp_spike_ratio >= 2.5:
            temporal_pts += 15.0
            temporal_desc_parts.append(f"Abnormal thermal spike (spike ratio: {frp_spike_ratio:.1f}x)")
        elif temporal_status == "PERSISTENT" or active_days >= 5:
            temporal_pts += 12.0
            temporal_desc_parts.append(f"Long-term persistent source ({active_days} active days)")
        elif temporal_status == "RECURRING" or active_days >= 2:
            temporal_pts += 7.0
            temporal_desc_parts.append(f"Recurring thermal activity ({active_days} active days)")
        else:
            temporal_pts += 3.0
            temporal_desc_parts.append("New / isolated anomaly detection")

        # Additional point boost if maximum FRP in cluster is very high
        cluster_max_frp = temporal_data.get("max_frp") or 0.0
        if cluster_max_frp > 100.0:
            temporal_pts += 5.0
            temporal_desc_parts.append(f"Historical peak FRP {cluster_max_frp:.1f} MW")

        temporal_pts = min(20.0, temporal_pts)
        breakdown_factors.append({
            "category": "Temporal Behavior",
            "contribution_points": temporal_pts,
            "max_points": 20.0,
            "description": "; ".join(temporal_desc_parts)
        })

        # 4. Infrastructure & Vulnerability Proximity (Max 15 points)
        dist_m = spatial_context.get("distance_meters")
        if dist_m is None and "nearest_facility" in spatial_context:
            nf = spatial_context.get("nearest_facility") or {}
            dist_m = nf.get("distance_meters")

        fac_name = "industrial facility"
        fac_type = "facility"
        if "nearest_facility" in spatial_context and spatial_context["nearest_facility"]:
            nf = spatial_context["nearest_facility"]
            fac_name = nf.get("name") or fac_name
            fac_type = nf.get("facility_type") or fac_type

        if dist_m is not None:
            dist_val = float(dist_m)
            if dist_val <= 250.0:
                infra_pts = 15.0
                infra_desc = f"Direct proximity ({dist_val:.0f} m) to {fac_name} ({fac_type})"
            elif dist_val <= 750.0:
                infra_pts = 12.0
                infra_desc = f"Close proximity ({dist_val:.0f} m) to {fac_name} ({fac_type})"
            elif dist_val <= 2000.0:
                infra_pts = 7.0
                infra_desc = f"Medium proximity ({dist_val:.0f} m) to {fac_name}"
            elif dist_val <= 5000.0:
                infra_pts = 4.0
                infra_desc = f"Within 5 km radius of {fac_name}"
            else:
                infra_pts = 1.0
                infra_desc = f"Far proximity (> 5 km) to mapped infrastructure"
        else:
            infra_pts = 2.0
            infra_desc = "No immediate industrial infrastructure identified within search radius"

        breakdown_factors.append({
            "category": "Infrastructure Proximity",
            "contribution_points": infra_pts,
            "max_points": 15.0,
            "description": infra_desc
        })

        # 5. Satellite Remote Sensing & Physical Confirmation (Max 5 points)
        has_sat = satellite_data.get("available") or satellite_data.get("satellite_evidence_available")
        burn_scar = satellite_data.get("indices", {}).get("burn_scar_indicator") if isinstance(satellite_data.get("indices"), dict) else False
        swir_ratio = satellite_data.get("indices", {}).get("swir_nir_ratio") if isinstance(satellite_data.get("indices"), dict) else None

        if has_sat:
            if burn_scar or (swir_ratio is not None and swir_ratio > 1.2):
                sat_pts = 5.0
                sat_desc = "Sentinel-2 spectral confirmation (combustion / burn scar signature observed)"
            else:
                sat_pts = 3.0
                sat_desc = "Sentinel-2 imagery verified with acceptable cloud cover"
        else:
            cloud_rej = satellite_data.get("evidence_status") == "REJECTED_CLOUD"
            if cloud_rej:
                sat_pts = 1.0
                sat_desc = "Optical satellite obstructed by dense cloud cover"
            else:
                sat_pts = 0.0
                sat_desc = "Satellite scene unconfirmed or pending acquisition window"

        breakdown_factors.append({
            "category": "Satellite Evidence",
            "contribution_points": sat_pts,
            "max_points": 5.0,
            "description": sat_desc
        })

        # Total Calculation & Level Assignment
        total_raw = sum(f["contribution_points"] for f in breakdown_factors)
        risk_score = round(max(0.0, min(100.0, total_raw)), 1)
        risk_level = cls._determine_risk_level(risk_score)

        return {
            "risk_score": risk_score,
            "risk_level": risk_level,
            "risk_model_version": cls.MODEL_VERSION,
            "breakdown": {
                "factors": breakdown_factors,
                "total_score": risk_score,
                "risk_level": risk_level,
                "model_version": cls.MODEL_VERSION
            },
            "input_snapshot": {
                "classification": class_key,
                "frp": frp,
                "temporal_status": temporal_status,
                "active_days": active_days,
                "distance_to_facility_meters": dist_m,
                "satellite_evidence_available": bool(has_sat)
            },
            "calculated_at": datetime.now(timezone.utc).isoformat()
        }

    @classmethod
    def _determine_risk_level(cls, score: float) -> str:
        if score >= cls.THRESHOLDS["CRITICAL"][0]:
            return "CRITICAL"
        elif score >= cls.THRESHOLDS["HIGH"][0]:
            return "HIGH"
        elif score >= cls.THRESHOLDS["MODERATE"][0]:
            return "MODERATE"
        return "LOW"

    @classmethod
    def get_tier(cls, score: float) -> str:
        return cls._determine_risk_level(score)

    @classmethod
    def record_risk_assessment(
        cls,
        db: Session,
        event_id: int,
        features: Optional[Dict[str, Any]] = None,
        classification: str = "UNKNOWN",
        spatial_context: Optional[Dict[str, Any]] = None,
        temporal_data: Optional[Dict[str, Any]] = None,
        satellite_data: Optional[Dict[str, Any]] = None
    ) -> RiskAssessment:
        """
        Computes risk assessment and persists a historical record in risk_assessments table.
        """
        assessment_data = cls.evaluate_risk(
            features=features,
            classification=classification,
            spatial_context=spatial_context,
            temporal_data=temporal_data,
            satellite_data=satellite_data
        )

        record = RiskAssessment(
            event_id=event_id,
            risk_score=assessment_data["risk_score"],
            risk_level=assessment_data["risk_level"],
            risk_model_version=assessment_data["risk_model_version"],
            breakdown_json=assessment_data["breakdown"],
            input_snapshot_json=assessment_data["input_snapshot"],
            calculated_at=datetime.now(timezone.utc)
        )
        db.add(record)
        db.commit()
        db.refresh(record)
        return record
