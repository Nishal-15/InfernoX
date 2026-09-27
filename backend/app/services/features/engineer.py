import logging
from typing import Dict, Any, Optional
from datetime import datetime, timezone
from app.schemas.features import ThermalFeatures
from app.services.landcover.provider import LandCoverProvider
from app.core.config import settings

logger = logging.getLogger(__name__)

class FeatureEngineer:
    """
    Dedicated Feature Engineering Layer for Phase 4.
    Extracts deterministic, reproducible feature vectors combining
    thermal observations, spatial infrastructure enrichment, temporal cluster intelligence,
    ESA WorldCover land-use classes, and Sentinel-2 satellite indices.
    """

    @staticmethod
    def extract_features(
        event: Any,
        spatial_context: Optional[Dict[str, Any]] = None,
        temporal_data: Optional[Dict[str, Any]] = None,
        satellite_data: Optional[Dict[str, Any]] = None
    ) -> ThermalFeatures:
        """
        Extracts a deterministic ThermalFeatures object with full multimodal coverage.
        """
        spatial_context = spatial_context or {}
        temporal_data = temporal_data or {}
        satellite_data = satellite_data or {}
        metrics = temporal_data.get("metrics", {})

        # 1. Event base properties
        event_id = getattr(event, "id", None) or event.get("id", 0)
        latitude = getattr(event, "latitude", None) if hasattr(event, "latitude") else event.get("latitude", 0.0)
        longitude = getattr(event, "longitude", None) if hasattr(event, "longitude") else event.get("longitude", 0.0)
        
        detected_at = getattr(event, "detected_at", None) if hasattr(event, "detected_at") else event.get("detected_at")
        if isinstance(detected_at, str):
            try:
                detected_at = datetime.fromisoformat(detected_at.replace("Z", "+00:00"))
            except Exception:
                detected_at = datetime.now(timezone.utc)
        elif not detected_at:
            detected_at = datetime.now(timezone.utc)

        satellite = getattr(event, "satellite", None) if hasattr(event, "satellite") else event.get("satellite", "UNKNOWN")
        frp = float(getattr(event, "frp", 0.0) if hasattr(event, "frp") else event.get("frp", 0.0) or 0.0)
        confidence = getattr(event, "confidence", None) if hasattr(event, "confidence") else event.get("confidence")
        confidence = float(confidence) if confidence is not None else None
        
        brightness_temp = getattr(event, "brightness_temperature", None) if hasattr(event, "brightness_temperature") else event.get("brightness_temperature")
        brightness_temp = float(brightness_temp) if brightness_temp is not None else None

        # 2. Temporal cluster metrics
        detection_count = int(metrics.get("event_count", 1))
        active_days = int(metrics.get("active_days", 1))
        duration_hours = float(metrics.get("duration_hours", 0.0))
        mean_frp = float(metrics.get("mean_frp", frp))
        max_frp = float(metrics.get("max_frp", frp))
        frp_std = float(metrics.get("frp_std", 0.0))
        frp_deviation_ratio = float(metrics.get("frp_deviation_ratio", 1.0))
        spatial_spread_meters = float(metrics.get("spatial_spread_meters", 0.0))
        detection_frequency = float(metrics.get("detection_frequency", 1.0))
        temporal_status = str(temporal_data.get("temporal_status", "NEW"))

        first_detection = metrics.get("first_detection")
        if isinstance(first_detection, str):
            try:
                first_detection = datetime.fromisoformat(first_detection.replace("Z", "+00:00"))
            except Exception:
                first_detection = None

        last_detection = metrics.get("last_detection")
        if isinstance(last_detection, str):
            try:
                last_detection = datetime.fromisoformat(last_detection.replace("Z", "+00:00"))
            except Exception:
                last_detection = None

        # 3. Spatial context properties & ESA WorldCover
        nearest_fac = spatial_context.get("nearest_facility") or {}
        dist_facility = spatial_context.get("distance_meters")
        if dist_facility is None and nearest_fac:
            dist_facility = nearest_fac.get("distance_meters")
        dist_facility = float(dist_facility) if dist_facility is not None else None

        facility_type = nearest_fac.get("facility_type")
        nearest_facility_name = nearest_fac.get("name")

        land_cover = spatial_context.get("land_cover")
        if not land_cover:
            try:
                land_cover = LandCoverProvider().get_land_cover(float(latitude or 0.0), float(longitude or 0.0))
            except Exception:
                land_cover = {}
        land_cover = land_cover or {}

        land_cover_class = land_cover.get("land_cover_class") or land_cover.get("class")
        land_cover_code = land_cover.get("land_cover_code")
        land_cover_category = land_cover.get("land_cover_category")

        is_industrial_land = False
        if land_cover_category == "INDUSTRIAL/BUILT":
            is_industrial_land = True
        elif land_cover_class:
            lc_lower = land_cover_class.lower()
            if "industrial" in lc_lower or "built-up" in lc_lower or "urban" in lc_lower:
                is_industrial_land = True
        if dist_facility is not None and dist_facility <= settings.INDUSTRIAL_PROXIMITY_THRESHOLD_METERS:
            is_industrial_land = True

        # 4. Phase 4 Satellite Imagery Derived Features
        has_satellite = bool(satellite_data.get("satellite_evidence_available", False))
        scene_id = satellite_data.get("scene_id")
        acq_time = satellite_data.get("acquisition_time")
        if isinstance(acq_time, str):
            try:
                acq_time = datetime.fromisoformat(acq_time.replace("Z", "+00:00"))
            except Exception:
                acq_time = None
        cloud_pct = satellite_data.get("cloud_percentage")
        cloud_pct = float(cloud_pct) if cloud_pct is not None else None

        indices = satellite_data.get("indices") or {}
        ndvi = float(indices["ndvi"]) if "ndvi" in indices and indices["ndvi"] is not None else None
        nbr = float(indices["nbr"]) if "nbr" in indices and indices["nbr"] is not None else None
        ndwi = float(indices["ndwi"]) if "ndwi" in indices and indices["ndwi"] is not None else None
        swir_nir = float(indices["swir_nir_ratio"]) if "swir_nir_ratio" in indices and indices["swir_nir_ratio"] is not None else None
        burn_scar = bool(satellite_data.get("burn_scar_indicator")) if satellite_data.get("burn_scar_indicator") is not None else None

        # 5. Deterministic composite scores (0.0 to 1.0)
        persistence_score = round(min(1.0, active_days / float(max(1, settings.PERSISTENCE_MIN_ACTIVE_DAYS * 3))), 2)
        recurrence_score = round(min(1.0, detection_count / float(max(1, settings.RECURRING_MIN_DETECTIONS * 5))), 2)
        
        abnormality_score = 0.0
        if frp_deviation_ratio > 1.0:
            abnormality_score = round(min(1.0, (frp_deviation_ratio - 1.0) / 4.0), 2)

        return ThermalFeatures(
            event_id=event_id,
            latitude=latitude,
            longitude=longitude,
            detected_at=detected_at,
            satellite=satellite,
            frp=frp,
            confidence=confidence,
            brightness_temperature=brightness_temp,
            detection_count=detection_count,
            active_days=active_days,
            duration_hours=duration_hours,
            first_detection=first_detection,
            last_detection=last_detection,
            mean_frp=mean_frp,
            max_frp=max_frp,
            frp_std=frp_std,
            frp_deviation_ratio=frp_deviation_ratio,
            spatial_spread_meters=spatial_spread_meters,
            detection_frequency=detection_frequency,
            temporal_status=temporal_status,
            distance_to_industrial_facility=dist_facility,
            facility_type=facility_type,
            nearest_facility_name=nearest_facility_name,
            land_cover_class=land_cover_class,
            land_cover_code=land_cover_code,
            land_cover_category=land_cover_category,
            is_industrial_land=is_industrial_land,
            has_satellite_data=has_satellite,
            satellite_scene_id=scene_id,
            satellite_acquisition_time=acq_time,
            cloud_coverage=cloud_pct,
            ndvi=ndvi,
            nbr=nbr,
            ndwi=ndwi,
            swir_nir_ratio=swir_nir,
            burn_scar_detected=burn_scar,
            persistence_score=persistence_score,
            recurrence_score=recurrence_score,
            abnormality_score=abnormality_score
        )
