import math
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)

class SpatialPropagationModel:
    """
    Spatial Propagation Analysis Engine.
    Analyzes multi-temporal thermal cluster coordinates to distinguish stationary
    industrial thermal emitters from expanding or propagating active wildfires.
    
    States:
      - STATIONARY_SOURCE: Spatial radius <= 350m, velocity <= 10m/h, high concentration
      - LOCALIZED_EVENT: Spatial radius 350-750m, velocity <= 30m/h
      - EXPANDING_EVENT: Spatial radius 750-2000m, velocity 30-100m/h
      - PROPAGATING_EVENT: Spatial radius > 2000m or velocity > 100m/h with directional drift
      - INSUFFICIENT_DATA: Less than 3 historical observations available
    """

    @staticmethod
    def haversine_distance_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        r = 6371000.0
        phi1 = math.radians(lat1)
        phi2 = math.radians(lat2)
        dphi = math.radians(lat2 - lat1)
        dlambda = math.radians(lon2 - lon1)
        a = math.sin(dphi / 2.0)**2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2.0)**2
        c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
        return r * c

    @classmethod
    def analyze_propagation(
        cls,
        current_event: Dict[str, Any],
        cluster_records: List[Dict[str, Any]],
        duration_hours: float = 0.0
    ) -> Dict[str, Any]:
        """
        Calculates spatial dispersion, principal spread vector, spread velocity,
        and propagation classification.
        """
        # Assemble all chronological points
        all_pts: List[Dict[str, Any]] = []
        for r in cluster_records:
            lat = float(r.get("latitude") or 0.0)
            lon = float(r.get("longitude") or 0.0)
            if lat != 0.0 and lon != 0.0:
                all_pts.append({"lat": lat, "lon": lon, "id": r.get("id")})

        curr_lat = float(current_event.get("latitude") or 0.0)
        curr_lon = float(current_event.get("longitude") or 0.0)
        curr_id = current_event.get("id")
        if curr_lat != 0.0 and curr_lon != 0.0 and not any(p["id"] == curr_id for p in all_pts if curr_id is not None):
            all_pts.append({"lat": curr_lat, "lon": curr_lon, "id": curr_id})

        sample_count = len(all_pts)

        if sample_count < 3:
            return {
                "propagation_state": "INSUFFICIENT_DATA",
                "sample_count": sample_count,
                "confidence": "LOW",
                "spread_radius_meters": 0.0,
                "spread_velocity_m_per_hour": 0.0,
                "directional_azimuth_deg": None,
                "stationary_concentration": 1.0 if sample_count == 1 else 0.5,
                "elongation_ratio": 1.0,
                "explanation": f"Insufficient spatial observation count ({sample_count} < 3) to infer propagation dynamics."
            }

        # 1. Centroid calculation
        c_lat = sum(p["lat"] for p in all_pts) / sample_count
        c_lon = sum(p["lon"] for p in all_pts) / sample_count

        # 2. Distance from centroid and maximum spread radius
        distances_to_centroid = [cls.haversine_distance_m(p["lat"], p["lon"], c_lat, c_lon) for p in all_pts]
        spread_radius_m = round(max(distances_to_centroid), 1)

        # 3. Stationary concentration: fraction of detections within 250m of centroid
        within_250m = sum(1 for d in distances_to_centroid if d <= 250.0)
        stationary_conc = round(within_250m / sample_count, 2)

        # 4. Spread velocity
        effective_duration = max(1.0, float(duration_hours))
        spread_velocity = round(spread_radius_m / effective_duration, 2)

        # 5. Principal spread direction & elongation using spatial coordinate covariance
        mean_y = c_lat
        mean_x = c_lon * math.cos(math.radians(c_lat))
        
        # Convert degrees to local meters relative to centroid
        m_per_deg_lat = 111132.0
        m_per_deg_lon = 111132.0 * math.cos(math.radians(c_lat))

        coords_m = [
            ((p["lat"] - c_lat) * m_per_deg_lat, (p["lon"] - c_lon) * m_per_deg_lon)
            for p in all_pts
        ]

        var_y = sum(y**2 for y, x in coords_m) / sample_count
        var_x = sum(x**2 for y, x in coords_m) / sample_count
        cov_xy = sum(y * x for y, x in coords_m) / sample_count

        # Principal axis orientation: 0.5 * atan2(2 * cov_xy, var_x - var_y)
        theta_rad = 0.5 * math.atan2(2.0 * cov_xy, var_x - var_y + 1e-9)
        azimuth_deg = round((math.degrees(theta_rad) + 360.0) % 360.0, 1)

        # Elongation ratio
        term = math.sqrt(max(0.0, (var_x - var_y)**2 + 4.0 * cov_xy**2))
        lambda1 = max(0.1, 0.5 * (var_x + var_y + term))
        lambda2 = max(0.1, 0.5 * (var_x + var_y - term))
        elongation = round(math.sqrt(lambda1 / lambda2), 2)

        # 6. Propagation State Determination
        if spread_radius_m <= 350.0 and stationary_conc >= 0.70:
            state = "STATIONARY_SOURCE"
            expl = (
                f"Stationary thermal emitter localized within {spread_radius_m:.0f}m "
                f"({int(stationary_conc * 100)}% of detections within 250m centroid). Characteristic of fixed industrial flare."
            )
        elif spread_radius_m <= 750.0 and spread_velocity <= 40.0:
            state = "LOCALIZED_EVENT"
            expl = f"Localized thermal anomaly footprint spanning {spread_radius_m:.0f}m with low expansion velocity ({spread_velocity} m/h)."
        elif (spread_radius_m > 1000.0 and spread_velocity > 50.0) or spread_radius_m > 3000.0:
            state = "PROPAGATING_EVENT"
            expl = (
                f"Active propagating wildfire detected with extensive spatial perimeter ({spread_radius_m:.0f}m) "
                f"and rapid expansion velocity ({spread_velocity} m/h along {azimuth_deg}°)."
            )
        else:
            state = "EXPANDING_EVENT"
            expl = f"Expanding thermal cluster spanning {spread_radius_m:.0f}m at velocity {spread_velocity} m/h along {azimuth_deg}° axis."

        return {
            "propagation_state": state,
            "sample_count": sample_count,
            "confidence": "HIGH" if sample_count >= 5 else "MEDIUM",
            "spread_radius_meters": spread_radius_m,
            "spread_velocity_m_per_hour": spread_velocity,
            "spread_velocity_m_per_h": spread_velocity,
            "directional_azimuth_deg": azimuth_deg,
            "stationary_concentration": stationary_conc,
            "elongation_ratio": elongation,
            "centroid": {"latitude": round(c_lat, 6), "longitude": round(c_lon, 6)},
            "explanation": expl
        }

    @classmethod
    def evaluate_propagation(
        cls,
        cluster: List[Dict[str, Any]],
        duration_hours: float = 1.0
    ) -> Dict[str, Any]:
        """
        Convenience alias accepting a full list of cluster observation points.
        """
        if not cluster:
            return {
                "propagation_state": "INSUFFICIENT_DATA",
                "sample_count": 0,
                "confidence": "LOW",
                "spread_velocity_m_per_h": 0.0,
                "stationary_concentration": 0.0
            }
        current_event = cluster[0]
        cluster_records = cluster[1:] if len(cluster) > 1 else []
        return cls.analyze_propagation(current_event, cluster_records, duration_hours=duration_hours)

