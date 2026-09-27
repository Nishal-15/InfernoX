from fastapi import APIRouter, Depends, Query, HTTPException # type: ignore
from sqlalchemy.orm import Session # type: ignore
from sqlalchemy import text # type: ignore
from app.api.deps import get_db
from app.models.facility import Facility
from app.models.thermal_event import ThermalEvent
from app.schemas.facility import FacilityOut, PaginatedFacilities
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone, timedelta
from fastapi.responses import JSONResponse # type: ignore
import math

router = APIRouter()

@router.get("", response_model=PaginatedFacilities)
def get_facilities(
    db: Session = Depends(get_db),
    facility_type: Optional[str] = None,
    limit: int = Query(100, le=1000),
    offset: int = 0
):
    query = db.query(Facility)
    
    if facility_type:
        query = query.filter(Facility.facility_type == facility_type)
        
    total = query.count()
    items = query.offset(offset).limit(limit).all()
    
    return {"items": items, "total": total, "limit": limit, "offset": offset}

@router.get("/geojson")
def get_facilities_geojson(
    db: Session = Depends(get_db),
    facility_type: Optional[str] = None,
    limit: int = Query(1000, le=10000)
):
    query = db.query(Facility)
    
    if facility_type:
        query = query.filter(Facility.facility_type == facility_type)
        
    facilities = query.limit(limit).all()
    
    features = []
    for f in facilities:
        features.append({
            "type": "Feature",
            "geometry": {
                "type": "Point",
                "coordinates": [f.longitude, f.latitude]
            },
            "properties": {
                "id": f.id,
                "osm_id": f.osm_id,
                "name": f.name,
                "facility_type": f.facility_type,
                "operator": f.operator,
                "source": f.source
            }
        })
        
    return JSONResponse(content={
        "type": "FeatureCollection",
        "features": features
    })

@router.get("/nearby")
def get_nearby_facilities(
    latitude: float,
    longitude: float,
    radius_km: float = Query(5.0, gt=0),
    db: Session = Depends(get_db)
):
    distance_meters = radius_km * 1000.0
    point_geom = f"SRID=4326;POINT({longitude} {latitude})"
    
    try:
        query = db.query(Facility).filter(
            text(f"ST_DWithin(geometry::geography, ST_GeomFromEWKT('{point_geom}')::geography, {distance_meters})")
        )
        return query.all()
    except Exception:
        # Fallback for non-PostGIS / SQLite
        all_facs = db.query(Facility).all()
        result = []
        for f in all_facs:
            dlat = (f.latitude - latitude) * 111000
            dlon = (f.longitude - longitude) * 111000 * math.cos(math.radians(latitude))
            dist = math.sqrt(dlat**2 + dlon**2)
            if dist <= distance_meters:
                result.append(f)
        return result

@router.get("/{facility_id}", response_model=FacilityOut)
def get_facility(facility_id: int, db: Session = Depends(get_db)):
    facility = db.query(Facility).filter(Facility.id == facility_id).first()
    if not facility:
        raise HTTPException(status_code=404, detail="Facility not found")
    return facility

