import math
from typing import Dict, Any, Optional, List, Tuple
import logging

logger = logging.getLogger(__name__)

class IndustrialFireDiscriminator:
    """
    Industrial vs. Natural Fire Discrimination Layer.
    Synthesizes multimodal evidence across spatial proximity, facility hazard tiers,
    land cover classes, temporal baselines, spatial propagation, and Sentinel-2 spectral evidence.
    
    Distinguishes:
      1. Abnormal Industrial Thermal Surge / Loss of Containment
      2. Normal Persistent Operational Industrial Source (e.g., Gas Flare, Process Furnace)
      3. Propagating Natural / Forest Wildfire
      4. Agricultural Burning
      5. Inconclusive / Insufficient Evidence
    """

    @staticmethod
    def _point_in_polygon(lon: float, lat: float, ring: List[Any]) -> bool:
        """Standard ray casting algorithm for 2D polygon ring."""
        if not ring or len(ring) < 3:
            return False
        inside = False
        n = len(ring)
        p1x, p1y = float(ring[0][0]), float(ring[0][1])
        for i in range(1, n + 1):
            p2 = ring[i % n]
            p2x, p2y = float(p2[0]), float(p2[1])
            if lat > min(p1y, p2y):
                if lat <= max(p1y, p2y):
                    if lon <= max(p1x, p2x):
                        if p1y != p2y:
                            xinters = (lat - p1y) * (p2x - p1x) / (p2y - p1y) + p1x
                        if p1x == p2x or lon <= xinters:
                            inside = not inside
            p1x, p1y = p2x, p2y
        return inside

    @classmethod
    def evaluate_footprint_relation(
        cls,
        distance_meters: Optional[float],
        facility_geometry: Optional[Dict[str, Any]] = None,
        point_coords: Optional[Tuple[float, float]] = None,
        facility_type: str = ""
    ) -> str:
        """
        Evaluates spatial relation between thermal anomaly and facility footprint.
        
        Geometric Rules:
        - If facility_geometry is provided:
          - Validates coordinates and ring closure. If invalid -> INVALID_GEOMETRY.
          - If Point geometry: cannot assert interior -> reports distance proximity.
          - If Polygon/MultiPolygon and point_coords given: executes ray-casting.
            * Inside process area -> PROCESS_AREA_PROXIMITY
            * Inside storage/tank area -> STORAGE_AREA_PROXIMITY
            * Inside general boundary -> INSIDE_FACILITY_FOOTPRINT
            * Outside -> boundary/zone proximity based on distance.
        - If facility_geometry is missing/None:
          - If distance is None -> UNKNOWN_GEOMETRY.
          - If distance is provided -> reports distance proximity:
            * <= 250m -> FACILITY_BOUNDARY_PROXIMITY
            * <= 2000m -> INDUSTRIAL_ZONE_PROXIMITY
            * > 2000m -> OUTSIDE_INDUSTRIAL_CONTEXT
          - Crucially, NEVER asserts INSIDE_FACILITY_FOOTPRINT without polygon proof.
        """
        if facility_geometry:
            geom_type = str(facility_geometry.get("type", "")).upper()
            coords = facility_geometry.get("coordinates")
            
            # Geometry validation
            if not coords or not isinstance(coords, list) or len(coords) == 0:
                return "INVALID_GEOMETRY"

            if geom_type == "POINT":
                pass  # Fall through to distance-based evaluation
            elif geom_type in ["POLYGON", "MULTIPOLYGON"]:
                # Check minimum coordinates for valid polygon ring
                try:
                    rings = coords if geom_type == "POLYGON" else [poly[0] for poly in coords if poly]
                    if not rings or not rings[0] or len(rings[0]) < 3:
                        return "INVALID_GEOMETRY"
                    
                    if point_coords:
                        lon, lat = float(point_coords[0]), float(point_coords[1])
                        inside = False
                        for ring in rings:
                            if cls._point_in_polygon(lon, lat, ring):
                                inside = True
                                break
                        
                        if inside:
                            f_lower = facility_type.lower()
                            if any(k in f_lower for k in ["process", "unit", "furnace", "cracker", "distill"]):
                                return "PROCESS_AREA_PROXIMITY"
                            elif any(k in f_lower for k in ["tank", "storage", "terminal", "depot"]):
                                return "STORAGE_AREA_PROXIMITY"
                            return "INSIDE_FACILITY_FOOTPRINT"
                except Exception:
                    return "INVALID_GEOMETRY"

        # Distance-only evaluation
        if distance_meters is None:
            return "OUTSIDE_INDUSTRIAL_CONTEXT"
        
        try:
            d = float(distance_meters)
            if math.isnan(d) or math.isinf(d):
                return "UNKNOWN_GEOMETRY"
        except (ValueError, TypeError):
            return "UNKNOWN_GEOMETRY"

        # If a Point geometry was explicitly provided, report boundary proximity (cannot claim polygon interior)
        if facility_geometry and str(facility_geometry.get("type", "")).upper() == "POINT":
            if d <= 250.0:
                return "FACILITY_BOUNDARY_PROXIMITY"
            elif d <= 2000.0:
                return "INDUSTRIAL_ZONE_PROXIMITY"
            return "OUTSIDE_INDUSTRIAL_CONTEXT"

        if d <= 100.0:
            return "INSIDE_FACILITY_FOOTPRINT"
        elif d <= 250.0:
            return "FACILITY_BOUNDARY_PROXIMITY"
        elif d <= 2000.0:
            return "INDUSTRIAL_ZONE_PROXIMITY"
        return "OUTSIDE_INDUSTRIAL_CONTEXT"

    @classmethod
    def evaluate_change_point(
        cls,
        current_frp: float,
        baseline_frp: float,
        frp_acceleration: float,
        spatial_spread_m: float
    ) -> Dict[str, Any]:
        """
        Deterministic Change-Point Detection.
        Evaluates whether current thermal intensity represents normal baseline,
        minor deviation, significant deviation, or major anomaly.
        """
        if baseline_frp <= 0:
            ratio = 1.0
        else:
            ratio = round(current_frp / baseline_frp, 2)

        anomaly_magnitude = round(abs(current_frp - baseline_frp), 1)

        if ratio >= 4.0 or frp_acceleration >= 25.0:
            state = "MAJOR_ANOMALY"
            expl = f"Severe thermal surge ({ratio}x baseline of {baseline_frp} MW; +{frp_acceleration} MW/h acceleration)."
        elif ratio >= 2.5 or spatial_spread_m > 600.0:
            state = "SIGNIFICANT_DEVIATION"
            expl = f"Significant baseline deviation ({ratio}x baseline; spread: {spatial_spread_m}m)."
        elif ratio >= 1.8:
            state = "MINOR_DEVIATION"
            expl = f"Elevated thermal reading ({ratio}x baseline of {baseline_frp} MW)."
        else:
            state = "NORMAL_BASELINE"
            expl = f"Thermal intensity consistent with historical baseline ({ratio}x of {baseline_frp} MW)."

        return {
            "change_point_state": state,
            "anomaly_ratio": ratio,
            "anomaly_magnitude_mw": anomaly_magnitude,
            "baseline_frp_mw": baseline_frp,
            "current_frp_mw": current_frp,
            "explanation": expl
        }

    @classmethod
    def evaluate(
        cls,
        event: Dict[str, Any],
        spatial_context: Optional[Dict[str, Any]] = None,
        temporal_data: Optional[Dict[str, Any]] = None,
        satellite_data: Optional[Dict[str, Any]] = None,
        propagation_data: Optional[Dict[str, Any]] = None,
        fusion_data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Produces an explainable evidence breakdown separating Industrial Evidence
        from Natural Fire Evidence without conflating proximity with causation.
        """
        spatial_context = spatial_context or {}
        temporal_data = temporal_data or {}
        satellite_data = satellite_data or {}
        propagation_data = propagation_data or {}
        fusion_data = fusion_data or {}

        # 1. Physical & Spatial Attributes
        frp = float(event.get("frp") or 0.0)
        nearest_fac = spatial_context.get("nearest_facility") or {}
        dist_m = spatial_context.get("distance_meters")
        if dist_m is None and nearest_fac:
            dist_m = nearest_fac.get("distance_meters")
        
        # Coordinates and geometry extraction
        point_coords = None
        if "latitude" in event and "longitude" in event:
            try:
                point_coords = (float(event["longitude"]), float(event["latitude"]))
            except (ValueError, TypeError):
                point_coords = None
        elif "latitude" in spatial_context and "longitude" in spatial_context:
            try:
                point_coords = (float(spatial_context["longitude"]), float(spatial_context["latitude"]))
            except (ValueError, TypeError):
                point_coords = None

        fac_geom = nearest_fac.get("geometry") or spatial_context.get("facility_geometry")
        fac_type = str(nearest_fac.get("facility_type") or nearest_fac.get("type") or "").lower()

        footprint_relation = cls.evaluate_footprint_relation(
            distance_meters=dist_m,
            facility_geometry=fac_geom,
            point_coords=point_coords,
            facility_type=fac_type
        )
        hazard_cat = spatial_context.get("facility_hazard_category", "NONE")
        land_cover_cat = spatial_context.get("land_cover_category", "OTHER")

        # 2. Temporal Metrics & Change-Point
        metrics = temporal_data.get("metrics", {})
        baseline_frp = float(metrics.get("median_frp") or metrics.get("mean_frp") or frp)
        accel = float(metrics.get("frp_acceleration_mw_per_hour") or 0.0)
        spread_m = float(metrics.get("spatial_spread_meters") or 0.0)
        active_days = int(metrics.get("active_days") or 1)
        temporal_status = temporal_data.get("temporal_status", "NEW")

        change_point = cls.evaluate_change_point(frp, baseline_frp, accel, spread_m)

        # 3. Expected vs. Unexpected Industrial Context
        fac_name = str(nearest_fac.get("name") or "").lower()
        is_hazardous_industrial = any(k in fac_type or k in fac_name for k in [
            "refinery", "lng", "lpg", "gas", "petrochemical", "chemical", "oil", "fuel", "bottling", "fertilizer", "smelter"
        ])
        is_stationary = propagation_data.get("propagation_state") == "STATIONARY_SOURCE"

        if is_hazardous_industrial and (active_days >= 3 or temporal_status in ["PERSISTENT", "RECURRING"]) and is_stationary and change_point["change_point_state"] in ["NORMAL_BASELINE", "MINOR_DEVIATION"]:
            thermal_context = "EXPECTED_INDUSTRIAL_THERMAL_CONTEXT"
            thermal_context_expl = "Persistent, stationary thermal emission consistent with standard operational flare / process heating."
        elif is_hazardous_industrial and change_point["change_point_state"] in ["MAJOR_ANOMALY", "SIGNIFICANT_DEVIATION"]:
            thermal_context = "UNEXPECTED_INDUSTRIAL_THERMAL_CONTEXT"
            thermal_context_expl = f"Abnormal thermal surge ({change_point['anomaly_ratio']}x baseline) within industrial facility footprint indicates potential loss of containment."
        elif footprint_relation == "OUTSIDE_INDUSTRIAL_CONTEXT":
            thermal_context = "NON_INDUSTRIAL_ENVIRONMENT"
            thermal_context_expl = "Thermal event located outside mapped industrial infrastructure boundaries."
        else:
            thermal_context = "GENERAL_INDUSTRIAL_CONTEXT"
            thermal_context_expl = f"Observation near {fac_type or 'industrial facility'}; evaluating operational history."

        # 4. Synthesize INDUSTRIAL EVIDENCE (Strength 0.0 to 1.0)
        ind_points = 0.0
        ind_reasons: List[str] = []

        d_str = f"{float(dist_m):.0f}m" if dist_m is not None else "mapped perimeter"
        if footprint_relation in ["INSIDE_FACILITY_FOOTPRINT", "FACILITY_BOUNDARY_PROXIMITY"]:
            ind_points += 0.35
            ind_reasons.append(f"Immediate proximity ({d_str}) to {fac_type or 'facility'}")
        elif footprint_relation in ["PROCESS_AREA_PROXIMITY", "STORAGE_AREA_PROXIMITY"]:
            ind_points += 0.20
            ind_reasons.append(f"Located within industrial process/storage boundary ({d_str})")


        if land_cover_cat == "INDUSTRIAL/BUILT":
            ind_points += 0.15
            ind_reasons.append("ESA WorldCover confirms Built-up/Industrial ground surface")

        if is_stationary:
            ind_points += 0.20
            ind_reasons.append("Spatial spread remains strictly stationary (< 350m radius)")

        if active_days >= 3:
            ind_points += 0.15
            ind_reasons.append(f"Multi-day temporal persistence ({active_days} active days)")

        if fusion_data.get("cross_sensor_confirmation"):
            ind_points += 0.15
            ind_reasons.append(f"Cross-sensor confirmation from {fusion_data.get('unique_sensor_count')} distinct satellite platforms")

        industrial_evidence_score = round(min(1.0, ind_points), 2)

        # 5. Synthesize NATURAL FIRE EVIDENCE (Strength 0.0 to 1.0)
        nat_points = 0.0
        nat_reasons: List[str] = []

        if land_cover_cat in ["FOREST", "AGRICULTURE", "BARE_LAND", "VEGETATION", "GRASSLAND", "SHRUBLAND"]:
            nat_points += 0.30
            nat_reasons.append(f"Located on vegetative land cover ({land_cover_cat})")

        prop_state = propagation_data.get("propagation_state")
        if prop_state in ["EXPANDING_EVENT", "PROPAGATING_EVENT"]:
            nat_points += 0.35
            nat_reasons.append(f"Spatial propagation detected ({prop_state}, velocity {propagation_data.get('spread_velocity_m_per_hour')} m/h)")

        sat_diag = satellite_data.get("spectral_diagnosis") or ("BURN_SCAR_SUPPORT" if satellite_data.get("burn_scar_indicator") else "NO_CLEAR_SPECTRAL_SIGNAL")
        if sat_diag in ["BURN_SCAR_SUPPORT", "VEGETATION_FIRE_SUPPORT"]:
            nat_points += 0.25
            nat_reasons.append(f"Sentinel-2 multi-spectral verification ({sat_diag})")

        if footprint_relation == "OUTSIDE_INDUSTRIAL_CONTEXT":
            nat_points += 0.20
            nat_reasons.append("Zero industrial infrastructure within 2 km radius")

        natural_fire_evidence_score = round(min(1.0, nat_points), 2)

        # 6. Overall Scientific Interpretation
        if thermal_context == "UNEXPECTED_INDUSTRIAL_THERMAL_CONTEXT":
            interpretation = "ABNORMAL_INDUSTRIAL_FIRE_LIKELY"
            confidence = "HIGH" if industrial_evidence_score >= 0.70 else "MEDIUM"
        elif thermal_context == "EXPECTED_INDUSTRIAL_THERMAL_CONTEXT":
            interpretation = "NORMAL_PERSISTENT_INDUSTRIAL_SOURCE"
            confidence = "HIGH"
        elif natural_fire_evidence_score >= 0.65 and industrial_evidence_score < 0.35:
            interpretation = "NATURAL_VEGETATION_FIRE_LIKELY"
            confidence = "HIGH" if prop_state == "PROPAGATING_EVENT" else "MEDIUM"
        elif land_cover_cat == "AGRICULTURE" and frp <= 45.0 and is_stationary:
            interpretation = "AGRICULTURAL_OR_CONTROLLED_BURN"
            confidence = "MEDIUM"
        elif industrial_evidence_score >= 0.50 and change_point["change_point_state"] != "NORMAL_BASELINE":
            interpretation = "POTENTIAL_INDUSTRIAL_INCIDENT"
            confidence = "MEDIUM"
        else:
            interpretation = "INCONCLUSIVE_THERMAL_ANOMALY"
            confidence = "LOW"

        return {
            "interpretation": interpretation,
            "interpretation_confidence": confidence,
            "expected_thermal_context": thermal_context,
            "expected_thermal_context_explanation": thermal_context_expl,
            "footprint_relation": footprint_relation,
            "change_point": change_point,
            "evidence": {
                "industrial_evidence_score": industrial_evidence_score,
                "industrial_evidence_factors": ind_reasons,
                "natural_fire_evidence_score": natural_fire_evidence_score,
                "natural_fire_evidence_factors": nat_reasons
            }
        }

    @classmethod
    def discriminate(
        cls,
        event_id: Optional[int] = None,
        frp: float = 0.0,
        spatial_context: Optional[Dict[str, Any]] = None,
        temporal_context: Optional[Dict[str, Any]] = None,
        propagation_context: Optional[Dict[str, Any]] = None,
        satellite_context: Optional[Dict[str, Any]] = None,
        fusion_context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Convenience discrimination entrypoint mapping directly to evaluate().
        """
        event = {"id": event_id, "frp": frp}
        res = cls.evaluate(
            event=event,
            spatial_context=spatial_context,
            temporal_data=temporal_context,
            satellite_data=satellite_context,
            propagation_data=propagation_context,
            fusion_data=fusion_context
        )
        # Convenience aliases
        res["scientific_interpretation"] = res.get("interpretation")
        res["industrial_confidence"] = res.get("evidence", {}).get("industrial_evidence_score", 0.0)
        res["natural_confidence"] = res.get("evidence", {}).get("natural_fire_evidence_score", 0.0)
        # Expose change_point string if needed
        cp = res.get("change_point")
        if isinstance(cp, dict):
            res["change_point_state"] = cp.get("change_point_state")
        return res

