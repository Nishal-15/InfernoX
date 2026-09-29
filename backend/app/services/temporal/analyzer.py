import logging
import math
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.models.thermal_event import ThermalEvent
from app.core.config import settings

logger = logging.getLogger(__name__)

class TemporalAnalyzer:
    """
    Temporal Intelligence Engine.
    Analyzes historical thermal cluster behavior to compute persistence,
    duration, FRP statistics, spatial spread, and event states (NEW, RECURRING, PERSISTENT, ABNORMAL).
    """
    def __init__(
        self,
        radius_meters: Optional[float] = None,
        lookback_days: Optional[int] = None,
        persistence_min_days: Optional[int] = None,
        recurring_min_detections: Optional[int] = None,
        abnormal_frp_multiplier: Optional[float] = None
    ):
        self.radius_meters = radius_meters or settings.SPATIAL_CLUSTER_RADIUS_METERS
        self.lookback_days = lookback_days or settings.TEMPORAL_LOOKBACK_DAYS
        self.min_active_days_persistent = persistence_min_days or settings.PERSISTENCE_MIN_ACTIVE_DAYS
        self.min_detections_recurring = recurring_min_detections or settings.RECURRING_MIN_DETECTIONS
        self.abnormal_frp_multiplier = abnormal_frp_multiplier or settings.ABNORMAL_FRP_MULTIPLIER

    def determine_status(
        self,
        current_frp: Optional[float],
        cluster_detection_count: int,
        active_days: int,
        mean_frp: Optional[float]
    ) -> str:
        """
        Determines event state based on configurable thresholds.
        States: NEW, RECURRING, PERSISTENT, ABNORMAL
        """
        # If there is only the current detection or no history
        if cluster_detection_count <= 1:
            return "NEW"

        # Check for abnormal spike: current FRP significantly higher than historical baseline
        if current_frp is not None and mean_frp is not None and mean_frp > 0:
            if current_frp >= (mean_frp * self.abnormal_frp_multiplier):
                return "ABNORMAL"

        # Check for persistent thermal activity
        if active_days >= self.min_active_days_persistent:
            return "PERSISTENT"

        # Check for recurring activity
        if cluster_detection_count >= self.min_detections_recurring:
            return "RECURRING"

        return "NEW"

    def compute_metrics(
        self,
        current_event: Dict[str, Any],
        cluster_records: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Pure calculation function: processes cluster points and returns all temporal metrics.
        Can be used both with database query results and direct test objects.
        """
        all_records = list(cluster_records)
        # Ensure current event is included in total cluster metrics if not already
        current_id = current_event.get("id")
        has_current = any(r.get("id") == current_id for r in all_records if current_id is not None)
        if not has_current:
            all_records.append(current_event)

        # Sort all records chronologically
        def get_dt(r):
            dt = r.get("detected_at")
            if isinstance(dt, str):
                try:
                    return datetime.fromisoformat(dt.replace("Z", "+00:00"))
                except Exception:
                    return datetime.min.replace(tzinfo=timezone.utc)
            elif isinstance(dt, datetime):
                return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
            return datetime.min.replace(tzinfo=timezone.utc)

        all_records.sort(key=get_dt)

        event_count = len(all_records)
        unique_days = set()
        frp_values = []
        distances = []

        first_detection = None
        last_detection = None

        timeline = []
        for r in all_records:
            dt = get_dt(r)
            if first_detection is None or dt < first_detection:
                first_detection = dt
            if last_detection is None or dt > last_detection:
                last_detection = dt

            unique_days.add(dt.date())
            frp = r.get("frp")
            if frp is not None and isinstance(frp, (int, float)) and frp > 0:
                frp_values.append(float(frp))
            
            dist = r.get("distance", 0.0)
            if dist is not None and isinstance(dist, (int, float)):
                distances.append(float(dist))

            timeline.append({
                "id": r.get("id"),
                "detected_at": dt.isoformat(),
                "frp": frp,
                "confidence": r.get("confidence"),
                "distance_m": round(float(dist), 1) if dist else 0.0,
                "is_current": (r.get("id") == current_id)
            })

        active_days = len(unique_days)
        duration_hours = 0.0
        if first_detection and last_detection:
            duration_hours = round((last_detection - first_detection).total_seconds() / 3600.0, 1)

        mean_frp = round(sum(frp_values) / len(frp_values), 1) if frp_values else 0.0
        max_frp = round(max(frp_values), 1) if frp_values else 0.0
        
        # Standard deviation of FRP
        if len(frp_values) > 1:
            variance = sum((x - mean_frp) ** 2 for x in frp_values) / (len(frp_values) - 1)
            frp_std = round(math.sqrt(variance), 1)
        else:
            frp_std = 0.0

        current_frp = current_event.get("frp") or 0.0
        frp_deviation_ratio = round(current_frp / mean_frp, 2) if (mean_frp > 0 and current_frp) else 1.0

        # Spatial spread (max distance or mean distance from centroid)
        spatial_spread_meters = round(max(distances), 1) if distances else 0.0

        # Detection frequency (detections per active day)
        detection_frequency = round(event_count / max(1, active_days), 2)

        # Baseline mean FRP excluding the current event for clean deviation checking
        hist_frps = [r.get("frp") for r in cluster_records if r.get("frp") and r.get("id") != current_id]
        baseline_mean_frp = (sum(hist_frps) / len(hist_frps)) if hist_frps else mean_frp

        # Robust statistics: Median & MAD (Median Absolute Deviation)
        sorted_frps = sorted(frp_values) if frp_values else []
        n_frps = len(sorted_frps)
        if n_frps > 0:
            mid = n_frps // 2
            median_frp = round((sorted_frps[mid] if n_frps % 2 != 0 else (sorted_frps[mid - 1] + sorted_frps[mid]) / 2.0), 1)
            deviations = sorted(abs(x - median_frp) for x in sorted_frps)
            mad_frp = round((deviations[mid] if n_frps % 2 != 0 else (deviations[mid - 1] + deviations[mid]) / 2.0), 1)
        else:
            median_frp = 0.0
            mad_frp = 0.0

        # FRP Acceleration and time since previous detection
        frp_acceleration = 0.0
        time_since_prev_hrs = None
        curr_idx = -1
        for idx, rec in enumerate(all_records):
            if rec.get("id") == current_id and current_id is not None:
                curr_idx = idx
                break

        if curr_idx > 0:
            prev_event = all_records[curr_idx - 1]
        elif curr_idx == -1 and len(all_records) >= 1:
            curr_dt = get_dt(current_event)
            preceding = [r for r in all_records if get_dt(r) < curr_dt]
            prev_event = preceding[-1] if preceding else None
        else:
            prev_event = None

        if prev_event is not None:
            prev_dt = get_dt(prev_event)
            curr_dt = get_dt(current_event)
            prev_frp = float(prev_event.get("frp") or 0.0)
            time_delta_hrs = (curr_dt - prev_dt).total_seconds() / 3600.0 if curr_dt > prev_dt else 0.0
            time_since_prev_hrs = round(time_delta_hrs, 2)
            if 0.1 <= time_delta_hrs <= 72.0:
                frp_acceleration = round((current_frp - prev_frp) / time_delta_hrs, 2)

        # Robust Z-Score: (current - median) / (1.4826 * MAD)
        # Avoid unstable statistics when sample size is too small (< 4)
        # Handle degenerate zero-variance baseline (MAD = 0) with 10% median / minimum floor
        if event_count >= 4:
            scale = 1.4826 * mad_frp
            if scale <= 1e-4:
                scale = max(0.10 * median_frp, 1.0)
            robust_z_score = round(abs(current_frp - median_frp) / scale, 2)
        else:
            robust_z_score = 0.0

        # Temporal confidence rating based on empirical sample size
        if event_count >= 5:
            temporal_conf = "HIGH"
            baseline_rel = "SUFFICIENT_SAMPLE_SIZE"
        elif event_count >= 3:
            temporal_conf = "MEDIUM"
            baseline_rel = "SUFFICIENT_SAMPLE_SIZE"
        else:
            temporal_conf = "LOW"
            baseline_rel = "INSUFFICIENT_SAMPLE_SIZE"

        # Persistence confidence score (0.0 to 1.0)
        p_day_ratio = min(1.0, active_days / max(1, self.min_active_days_persistent))
        p_count_ratio = min(1.0, event_count / 10.0)
        persistence_confidence = round(0.6 * p_day_ratio + 0.4 * p_count_ratio, 2)

        # Stationary thermal source vs spreading fire confidence
        # Gas flares/refineries stay within tight spatial radius (< 350m) despite many detections
        spread_rate_m_per_hr = round(spatial_spread_meters / max(1.0, duration_hours), 2)
        if event_count >= 3 and spatial_spread_meters <= 400.0:
            stationary_confidence = round(min(1.0, 0.5 + (0.5 * (1.0 - (spatial_spread_meters / 400.0)))), 2)
        elif spatial_spread_meters > 800.0:
            stationary_confidence = round(max(0.0, 0.3 - (spatial_spread_meters / 5000.0)), 2)
        else:
            stationary_confidence = 0.5

        status = self.determine_status(
            current_frp=current_frp,
            cluster_detection_count=event_count,
            active_days=active_days,
            mean_frp=baseline_mean_frp
        )

        return {
            "status": "success",
            "temporal_status": status,
            "temporal_confidence": temporal_conf,
            "baseline_reliability": baseline_rel,
            "metrics": {
                "event_count": event_count,
                "sample_count": event_count,
                "active_days": active_days,
                "first_detection": first_detection.isoformat() if first_detection else None,
                "last_detection": last_detection.isoformat() if last_detection else None,
                "duration_hours": duration_hours,
                "mean_frp": mean_frp,
                "median_frp": median_frp,
                "mad_frp": mad_frp,
                "max_frp": max_frp,
                "robust_z_score": robust_z_score,
                "frp_std": frp_std,
                "frp_deviation_ratio": frp_deviation_ratio,
                "frp_anomaly_magnitude_mw": round(abs(current_frp - median_frp), 1),
                "frp_acceleration_mw_per_hour": frp_acceleration,
                "time_since_previous_detection_hours": time_since_prev_hrs,
                "spatial_spread_meters": spatial_spread_meters,
                "detection_frequency": detection_frequency,
                "persistence_confidence": persistence_confidence,
                "stationary_confidence": stationary_confidence,
                "spread_rate_m_per_hour": spread_rate_m_per_hr,
                "temporal_confidence": temporal_conf,
                "baseline_reliability": baseline_rel,
                "spatial_radius_m": self.radius_meters,
                "lookback_days": self.lookback_days
            },
            "timeline": timeline
        }



    def analyze_event(self, db: Session, event_id: int) -> Dict[str, Any]:
        """
        Analyzes a specific event using PostGIS spatial clustering over the lookback window.
        """
        event = db.query(ThermalEvent).filter(ThermalEvent.id == event_id).first()
        if not event:
            return {"status": "error", "message": f"Event {event_id} not found"}

        point_geom = f"SRID=4326;POINT({event.longitude} {event.latitude})"
        lookback_date = datetime.now(timezone.utc) - timedelta(days=self.lookback_days)
        
        # PostGIS query: Find all detections within radius_meters over lookback_days
        try:
            historical_query = db.query(
                ThermalEvent,
                text(f"ST_Distance(geometry::geography, ST_GeomFromEWKT('{point_geom}')::geography) as dist")
            ).filter(
                ThermalEvent.detected_at >= lookback_date,
                text(f"ST_DWithin(geometry::geography, ST_GeomFromEWKT('{point_geom}')::geography, {self.radius_meters})")
            ).order_by(ThermalEvent.detected_at.asc()).all()
        except Exception:
            # Fallback for non-PostGIS / SQLite test environments
            import math
            all_events = db.query(ThermalEvent).filter(ThermalEvent.detected_at >= lookback_date).all()
            matched = []
            for e in all_events:
                dlat = (e.latitude - event.latitude) * 111000
                dlon = (e.longitude - event.longitude) * 111000 * math.cos(math.radians(event.latitude))
                dist = math.sqrt(dlat**2 + dlon**2)
                if dist <= self.radius_meters:
                    matched.append((e, dist))
            matched.sort(key=lambda x: x[0].detected_at if x[0].detected_at else datetime.min)
            historical_query = matched

        cluster_records = []
        for e, dist in historical_query:
            cluster_records.append({
                "id": e.id,
                "detected_at": e.detected_at,
                "frp": e.frp,
                "confidence": e.confidence,
                "distance": dist
            })

        current_dict = {
            "id": event.id,
            "detected_at": event.detected_at,
            "frp": event.frp,
            "confidence": event.confidence,
            "distance": 0.0
        }

        return self.compute_metrics(current_dict, cluster_records)