@router.get("/{facility_id}/investigation")
def get_facility_investigation(
    facility_id: int, 
    radius_km: float = Query(3.0, gt=0),
    db: Session = Depends(get_db)
):
    """
    Returns complete facility investigation context: infrastructure metadata,
    thermal event density, persistent sources, risk level, and recent nearby detections.
    """
    facility = db.query(Facility).filter(Facility.id == facility_id).first()
    if not facility:
        raise HTTPException(status_code=404, detail="Facility not found")

    distance_meters = radius_km * 1000.0
    point_geom = f"SRID=4326;POINT({facility.longitude} {facility.latitude})"

    try:
        nearby_events_query = db.query(
            ThermalEvent,
            text(f"ST_Distance(geometry::geography, ST_GeomFromEWKT('{point_geom}')::geography) as distance_meters")
        ).filter(
            text(f"ST_DWithin(geometry::geography, ST_GeomFromEWKT('{point_geom}')::geography, {distance_meters})")
        ).order_by(ThermalEvent.detected_at.desc()).all()
    except Exception:
        # Haversine / Euclidean fallback
        all_events = db.query(ThermalEvent).all()
        matched = []
        for e in all_events:
            dlat = (e.latitude - facility.latitude) * 111000
            dlon = (e.longitude - facility.longitude) * 111000 * math.cos(math.radians(facility.latitude))
            dist = math.sqrt(dlat**2 + dlon**2)
            if dist <= distance_meters:
                matched.append((e, dist))
        matched.sort(key=lambda x: x[0].detected_at if x[0].detected_at else datetime.min, reverse=True)
        nearby_events_query = matched

    events_list = []
    clusters = set()
    frp_vals = []
    last_detected = None

    for item in nearby_events_query:
        ev = item[0]
        dist = item[1]
        if last_detected is None and ev.detected_at:
            last_detected = ev.detected_at.isoformat()
        if ev.frp is not None:
            frp_vals.append(ev.frp)
        # Cluster key based on spatial resolution (approx 1km)
        cluster_key = f"{round(ev.latitude, 2)}_{round(ev.longitude, 2)}"
        clusters.add(cluster_key)

        events_list.append({
            "id": ev.id,
            "detected_at": ev.detected_at.isoformat() if ev.detected_at else None,
            "latitude": ev.latitude,
            "longitude": ev.longitude,
            "confidence": ev.confidence,
            "frp": ev.frp,
            "brightness_temperature": ev.brightness_temperature,
            "status": getattr(ev, "status", "NEW") or "NEW",
            "distance_meters": round(dist, 1)
        })

    total_events = len(events_list)
    mean_frp = round(float(sum(frp_vals) / len(frp_vals)), 1) if frp_vals else 0.0
    max_frp = round(float(max(frp_vals)), 1) if frp_vals else 0.0

    if max_frp > 100 or total_events >= 20:
        risk_level = "CRITICAL"
    elif max_frp > 45 or total_events >= 5:
        risk_level = "ELEVATED"
    elif total_events > 0:
        risk_level = "MODERATE"
    else:
        risk_level = "NOMINAL"

    return {
        "facility": {
            "id": facility.id,
            "osm_id": facility.osm_id,
            "name": facility.name,
            "facility_type": facility.facility_type,
            "operator": facility.operator,
            "latitude": facility.latitude,
            "longitude": facility.longitude,
            "source": facility.source
        },
        "metrics": {
            "total_thermal_events": total_events,
            "persistent_sources_count": len(clusters),
            "last_event_detected_at": last_detected,
            "mean_frp": mean_frp,
            "max_frp": max_frp,
            "risk_level": risk_level,
            "search_radius_km": radius_km
        },
        "nearby_events": events_list[:25]
    }

@router.get("/{facility_id}/timeline")
def get_facility_timeline(
    facility_id: int,
    days: int = Query(30, ge=7, le=180),
    radius_km: float = Query(3.0, gt=0),
    db: Session = Depends(get_db)
):
    """
    Returns weekly and daily thermal anomaly aggregates for the facility over the specified time window.
    """
    facility = db.query(Facility).filter(Facility.id == facility_id).first()
    if not facility:
        raise HTTPException(status_code=404, detail="Facility not found")

    distance_meters = radius_km * 1000.0
    point_geom = f"SRID=4326;POINT({facility.longitude} {facility.latitude})"
    cutoff_time = datetime.now(timezone.utc) - timedelta(days=days)

    try:
        events = db.query(ThermalEvent).filter(
            text(f"ST_DWithin(geometry::geography, ST_GeomFromEWKT('{point_geom}')::geography, {distance_meters})"),
            ThermalEvent.detected_at >= cutoff_time
        ).order_by(ThermalEvent.detected_at.asc()).all()
    except Exception:
        # Fallback
        all_events = db.query(ThermalEvent).filter(ThermalEvent.detected_at >= cutoff_time).all()
        events = []
        for e in all_events:
            dlat = (e.latitude - facility.latitude) * 111000
            dlon = (e.longitude - facility.longitude) * 111000 * math.cos(math.radians(facility.latitude))
            dist = math.sqrt(dlat**2 + dlon**2)
            if dist <= distance_meters:
                events.append(e)

    # 4 weekly buckets
    num_weeks = max(4, math.ceil(days / 7))
    now = datetime.now(timezone.utc)
    weekly_buckets = []
    for w in range(num_weeks):
        w_start = now - timedelta(days=(w + 1) * 7)
        w_end = now - timedelta(days=w * 7)
        w_events = [e for e in events if e.detected_at and (w_start <= (e.detected_at if e.detected_at.tzinfo else e.detected_at.replace(tzinfo=timezone.utc)) < w_end)]
        w_frps = [e.frp for e in w_events if e.frp is not None]
        weekly_buckets.append({
            "week_label": f"Week {num_weeks - w}",
            "start_date": w_start.strftime("%Y-%m-%d"),
            "end_date": w_end.strftime("%Y-%m-%d"),
            "count": len(w_events),
            "mean_frp": round(float(sum(w_frps) / len(w_frps)), 1) if w_frps else 0.0,
            "max_frp": round(float(max(w_frps)), 1) if w_frps else 0.0
        })

    weekly_buckets.reverse()

    return {
        "facility_id": facility.id,
        "facility_name": facility.name,
        "time_window_days": days,
        "total_detections": len(events),
        "weekly_activity": weekly_buckets
    }
