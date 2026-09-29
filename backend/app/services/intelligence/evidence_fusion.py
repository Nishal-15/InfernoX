from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
import logging

logger = logging.getLogger(__name__)

class MultimodalEvidenceFusionService:
    """
    Multimodal Evidence Fusion Engine.
    Integrates observational signals from FIRMS, OSM, WorldCover, Temporal,
    Sentinel-2, and Machine Learning into a cohesive, explainable evidence graph.
    
    Guarantees that evidence strength and confidence are traceable to their
    exact data sources, avoiding opaque 'black-box' scoring.
    """

    @classmethod
    def fuse_evidence(
        cls,
        event: Dict[str, Any],
        spatial_context: Optional[Dict[str, Any]] = None,
        temporal_data: Optional[Dict[str, Any]] = None,
        satellite_data: Optional[Dict[str, Any]] = None,
        propagation_data: Optional[Dict[str, Any]] = None,
        fusion_data: Optional[Dict[str, Any]] = None,
        ml_prediction: Optional[Dict[str, Any]] = None,
        discrimination_data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Assembles a structured multimodal evidence ledger.
        """
        spatial_context = spatial_context or {}
        temporal_data = temporal_data or {}
        satellite_data = satellite_data or {}
        propagation_data = propagation_data or {}
        fusion_data = fusion_data or {}
        ml_prediction = ml_prediction or {}
        discrimination_data = discrimination_data or {}

        ledger: List[Dict[str, Any]] = []
        now_iso = datetime.now(timezone.utc).isoformat()

        # 1. Multi-Sensor Confirmation Evidence
        if fusion_data.get("cross_sensor_confirmation"):
            ledger.append({
                "evidence_type": "CROSS_SENSOR_CORROBORATION",
                "source": "NASA_FIRMS_FUSION",
                "strength": 0.90,
                "direction": "CORROBORATING",
                "value": f"{fusion_data.get('unique_sensor_count')} platforms ({', '.join(fusion_data.get('sensors', []))})",
                "description": fusion_data.get("fusion_explanation"),
                "timestamp": now_iso
            })
        elif fusion_data.get("sensor_count", 1) > 1:
            ledger.append({
                "evidence_type": "REPEATED_SENSOR_DETECTION",
                "source": "NASA_FIRMS_FUSION",
                "strength": 0.70,
                "direction": "SUPPORTING",
                "value": f"{fusion_data.get('sensor_count')} passes",
                "description": "Repeated detection by single platform confirms persistency over time",
                "timestamp": now_iso
            })
        else:
            ledger.append({
                "evidence_type": "SINGLE_SENSOR_OBSERVATION",
                "source": "NASA_FIRMS",
                "strength": 0.45,
                "direction": "UNCONFIRMED_PASS",
                "value": "1 pass",
                "description": "Single-pass detection; cross-sensor confirmation pending",
                "timestamp": now_iso
            })

        # 2. Industrial Infrastructure & Footprint Evidence
        footprint_rel = discrimination_data.get("footprint_relation", "OUTSIDE_INDUSTRIAL_CONTEXT")
        dist_m = spatial_context.get("distance_meters")
        nearest_fac = spatial_context.get("nearest_facility") or {}
        fac_name = nearest_fac.get("name") or "Industrial Facility"
        fac_type = nearest_fac.get("facility_type") or "Facility"

        dist_str = f"{float(dist_m):.0f}m" if dist_m is not None else "mapped perimeter"
        if footprint_rel in ["INSIDE_FACILITY_FOOTPRINT", "FACILITY_BOUNDARY_PROXIMITY"]:
            ledger.append({
                "evidence_type": "FACILITY_FOOTPRINT_PROXIMITY",
                "source": "OPENSTREETMAP",
                "strength": 0.95,
                "direction": "INDUSTRIAL",
                "value": f"{dist_str} ({footprint_rel})",
                "description": f"Located within immediate boundary of {fac_name} ({fac_type})",
                "timestamp": now_iso
            })
        elif footprint_rel in ["PROCESS_AREA_PROXIMITY", "STORAGE_AREA_PROXIMITY"]:
            ledger.append({
                "evidence_type": "INDUSTRIAL_PERIMETER_PROXIMITY",
                "source": "OPENSTREETMAP",
                "strength": 0.75,
                "direction": "INDUSTRIAL",
                "value": f"{dist_str} ({footprint_rel})",
                "description": f"Located within operating envelope of {fac_name}",
                "timestamp": now_iso
            })


        # 3. Ground Land-Cover Context
        land_cover_class = spatial_context.get("land_cover_class")
        land_cover_cat = spatial_context.get("land_cover_category")
        if land_cover_cat == "INDUSTRIAL/BUILT":
            ledger.append({
                "evidence_type": "SURFACE_LAND_COVER",
                "source": "ESA_WORLDCOVER_10M",
                "strength": 0.85,
                "direction": "INDUSTRIAL",
                "value": f"{land_cover_class} (Built-up)",
                "description": "10-meter global land cover confirms artificial impervious / industrial ground substrate",
                "timestamp": now_iso
            })
        elif land_cover_cat in ["FOREST", "AGRICULTURE", "BARE_LAND"]:
            ledger.append({
                "evidence_type": "SURFACE_LAND_COVER",
                "source": "ESA_WORLDCOVER_10M",
                "strength": 0.80,
                "direction": "NATURAL_VEGETATION",
                "value": f"{land_cover_class} ({land_cover_cat})",
                "description": "10-meter global land cover confirms combustible vegetative or agricultural substrate",
                "timestamp": now_iso
            })

        # 4. Spatial Propagation Evidence
        prop_state = propagation_data.get("propagation_state", "INSUFFICIENT_DATA")
        spread_radius = propagation_data.get("spread_radius_meters", 0.0)
        spread_vel = propagation_data.get("spread_velocity_m_per_hour", 0.0)

        if prop_state == "STATIONARY_SOURCE":
            ledger.append({
                "evidence_type": "SPATIAL_PROPAGATION_DYNAMICS",
                "source": "POSTGIS_TEMPORAL_CLUSTERING",
                "strength": 0.90,
                "direction": "STATIONARY_FLARE",
                "value": f"Radius: {spread_radius:.0f}m, Vel: {spread_vel:.1f}m/h",
                "description": "Cluster demonstrates stationary emitter dynamics characteristic of fixed flare tip",
                "timestamp": now_iso
            })
        elif prop_state in ["EXPANDING_EVENT", "PROPAGATING_EVENT"]:
            ledger.append({
                "evidence_type": "SPATIAL_PROPAGATION_DYNAMICS",
                "source": "POSTGIS_TEMPORAL_CLUSTERING",
                "strength": 0.85,
                "direction": "EXPANDING_FIRE",
                "value": f"Radius: {spread_radius:.0f}m, Vel: {spread_vel:.1f}m/h",
                "description": "Active thermal propagation observed across expanding spatial perimeter",
                "timestamp": now_iso
            })

        # 5. Temporal Baseline & Change-Point Evidence
        change_point = discrimination_data.get("change_point", {})
        cp_state = change_point.get("change_point_state", "NORMAL_BASELINE")
        anomaly_ratio = change_point.get("anomaly_ratio", 1.0)

        if cp_state in ["MAJOR_ANOMALY", "SIGNIFICANT_DEVIATION"]:
            ledger.append({
                "evidence_type": "TEMPORAL_CHANGE_POINT",
                "source": "TEMPORAL_BASELINE_ENGINE",
                "strength": 0.88,
                "direction": "ANOMALOUS_SURGE",
                "value": f"{anomaly_ratio:.1f}x baseline ({cp_state})",
                "description": change_point.get("explanation"),
                "timestamp": now_iso
            })

        # 6. Sentinel-2 Spectral Confirmation
        sat_diag = satellite_data.get("spectral_diagnosis", "NO_CLEAR_SPECTRAL_SIGNAL")
        if sat_diag == "BURN_SCAR_SUPPORT":
            ledger.append({
                "evidence_type": "OPTICAL_SPECTRAL_EVIDENCE",
                "source": "SENTINEL_2_MSI_L2A",
                "strength": 0.90,
                "direction": "BURN_SCAR_CONFIRMED",
                "value": f"NBR: {satellite_data.get('indices', {}).get('nbr')}",
                "description": "Negative Normalized Burn Ratio confirms physical ground surface charring",
                "timestamp": now_iso
            })
        elif sat_diag == "VEGETATION_FIRE_SUPPORT":
            ledger.append({
                "evidence_type": "OPTICAL_SPECTRAL_EVIDENCE",
                "source": "SENTINEL_2_MSI_L2A",
                "strength": 0.85,
                "direction": "ACTIVE_COMBUSTION",
                "value": f"SWIR/NIR: {satellite_data.get('indices', {}).get('swir_nir_ratio')}",
                "description": "Elevated SWIR reflection confirms intense subpixel active combustion",
                "timestamp": now_iso
            })
        elif sat_diag == "CLOUD_OBSCURED":
            ledger.append({
                "evidence_type": "OPTICAL_SPECTRAL_EVIDENCE",
                "source": "SENTINEL_2_MSI_L2A",
                "strength": 0.0,
                "direction": "INCONCLUSIVE",
                "value": f"Cloud: {satellite_data.get('cloud_percentage')}%",
                "description": "Optical verification inconclusive due to cloud obstruction (not treated as negative evidence)",
                "timestamp": now_iso
            })

        # 7. Production ML Prediction Signal
        pred_class = ml_prediction.get("classification", "UNKNOWN")
        pred_prob = ml_prediction.get("model_probability", 0.5)
        conf_tier = ml_prediction.get("confidence_tier", "UNCERTAIN")
        entropy = ml_prediction.get("prediction_entropy", 0.5)

        ledger.append({
            "evidence_type": "ML_PREDICTION_VECTOR",
            "source": f"XGBOOST_{ml_prediction.get('model_version', 'xgb-v1')}",
            "strength": round(float(pred_prob), 2),
            "direction": pred_class,
            "value": f"{pred_class} (p={pred_prob:.2f}, {conf_tier}, H={entropy})",
            "description": f"Tabular XGBoost inference across 27 canonical features predicts {pred_class}",
            "timestamp": now_iso
        })

        # Evidence completeness score: proportion of analytical modalities contributing positive signal
        modalities = [
            bool(fusion_data),
            bool(spatial_context.get("nearest_facility")),
            bool(spatial_context.get("land_cover_class")),
            bool(temporal_data.get("metrics")),
            bool(satellite_data.get("satellite_evidence_available")),
            bool(ml_prediction.get("classification"))
        ]
        completeness = round(sum(1 for m in modalities if m) / len(modalities), 2)

        return {
            "evidence_ledger": ledger,
            "evidence_count": len(ledger),
            "evidence_completeness": completeness,
            "evidence_completeness_rating": "COMPLETE" if completeness >= 0.8 else ("PARTIAL" if completeness >= 0.5 else "LOW"),
            "fused_at": now_iso
        }

    @classmethod
    def synthesize_evidence(
        cls,
        event_id: Optional[int] = None,
        firms_data: Optional[Dict[str, Any]] = None,
        osm_context: Optional[Dict[str, Any]] = None,
        worldcover_context: Optional[Dict[str, Any]] = None,
        spatial_context: Optional[Dict[str, Any]] = None,
        temporal_context: Optional[Dict[str, Any]] = None,
        satellite_context: Optional[Dict[str, Any]] = None,
        propagation_context: Optional[Dict[str, Any]] = None,
        ml_prediction: Optional[Dict[str, Any]] = None,
        discrimination: Optional[Dict[str, Any]] = None,
        fusion_data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Convenience alias synthesizing all available modality contexts into the evidence ledger.
        """
        event = dict(firms_data or {})
        if event_id is not None:
            event["id"] = event_id

        combined_spatial = dict(spatial_context or {})
        if osm_context:
            combined_spatial.update(osm_context)
        if worldcover_context:
            combined_spatial.update(worldcover_context)

        return cls.fuse_evidence(
            event=event,
            spatial_context=combined_spatial,
            temporal_data=temporal_context,
            satellite_data=satellite_context,
            propagation_data=propagation_context,
            fusion_data=fusion_data,
            ml_prediction=ml_prediction,
            discrimination_data=discrimination
        )

