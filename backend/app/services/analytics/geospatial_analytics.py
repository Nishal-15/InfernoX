import math
from datetime import datetime
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session

from app.models.thermal_event import ThermalEvent
from app.models.risk_alert import RiskAssessment, Alert
from app.schemas.analytics import GeospatialCell, GeospatialHeatmapResponse


class GeospatialAnalyticsService:
    @staticmethod
    def get_spatial_heatmap_grid(
        db: Session,
        resolution_deg: float = 0.25,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        min_frp: Optional[float] = None
    ) -> GeospatialHeatmapResponse:
        """
        PostGIS/Coordinate spatial grid binning for heatmap and density analytics.
        """
        query = db.query(
            ThermalEvent.id,
            ThermalEvent.latitude,
            ThermalEvent.longitude,
            ThermalEvent.frp,
            ThermalEvent.confidence
        )
        if start_date:
            query = query.filter(ThermalEvent.detected_at >= start_date)
        if end_date:
            query = query.filter(ThermalEvent.detected_at <= end_date)
        if min_frp is not None:
            query = query.filter(ThermalEvent.frp >= min_frp)

        events = query.all()
        if not events:
            return GeospatialHeatmapResponse(
                grid_resolution_deg=resolution_deg,
                cell_count=0,
                cells=[],
                geojson={"type": "FeatureCollection", "features": []}
            )

        # Cross reference risks & alerts
        event_ids = [e[0] for e in events]
        high_risk_event_ids = set()
        risks = db.query(RiskAssessment.event_id, RiskAssessment.risk_level).filter(
            RiskAssessment.event_id.in_(event_ids)
        ).all()
        for r_eid, r_lvl in risks:
            if (r_lvl or "").upper() in ("CRITICAL", "HIGH"):
                high_risk_event_ids.add(r_eid)

        alerts = db.query(Alert.event_id).filter(Alert.event_id.in_(event_ids)).all()
        alert_event_ids = set(a[0] for a in alerts)

        # Grid bucketing
        grid_bins: Dict[str, Dict[str, Any]] = {}
        for ev in events:
            eid, lat, lon, frp, conf = ev
            if lat is None or lon is None:
                continue

            grid_x = math.floor(lon / resolution_deg)
            grid_y = math.floor(lat / resolution_deg)
            cell_id = f"cell_{grid_y}_{grid_x}"

            if cell_id not in grid_bins:
                min_lat = round(grid_y * resolution_deg, 4)
                max_lat = round((grid_y + 1) * resolution_deg, 4)
                min_lon = round(grid_x * resolution_deg, 4)
                max_lon = round((grid_x + 1) * resolution_deg, 4)
                center_lat = round((min_lat + max_lat) / 2.0, 4)
                center_lon = round((min_lon + max_lon) / 2.0, 4)

                grid_bins[cell_id] = {
                    "cell_id": cell_id,
                    "latitude": center_lat,
                    "longitude": center_lon,
                    "bounds": [min_lat, min_lon, max_lat, max_lon],
                    "events": []
                }

            grid_bins[cell_id]["events"].append(ev)

        cells: List[GeospatialCell] = []
        geojson_features: List[Dict[str, Any]] = []

        for cell_id, data in grid_bins.items():
            ev_list = data["events"]
            cnt = len(ev_list)
            frps = [e[3] for e in ev_list if e[3] is not None]
            avg_frp = round(float(sum(frps) / len(frps)), 2) if frps else 0.0
            max_frp = round(float(max(frps)), 2) if frps else 0.0

            persistent_count = sum(1 for e in ev_list if (e[4] or 0) > 80 and (e[3] or 0) > 40)
            high_risk_count = sum(1 for e in ev_list if e[0] in high_risk_event_ids or (e[3] or 0) >= 60)
            alert_count = sum(1 for e in ev_list if e[0] in alert_event_ids)

            min_lat, min_lon, max_lat, max_lon = data["bounds"]

            cell = GeospatialCell(
                cell_id=cell_id,
                latitude=data["latitude"],
                longitude=data["longitude"],
                bounds=data["bounds"],
                event_count=cnt,
                avg_frp=avg_frp,
                max_frp=max_frp,
                persistent_count=persistent_count,
                high_risk_count=high_risk_count,
                alert_count=alert_count
            )
            cells.append(cell)

            # Build GeoJSON Polygon
            geojson_features.append({
                "type": "Feature",
                "id": cell_id,
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [[
                        [min_lon, min_lat],
                        [max_lon, min_lat],
                        [max_lon, max_lat],
                        [min_lon, max_lat],
                        [min_lon, min_lat]
                    ]]
                },
                "properties": {
                    "cell_id": cell_id,
                    "event_count": cnt,
                    "average_frp": avg_frp,
                    "max_frp": max_frp,
                    "persistent_count": persistent_count,
                    "high_risk_count": high_risk_count,
                    "alert_count": alert_count,
                    "centroid": [data["longitude"], data["latitude"]]
                }
            })

        cells.sort(key=lambda c: c.event_count, reverse=True)

        return GeospatialHeatmapResponse(
            grid_resolution_deg=resolution_deg,
            cell_count=len(cells),
            cells=cells,
            geojson={
                "type": "FeatureCollection",
                "features": geojson_features
            }
        )
