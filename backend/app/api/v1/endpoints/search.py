from fastapi import APIRouter, Depends, Query, HTTPException # type: ignore
from sqlalchemy.orm import Session # type: ignore
from sqlalchemy import text # type: ignore
from app.api.deps import get_db
from app.models.thermal_event import ThermalEvent
from app.models.facility import Facility
from typing import Optional, List, Dict, Any
import re
import math

router = APIRouter()

def execute_search(query: str, db: Session) -> Dict[str, Any]:
    """
    Search across facilities, thermal events, coordinates, and classifications.
    """
    q = query.strip()
    results: Dict[str, Any] = {
        "query": q,
        "facilities": [],
        "events": [],
        "coordinates": None
    }

    # 1. Coordinate search: check for "lat, lon" pattern
    coord_match = re.match(r"^[-+]?([1-8]?\d(\.\d+)?|90(\.0+)?)[,\s]+[-+]?(180(\.0+)?|((1[0-7]\d)|([1-9]?\d))(\.\d+)?)$", q)
    if coord_match:
        try:
            parts = re.split(r"[,\s]+", q)
            lat, lon = float(parts[0]), float(parts[1])
            results["coordinates"] = {"latitude": lat, "longitude": lon}
            
            # Find closest events to coordinates
            point_geom = f"SRID=4326;POINT({lon} {lat})"
            try:
                nearby = db.query(ThermalEvent).filter(
                    text(f"ST_DWithin(geometry::geography, ST_GeomFromEWKT('{point_geom}')::geography, 50000)")
                ).order_by(ThermalEvent.detected_at.desc()).limit(5).all()
            except Exception:
                # Euclidean fallback
                all_e = db.query(ThermalEvent).all()
                all_e.sort(key=lambda e: (e.latitude - lat)**2 + (e.longitude - lon)**2)
                nearby = all_e[:5]
                
            for e in nearby:
                results["events"].append({
                    "id": e.id,
                    "event_code": f"INF-2026-{e.id:06d}",
                    "detected_at": e.detected_at.isoformat() if e.detected_at else None,
                    "latitude": e.latitude,
                    "longitude": e.longitude,
                    "confidence": e.confidence,
                    "frp": e.frp,
                    "status": getattr(e, "status", "NEW") or "NEW",
                    "satellite": e.satellite
                })
        except Exception:
            pass

    # 2. Search Facilities by name, osm_id, facility_type, operator
    facilities = db.query(Facility).filter(
        (Facility.name.ilike(f"%{q}%")) | 
        (Facility.osm_id.ilike(f"%{q}%")) |
        (Facility.facility_type.ilike(f"%{q}%")) |
        (Facility.operator.ilike(f"%{q}%"))
    ).limit(10).all()

    for f in facilities:
        results["facilities"].append({
            "id": f.id,
            "osm_id": f.osm_id,
            "name": f.name,
            "facility_type": f.facility_type,
            "operator": f.operator,
            "latitude": f.latitude,
            "longitude": f.longitude,
            "source": f.source
        })

    # 3. Search Events by ID / formatted string
    clean_id = re.sub(r"[^0-9]", "", q)
    if clean_id:
        try:
            event_id = int(clean_id)
            matched_events = db.query(ThermalEvent).filter(ThermalEvent.id == event_id).all()
            for e in matched_events:
                if not any(item["id"] == e.id for item in results["events"]):
                    results["events"].append({
                        "id": e.id,
                        "event_code": f"INF-2026-{e.id:06d}",
                        "detected_at": e.detected_at.isoformat() if e.detected_at else None,
                        "latitude": e.latitude,
                        "longitude": e.longitude,
                        "confidence": e.confidence,
                        "frp": e.frp,
                        "status": getattr(e, "status", "NEW") or "NEW",
                        "satellite": e.satellite
                    })
        except Exception:
            pass

    # 4. Search Events by satellite or status
    if not results["events"] and len(q) >= 2:
        attr_events = db.query(ThermalEvent).filter(
            (ThermalEvent.satellite.ilike(f"%{q}%")) |
            (ThermalEvent.source.ilike(f"%{q}%")) |
            (ThermalEvent.status.ilike(f"%{q}%"))
        ).order_by(ThermalEvent.detected_at.desc()).limit(10).all()

        for e in attr_events:
            results["events"].append({
                "id": e.id,
                "event_code": f"INF-2026-{e.id:06d}",
                "detected_at": e.detected_at.isoformat() if e.detected_at else None,
                "latitude": e.latitude,
                "longitude": e.longitude,
                "confidence": e.confidence,
                "frp": e.frp,
                "status": getattr(e, "status", "NEW") or "NEW",
                "satellite": e.satellite
            })

    return results

@router.get("")
def global_search_root(
    query: str = Query(..., min_length=1, description="Search term for facilities, event ID, satellite, coordinates"),
    db: Session = Depends(get_db)
):
    return execute_search(query, db)

@router.get("/search")
def global_search_alias(
    query: str = Query(..., min_length=1, description="Search term for facilities, event ID, satellite, coordinates"),
    db: Session = Depends(get_db)
):
    return execute_search(query, db)
