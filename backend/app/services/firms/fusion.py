import math
import hashlib
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any, Optional, Tuple
import logging

logger = logging.getLogger(__name__)

# Base sensor resolution weights reflecting spatial ground sampling distance (GSD)
# VIIRS I-band (375m at nadir) provides significantly tighter spatial resolution than MODIS (1km)
SENSOR_BASE_WEIGHTS: Dict[str, float] = {
    "VIIRS_SNPP_NRT": 1.0,
    "VIIRS_NOAA20_NRT": 1.0,
    "VIIRS_NOAA21_NRT": 1.0,
    "SUOMI NPP": 1.0,
    "NPP": 1.0,
    "NOAA-20": 1.0,
    "NOAA-21": 1.0,
    "MODIS_NRT": 0.6,
    "TERRA": 0.6,
    "AQUA": 0.6,
    "UNKNOWN": 0.5
}

class FirmsObservationFusionService:
    """
    Multi-Sensor Observation Fusion Engine for NASA FIRMS.
    Associates concurrent or sequential satellite passes (VIIRS SNPP, NOAA-20, NOAA-21, MODIS)
    observing the same physical thermal event without discarding raw observations.
    
    Produces a quality-weighted fused representation, tracks cross-sensor confirmation,
    and documents full observation provenance.
    """

    def __init__(
        self,
        spatial_radius_meters: float = 1200.0,
        temporal_window_hours: float = 6.0,
        spatial_radius_m: Optional[float] = None
    ):
        if spatial_radius_m is not None:
            spatial_radius_meters = spatial_radius_m
        self.spatial_radius_meters = spatial_radius_meters
        self.temporal_window_hours = temporal_window_hours


    @classmethod
    def calculate_sensor_weight(cls, record: Dict[str, Any]) -> Tuple[float, Dict[str, Any]]:
        """
        Calculates a transparent, physically grounded quality weight for a single observation.
        Factors:
          1. Platform GSD (VIIRS 375m = 1.0, MODIS 1km = 0.6)
          2. Scan/track angle geometric expansion (nadir = 1.0, limb = degraded)
          3. Observation confidence (0.0 to 1.0)
          4. Night observation bonus (absence of solar reflection artifacts)
        """
        satellite = str(record.get("satellite", "")).strip().upper()
        instrument = str(record.get("instrument", "")).strip().upper()

        # Match base weight
        base_w = SENSOR_BASE_WEIGHTS.get(satellite, SENSOR_BASE_WEIGHTS.get(instrument, 0.7))

        # Footprint penalty for off-nadir distortion with numerical safety guards
        try:
            scan = float(record.get("scan") or 1.0)
            if math.isnan(scan) or math.isinf(scan) or scan <= 0:
                scan = 1.0
        except (ValueError, TypeError):
            scan = 1.0

        try:
            track = float(record.get("track") or 1.0)
            if math.isnan(track) or math.isinf(track) or track <= 0:
                track = 1.0
        except (ValueError, TypeError):
            track = 1.0

        footprint_area_ratio = max(1.0, scan * track)
        footprint_factor = round(1.0 / math.sqrt(footprint_area_ratio), 3)

        # Confidence scaling with finite bounds
        conf_raw = record.get("confidence")
        try:
            conf_val = float(conf_raw) if conf_raw is not None else 70.0
            if math.isnan(conf_val) or math.isinf(conf_val):
                conf_val = 70.0
            conf_factor = round(0.4 + 0.6 * (min(100.0, max(0.0, conf_val)) / 100.0), 3)
        except (ValueError, TypeError):
            conf_str = str(conf_raw).upper()
            if conf_str == "H":
                conf_factor = 1.0
            elif conf_str == "N":
                conf_factor = 0.7
            else:
                conf_factor = 0.5

        # Solar reflection noise penalty (Day observation vs Night)
        dn = str(record.get("daynight", "")).upper()
        night_bonus = 1.1 if dn == "N" else 1.0

        total_weight = round(base_w * footprint_factor * conf_factor * night_bonus, 4)

        audit_factors = {
            "satellite": satellite,
            "base_weight": base_w,
            "footprint_factor": footprint_factor,
            "confidence_factor": conf_factor,
            "night_bonus": night_bonus,
            "final_weight": total_weight
        }
        return total_weight, audit_factors

    @staticmethod
    def _parse_datetime(record: Dict[str, Any]) -> datetime:
        dt = record.get("detected_at") or record.get("acquired_at")
        if isinstance(dt, datetime):
            return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
        if isinstance(dt, str):
            try:
                return datetime.fromisoformat(dt.replace("Z", "+00:00"))
            except Exception:
                pass
        
        # Parse from acq_date and acq_time
        d_str = str(record.get("acq_date", "")).strip()
        t_str = str(record.get("acq_time", "")).strip().zfill(4)
        if d_str and t_str:
            try:
                hr = int(t_str[:2])
                mn = int(t_str[2:4])
                base_d = datetime.strptime(d_str, "%Y-%m-%d")
                return base_d.replace(hour=hr, minute=mn, tzinfo=timezone.utc)
            except Exception:
                pass
        return datetime.now(timezone.utc)

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

    def fuse_observations(self, records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Groups raw FIRMS observations into consolidated observation groups.
        Never discards duplicate/corroborating observations.
        
        Returns a list of FusedObservation objects containing:
          - observation_group_id
          - raw_observations (complete list of preserved inputs)
          - fused_latitude, fused_longitude (weighted by sensor quality)
          - fused_frp, peak_frp, mean_frp
          - cross_sensor_confirmation (bool)
          - sensor_consensus (0.0 to 1.0)
          - sensors (list of distinct platforms)
          - fusion_explanation
        """
        if not records:
            return []

        # Parse records with computed timestamps and weights
        enriched: List[Dict[str, Any]] = []
        for r in records:
            dt = self._parse_datetime(r)
            lat = float(r.get("latitude", 0.0))
            lon = float(r.get("longitude", 0.0))
            frp = float(r.get("frp", 0.0) or 0.0)
            weight, audit = self.calculate_sensor_weight(r)
            enriched.append({
                "raw": r,
                "lat": lat,
                "lon": lon,
                "dt": dt,
                "frp": frp,
                "weight": weight,
                "audit": audit,
                "satellite": str(r.get("satellite", "UNKNOWN")).strip().upper()
            })

        # Sort chronologically
        enriched.sort(key=lambda x: x["dt"])

        # Spatial-temporal cluster grouping with strict bounding to prevent single-linkage runaway chaining
        clusters: List[List[Dict[str, Any]]] = []
        for item in enriched:
            matched_cluster = None
            for c in clusters:
                # 1. Temporal span bound: total duration of cluster cannot exceed temporal_window_hours
                earliest_dt = min(x["dt"] for x in c)
                time_span_hrs = abs((item["dt"] - earliest_dt).total_seconds()) / 3600.0
                if time_span_hrs > self.temporal_window_hours:
                    continue

                # 2. Centroid distance bound: candidate must be within spatial_radius_meters of cluster center
                c_lat = sum(x["lat"] for x in c) / len(c)
                c_lon = sum(x["lon"] for x in c) / len(c)
                dist_centroid = self.haversine_distance_m(item["lat"], item["lon"], c_lat, c_lon)
                if dist_centroid > self.spatial_radius_meters:
                    continue

                # 3. Maximum pairwise distance guard (complete linkage safety factor)
                if any(self.haversine_distance_m(item["lat"], item["lon"], x["lat"], x["lon"]) > (self.spatial_radius_meters * 1.5) for x in c):
                    continue

                matched_cluster = c
                break

            if matched_cluster is not None:
                matched_cluster.append(item)
            else:
                clusters.append([item])

        # Formulate fused representation for each cluster
        fused_results: List[Dict[str, Any]] = []
        for c in clusters:
            first_obs = min(x["dt"] for x in c)
            last_obs = max(x["dt"] for x in c)

            total_w = sum(x["weight"] for x in c) or 1.0
            fused_lat = sum(x["lat"] * x["weight"] for x in c) / total_w
            fused_lon = sum(x["lon"] * x["weight"] for x in c) / total_w
            
            frps = [x["frp"] for x in c if x["frp"] > 0]
            peak_frp = round(max(frps), 1) if frps else 0.0
            mean_frp = round(sum(frps) / len(frps), 1) if frps else 0.0
            weighted_frp = round(sum(x["frp"] * x["weight"] for x in c) / total_w, 1)

            sensors = sorted(list(set(x["satellite"] for x in c)))
            unique_sensor_count = len(sensors)
            total_observations = len(c)
            cross_sensor_confirmed = (unique_sensor_count >= 2)

            # Consensus metric: ratio of consistent non-zero FRP measurements
            sensor_consensus = round(min(1.0, (unique_sensor_count / max(1, total_observations)) * 0.5 + 0.5), 2) if total_observations > 1 else 1.0

            # Deterministic group hash ID
            seed = f"{fused_lat:.4f}_{fused_lon:.4f}_{first_obs.isoformat()}_{total_observations}"
            grp_hash = hashlib.sha256(seed.encode()).hexdigest()[:10].upper()
            group_id = f"OBSGRP-{first_obs.strftime('%Y%m%d')}-{grp_hash}"

            # Human-readable explanation
            if cross_sensor_confirmed:
                expl = (
                    f"Corroborated thermal event verified by {unique_sensor_count} distinct satellite platforms "
                    f"({', '.join(sensors)}) across {total_observations} passes. "
                    f"Peak FRP: {peak_frp} MW, Quality-weighted mean: {weighted_frp} MW."
                )
            elif total_observations > 1:
                expl = (
                    f"Repeated single-platform observation ({sensors[0]}) with {total_observations} passes "
                    f"confirming persistence. Peak FRP: {peak_frp} MW."
                )
            else:
                expl = f"Single-satellite detection from {sensors[0]} (FRP: {peak_frp} MW)."

            fused_results.append({
                "observation_group_id": group_id,
                "sensor_count": total_observations,
                "unique_sensor_count": unique_sensor_count,
                "sensors": sensors,
                "cross_sensor_confirmation": cross_sensor_confirmed,
                "sensor_consensus": sensor_consensus,
                "first_observed_at": first_obs.isoformat(),
                "last_observed_at": last_obs.isoformat(),
                "fused_latitude": round(fused_lat, 6),
                "fused_longitude": round(fused_lon, 6),
                "fused_frp": weighted_frp,
                "peak_frp": peak_frp,
                "mean_frp": mean_frp,
                "fusion_explanation": expl,
                "raw_observations": [x["raw"] for x in c],
                "observation_weights": [
                    {"satellite": x["satellite"], "frp": x["frp"], "weight": x["weight"], "audit": x["audit"]}
                    for x in c
                ]
            })

        return fused_results
