import os
import json
import pickle
import logging
from typing import Dict, Any, List, Optional
import numpy as np
from app.core.config import settings
from app.schemas.features import ThermalFeatures
from app.services.classification.classifier import ClassifierInterface, PrototypeClassifier

logger = logging.getLogger(__name__)

class MLClassifier(ClassifierInterface):
    """
    Production Machine Learning Inference Service.
    Loads trained tabular models (XGBoost / Random Forest) from versioned model registry.
    Handles missing satellite/land-cover features gracefully via native tree missing-value logic,
    and returns true model probabilities, feature importance attributions, and factual evidence.
    """

    def __init__(
        self,
        registry_dir: str = settings.MODEL_REGISTRY_PATH,
        model_version: str = settings.ACTIVE_MODEL_VERSION,
        fallback_to_prototype: bool = settings.FALLBACK_TO_PROTOTYPE
    ):
        self.registry_dir = registry_dir
        self.model_version = model_version
        self.fallback_to_prototype = fallback_to_prototype
        
        self.model = None
        self.label_encoder = None
        self.classes: List[str] = []
        self.feature_columns: List[str] = []
        self.metadata: Dict[str, Any] = {}
        self.feature_importances: Dict[str, float] = {}
        
        self._load_model()

    def _load_model(self) -> None:
        """
        Loads model artifact and metadata from registry directory.
        """
        version_dir = os.path.join(self.registry_dir, self.model_version)
        model_path = os.path.join(version_dir, "model.pkl")
        metadata_path = os.path.join(version_dir, "metadata.json")

        if not os.path.exists(model_path) or not os.path.exists(metadata_path):
            logger.warning(
                f"Model artifact not found at {version_dir}. Will use prototype fallback if enabled."
            )
            return

        try:
            with open(model_path, "rb") as f:
                artifact = pickle.load(f)
                self.model = artifact["model"]
                self.label_encoder = artifact["label_encoder"]
                self.classes = artifact["classes"]
                self.feature_columns = artifact["feature_columns"]

            with open(metadata_path, "r", encoding="utf-8") as f:
                self.metadata = json.load(f)
                self.feature_importances = self.metadata.get("feature_importances", {})

            logger.info(f"Loaded production ML model {self.model_version} with {len(self.classes)} classes.")
        except Exception as e:
            logger.error(f"Failed to load model from {version_dir}: {e}")
            self.model = None

    def is_operational(self) -> bool:
        return self.model is not None

    def predict(self, features: ThermalFeatures) -> Dict[str, Any]:
        """
        Alias for classify conforming to MLClassifier interface specification.
        """
        return self.classify(features)

    def classify(self, features: ThermalFeatures) -> Dict[str, Any]:
        """
        Runs ML inference on the provided feature vector.
        """
        # If production model unavailable, handle fallback
        if not self.is_operational():
            if self.fallback_to_prototype:
                logger.info("Production ML model not loaded; invoking PrototypeClassifier fallback.")
                proto = PrototypeClassifier().classify(features)
                proto["is_fallback"] = True
                proto["classification_source"] = "Prototype heuristic engine"
                proto["model_version"] = f"fallback-{proto['model_version']}"
                return proto
            else:
                raise RuntimeError(f"Production ML model {self.model_version} is not operational.")

        # 1. Vectorize input features
        feat_dict = features.to_ml_dict()
        row: List[float] = []
        for col in self.feature_columns:
            val = feat_dict.get(col)
            if val is None:
                row.append(np.nan)
            else:
                try:
                    row.append(float(val))
                except (ValueError, TypeError):
                    row.append(np.nan)

        X = np.array([row], dtype=np.float32)

        # 2. Run model inference
        if self.model is None:
            raise RuntimeError("Model is None")

        try:
            proba_arr = self.model.predict_proba(X)[0]
            pred_idx = int(np.argmax(proba_arr))
            pred_class = self.classes[pred_idx]
            pred_prob = float(proba_arr[pred_idx])

            probabilities = {
                cls_name: round(float(proba_arr[i]), 4)
                for i, cls_name in enumerate(self.classes)
            }
        except Exception as e:
            logger.error(f"ML inference error: {e}")
            if self.fallback_to_prototype:
                proto = PrototypeClassifier().classify(features)
                proto["is_fallback"] = True
                proto["classification_source"] = "Prototype heuristic engine (Inference Error Fallback)"
                return proto
            raise

        # 3. Explainability: Top contributing features
        top_contributing = self._compute_feature_attributions(features, feat_dict)
        evidence_factors = self._build_evidence_factors(features, pred_class, pred_prob)

        return {
            "classification": pred_class,
            "model_probability": round(pred_prob, 3),
            "confidence_score": round(pred_prob * 100.0, 1),
            "confidence_type": "model_probability",
            "model_type": self.metadata.get("model_type", "xgboost"),
            "model_version": self.model_version,
            "feature_schema_version": self.metadata.get("feature_schema_version", "v2.0"),
            "probabilities": probabilities,
            "top_contributing_features": top_contributing,
            "evidence_factors": evidence_factors,
            "is_fallback": False,
            "classification_source": f"XGBoost {self.model_version}"
        }

    def _compute_feature_attributions(
        self,
        features: ThermalFeatures,
        feat_dict: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Generates ranked feature contributions combining model global importance
        and event-specific observation values.
        """
        attributions: List[Dict[str, Any]] = []

        for feat_name, imp in list(self.feature_importances.items())[:6]:
            val = feat_dict.get(feat_name)
            desc = ""
            if feat_name == "distance_to_industrial_facility":
                desc = f"Facility distance {int(val)}m" if val is not None else "No nearby industrial facility"
            elif feat_name == "spatial_spread_meters":
                desc = f"Cluster geographic spread: {val}m"
            elif feat_name == "mean_frp":
                desc = f"Mean thermal intensity: {val} MW"
            elif feat_name == "active_days":
                desc = f"Detected across {val} separate dates"
            elif feat_name == "confidence":
                desc = f"FIRMS detection confidence: {val}%"
            elif feat_name == "ndvi":
                desc = f"Sentinel-2 NDVI: {val}" if val is not None else "Satellite optical data unavailable"
            elif feat_name == "swir_nir_ratio":
                desc = f"SWIR/NIR combustion ratio: {val}" if val is not None else "Satellite SWIR unavailable"
            else:
                desc = f"{feat_name} = {val}"

            attributions.append({
                "feature": feat_name,
                "importance_weight": imp,
                "value": val,
                "description": desc
            })

        return attributions

    def _build_evidence_factors(
        self,
        features: ThermalFeatures,
        pred_class: str,
        probability: float
    ) -> List[str]:
        """
        Assembles factual evidence statements grounded in calculated observations.
        """
        factors: List[str] = [
            f"ML model ({self.model_version}) predicts '{pred_class}' with {round(probability * 100.0, 1)}% probability.",
            f"Thermal cluster exhibits {features.detection_count} detections across {features.active_days} active days (duration: {features.duration_hours} hrs)."
        ]

        if features.distance_to_industrial_facility is not None and features.distance_to_industrial_facility <= 2000.0:
            fac_name = features.nearest_facility_name or "Industrial Facility"
            factors.append(f"Located {int(features.distance_to_industrial_facility)}m from {fac_name} ({features.facility_type or 'Industrial infrastructure'}).")

        if features.temporal_status == "ABNORMAL":
            factors.append(f"Thermal intensity is marked ABNORMAL ({features.frp_deviation_ratio}x historical mean FRP of {features.mean_frp} MW).")
        elif features.temporal_status == "PERSISTENT":
            factors.append(f"Long-term temporal persistence detected across {features.active_days} active days with stable thermal FRP (std: {features.frp_std} MW).")

        if features.land_cover_class:
            factors.append(f"ESA WorldCover 10m land cover context: '{features.land_cover_class}' (Category: {features.land_cover_category or 'GENERAL'}).")

        if features.has_satellite_data:
            s2_info = []
            if features.cloud_coverage is not None:
                s2_info.append(f"Cloud: {features.cloud_coverage}%")
            if features.ndvi is not None:
                s2_info.append(f"NDVI: {features.ndvi}")
            if features.nbr is not None:
                s2_info.append(f"NBR: {features.nbr}")
            if features.swir_nir_ratio is not None:
                s2_info.append(f"SWIR/NIR ratio: {features.swir_nir_ratio}")
            factors.append(f"Sentinel-2 MSI surface reflectance verified: {', '.join(s2_info)}.")
        else:
            factors.append("Sentinel-2 optical evidence not available for this observation window (or obscured by cloud coverage).")

        return factors
