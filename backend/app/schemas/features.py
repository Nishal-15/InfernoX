from pydantic import BaseModel, ConfigDict
from typing import Optional, List, Dict, Any
from datetime import datetime

class FeatureAttribution(BaseModel):
    feature: str
    value: Any
    importance: str # HIGH, MEDIUM, LOW
    description: str

class ThermalFeatures(BaseModel):
    event_id: int
    latitude: float
    longitude: float
    detected_at: datetime
    satellite: str
    
    # 1. Raw thermal metrics
    frp: float
    confidence: Optional[float] = None
    brightness_temperature: Optional[float] = None
    
    # 2. Temporal cluster metrics
    detection_count: int = 1
    active_days: int = 1
    duration_hours: float = 0.0
    first_detection: Optional[datetime] = None
    last_detection: Optional[datetime] = None
    mean_frp: float = 0.0
    max_frp: float = 0.0
    frp_std: float = 0.0
    frp_deviation_ratio: float = 1.0
    spatial_spread_meters: float = 0.0
    detection_frequency: float = 1.0
    temporal_status: str = "NEW" # NEW, RECURRING, PERSISTENT, ABNORMAL
    
    # 3. Spatial context features
    distance_to_industrial_facility: Optional[float] = None
    facility_type: Optional[str] = None
    nearest_facility_name: Optional[str] = None
    land_cover_class: Optional[str] = None
    land_cover_code: Optional[int] = None
    land_cover_category: Optional[str] = None # FOREST, AGRICULTURE, URBAN, INDUSTRIAL/BUILT, WATER, BARE_LAND, OTHER
    is_industrial_land: bool = False
    
    # 4. Phase 4 Satellite Imagery Derived Features (Sentinel-2 L2A)
    has_satellite_data: bool = False
    satellite_scene_id: Optional[str] = None
    satellite_acquisition_time: Optional[datetime] = None
    cloud_coverage: Optional[float] = None
    ndvi: Optional[float] = None
    nbr: Optional[float] = None
    ndwi: Optional[float] = None
    swir_nir_ratio: Optional[float] = None
    burn_scar_detected: Optional[bool] = None

    # 5. Derived composite scores (0.0 to 1.0)
    persistence_score: float = 0.0
    recurrence_score: float = 0.0
    abnormality_score: float = 0.0

    model_config = ConfigDict(from_attributes=True)

    def to_ml_dict(self) -> Dict[str, Any]:
        """
        Extracts a dictionary of numerical and encoded categorical features
        tailored for tabular ML models (XGBoost / Random Forest).
        Missing values are represented as None (which convert to np.nan).
        """
        # Encode temporal status
        temporal_status_map = {"NEW": 0, "RECURRING": 1, "PERSISTENT": 2, "ABNORMAL": 3}
        temporal_status_code = temporal_status_map.get(self.temporal_status, 0)

        # Encode land cover category
        lc_category_map = {
            "FOREST": 1,
            "AGRICULTURE": 2,
            "URBAN": 3,
            "INDUSTRIAL/BUILT": 4,
            "WATER": 5,
            "BARE_LAND": 6,
            "OTHER": 0
        }
        lc_category_code = lc_category_map.get(self.land_cover_category or "", 0)

        return {
            "frp": float(self.frp),
            "confidence": float(self.confidence) if self.confidence is not None else None,
            "brightness_temperature": float(self.brightness_temperature) if self.brightness_temperature is not None else None,
            "detection_count": int(self.detection_count),
            "active_days": int(self.active_days),
            "duration_hours": float(self.duration_hours),
            "mean_frp": float(self.mean_frp),
            "max_frp": float(self.max_frp),
            "frp_std": float(self.frp_std),
            "frp_deviation_ratio": float(self.frp_deviation_ratio),
            "spatial_spread_meters": float(self.spatial_spread_meters),
            "detection_frequency": float(self.detection_frequency),
            "temporal_status_code": temporal_status_code,
            "distance_to_industrial_facility": float(self.distance_to_industrial_facility) if self.distance_to_industrial_facility is not None else 9999.0,
            "is_industrial_land": 1.0 if self.is_industrial_land else 0.0,
            "land_cover_code": float(self.land_cover_code) if self.land_cover_code is not None else 0.0,
            "land_cover_category_code": lc_category_code,
            "has_satellite_data": 1.0 if self.has_satellite_data else 0.0,
            "cloud_coverage": float(self.cloud_coverage) if self.cloud_coverage is not None else None,
            "ndvi": float(self.ndvi) if self.ndvi is not None else None,
            "nbr": float(self.nbr) if self.nbr is not None else None,
            "ndwi": float(self.ndwi) if self.ndwi is not None else None,
            "swir_nir_ratio": float(self.swir_nir_ratio) if self.swir_nir_ratio is not None else None,
            "burn_scar_detected": 1.0 if self.burn_scar_detected else 0.0,
            "persistence_score": float(self.persistence_score),
            "recurrence_score": float(self.recurrence_score),
            "abnormality_score": float(self.abnormality_score)
        }
