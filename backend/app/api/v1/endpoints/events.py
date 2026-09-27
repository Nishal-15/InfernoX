from fastapi import APIRouter, Depends, Query, HTTPException # type: ignore
from sqlalchemy.orm import Session # type: ignore
from sqlalchemy import text # type: ignore
from app.api.deps import get_db
from app.models.thermal_event import ThermalEvent
from app.models.facility import Facility
from app.models.ai_models import EventAssessment
from app.schemas.thermal_event import ThermalEventOut, PaginatedThermalEvents
from app.schemas.features import ThermalFeatures
from app.schemas.classification import ClassificationResponse
from app.schemas.review import AnalystReviewCreate, AnalystReviewOut
from app.services.features.engineer import FeatureEngineer
from app.services.classification.classifier import PrototypeClassifier
from app.services.ml.classifier import MLClassifier
from app.services.priority.engine import PriorityEngine
from app.services.review.service import ReviewService
from app.services.satellite.provider import Sentinel2Provider
from app.services.landcover.provider import LandCoverProvider
from app.services.temporal.analyzer import TemporalAnalyzer
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from pydantic import BaseModel
from fastapi.responses import JSONResponse # type: ignore
import logging
import math

logger = logging.getLogger(__name__)

router = APIRouter()

class EventStatusUpdate(BaseModel):
    status: str
    reason: Optional[str] = None

def _query_nearby_facilities(db: Session, longitude: float, latitude: float, radius_meters: float = 5000.0) -> List[Dict[str, Any]]:
    point_geom = f"SRID=4326;POINT({longitude} {latitude})"
    try:
        facilities_query = db.query(
            Facility, 
            text(f"ST_Distance(geometry::geography, ST_GeomFromEWKT('{point_geom}')::geography) as distance_meters")
        ).filter(
            text(f"ST_DWithin(geometry::geography, ST_GeomFromEWKT('{point_geom}')::geography, {radius_meters})")
        ).order_by(text("distance_meters ASC")).limit(10).all()
        
        nearby_facilities = []
        for fac, dist in facilities_query:
            nearby_facilities.append({
                "id": fac.id,
                "osm_id": fac.osm_id,
                "name": fac.name,
                "facility_type": fac.facility_type,
                "latitude": fac.latitude,
                "longitude": fac.longitude,
                "operator": fac.operator,
                "distance_meters": round(float(dist), 1)
            })
        return nearby_facilities
    except Exception:
        # Fallback for SQLite / non-PostGIS
        all_facs = db.query(Facility).all()
        matched = []
        for fac in all_facs:
            dlat = (fac.latitude - latitude) * 111000
            dlon = (fac.longitude - longitude) * 111000 * math.cos(math.radians(latitude))
            dist = math.sqrt(dlat**2 + dlon**2)
            if dist <= radius_meters:
                matched.append({
                    "id": fac.id,
                    "osm_id": fac.osm_id,
                    "name": fac.name,
                    "facility_type": fac.facility_type,
                    "latitude": fac.latitude,
                    "longitude": fac.longitude,
                    "operator": fac.operator,
                    "distance_meters": round(dist, 1)
                })
        matched.sort(key=lambda x: x["distance_meters"])
        return matched[:10]

def _query_historical_cluster(db: Session, longitude: float, latitude: float, radius_meters: float = 1500.0, target_id: Optional[int] = None) -> List[Dict[str, Any]]:
    point_geom = f"SRID=4326;POINT({longitude} {latitude})"
    try:
        hist_query = db.query(ThermalEvent).filter(
            text(f"ST_DWithin(geometry::geography, ST_GeomFromEWKT('{point_geom}')::geography, {radius_meters})")
        ).order_by(ThermalEvent.detected_at.asc()).limit(50).all()
    except Exception:
        all_events = db.query(ThermalEvent).all()
        matched = []
        for e in all_events:
            dlat = (e.latitude - latitude) * 111000
            dlon = (e.longitude - longitude) * 111000 * math.cos(math.radians(latitude))
            dist = math.sqrt(dlat**2 + dlon**2)
            if dist <= radius_meters:
                matched.append(e)
        matched.sort(key=lambda x: x.detected_at if x.detected_at else datetime.min)
        hist_query = matched[:50]

    historical_events = []
    for h in hist_query:
        historical_events.append({
            "id": h.id,
            "detected_at": h.detected_at.isoformat() if h.detected_at else None,
            "frp": h.frp,
            "brightness_temperature": h.brightness_temperature,
            "confidence": h.confidence,
            "latitude": h.latitude,
            "longitude": h.longitude,
            "satellite": h.satellite,
            "status": getattr(h, "status", "NEW") or "NEW",
            "is_current": h.id == target_id
        })
    return historical_events

@router.get("", response_model=PaginatedThermalEvents)
def get_events(
    db: Session = Depends(get_db),
    start: Optional[datetime] = None,
    end: Optional[datetime] = None,
    min_confidence: Optional[float] = None,
    satellite: Optional[str] = None,
    limit: int = Query(100, le=1000),
    offset: int = 0
):
    query = db.query(ThermalEvent)
    
    if start:
        query = query.filter(ThermalEvent.detected_at >= start)
    if end:
        query = query.filter(ThermalEvent.detected_at <= end)
    if min_confidence is not None:
        query = query.filter(ThermalEvent.confidence >= min_confidence)
    if satellite:
        query = query.filter(ThermalEvent.satellite == satellite)
        
    total = query.count()
    items = query.order_by(ThermalEvent.detected_at.desc()).offset(offset).limit(limit).all()
    
    return {"items": items, "total": total, "limit": limit, "offset": offset}

@router.get("/geojson")
def get_events_geojson(
    db: Session = Depends(get_db),
    start: Optional[datetime] = None,
    end: Optional[datetime] = None,
    min_confidence: Optional[float] = None,
    satellite: Optional[str] = None,
    limit: int = Query(1000, le=10000)
):
    """
    Returns valid GeoJSON FeatureCollection for thermal events.
    """
    query = db.query(ThermalEvent)
    
    if start:
        query = query.filter(ThermalEvent.detected_at >= start)
    if end:
        query = query.filter(ThermalEvent.detected_at <= end)
    if min_confidence is not None:
        query = query.filter(ThermalEvent.confidence >= min_confidence)
    if satellite:
        query = query.filter(ThermalEvent.satellite == satellite)
        
    events = query.order_by(ThermalEvent.detected_at.desc()).limit(limit).all()
    
    features = []
    for event in events:
        features.append({
            "type": "Feature",
            "geometry": {
                "type": "Point",
                "coordinates": [event.longitude, event.latitude]
            },
            "properties": {
                "id": event.id,
                "detected_at": event.detected_at.isoformat() if event.detected_at else None,
                "satellite": event.satellite,
                "confidence": event.confidence,
                "frp": event.frp,
                "brightness_temperature": event.brightness_temperature,
                "status": getattr(event, "status", "NEW") or "NEW",
                "source": event.source
            }
        })
        
    return JSONResponse(content={
        "type": "FeatureCollection",
        "features": features
    })

@router.get("/nearby")
def get_nearby_events(
    latitude: float,
    longitude: float,
    radius_km: float = Query(10.0, gt=0),
    db: Session = Depends(get_db)
):
    distance_meters = radius_km * 1000.0
    point_geom = f"SRID=4326;POINT({longitude} {latitude})"
    try:
        query = db.query(ThermalEvent).filter(
            text(f"ST_DWithin(geometry::geography, ST_GeomFromEWKT('{point_geom}')::geography, {distance_meters})")
        )
        return query.all()
    except Exception:
        all_events = db.query(ThermalEvent).all()
        matched = []
        for e in all_events:
            dlat = (e.latitude - latitude) * 111000
            dlon = (e.longitude - longitude) * 111000 * math.cos(math.radians(latitude))
            if math.sqrt(dlat**2 + dlon**2) <= distance_meters:
                matched.append(e)
        return matched

@router.get("/compare")
def compare_events(
    id1: int = Query(..., description="First event ID"),
    id2: int = Query(..., description="Second event ID"),
    db: Session = Depends(get_db)
):
    """
    Side-by-side analytical comparison of two thermal events.
    """
    ev1 = db.query(ThermalEvent).filter(ThermalEvent.id == id1).first()
    ev2 = db.query(ThermalEvent).filter(ThermalEvent.id == id2).first()

    if not ev1 or not ev2:
        missing = id1 if not ev1 else id2
        raise HTTPException(status_code=404, detail=f"Thermal event {missing} not found for comparison")

    def _get_summary_card(ev: ThermalEvent) -> Dict[str, Any]:
        analyzer = TemporalAnalyzer()
        temp = analyzer.analyze_event(db, ev.id)
        facs = _query_nearby_facilities(db, ev.longitude, ev.latitude, 5000.0)
        nearest = facs[0] if facs else None
        
        lc = LandCoverProvider().get_land_cover(ev.latitude, ev.longitude)
        sat = Sentinel2Provider().search_imagery(ev.latitude, ev.longitude, ev.detected_at)
        
        features = FeatureEngineer.extract_features(
            ev, 
            spatial_context={"nearest_facility": nearest, "distance_meters": nearest["distance_meters"] if nearest else None, "land_cover": lc}, 
            temporal_data=temp
        )
        
        try:
            clf = MLClassifier()
            res = clf.classify(features)
        except Exception:
            res = PrototypeClassifier().classify(features)

        p_score, p_level = PriorityEngine.evaluate_priority(features=features, classification=res["classification"])
        lc_dict = lc or {}
        sat_dict = sat or {}

        return {
            "id": ev.id,
            "detected_at": ev.detected_at.isoformat() if ev.detected_at else None,
            "frp": ev.frp,
            "confidence": ev.confidence,
            "status": getattr(ev, "status", "NEW") or "NEW",
            "duration_days": temp.get("duration_days", 1),
            "active_days": temp.get("active_days", 1),
            "temporal_status": temp.get("status", "NEW"),
            "nearest_facility_name": nearest["name"] if nearest else "None within 5km",
            "nearest_facility_type": nearest["facility_type"] if nearest else None,
            "distance_to_facility_meters": nearest["distance_meters"] if nearest else None,
            "classification": res["classification"],
            "model_probability": res.get("confidence_score", 0.0),
            "priority_level": p_level,
            "land_cover_category": lc_dict.get("category", "OTHER"),
            "satellite_status": sat_dict.get("evidence_status", "NOT_FOUND"),
            "ndvi": sat_dict.get("indices", {}).get("ndvi") if sat_dict.get("indices") else None,
            "nbr": sat_dict.get("indices", {}).get("nbr") if sat_dict.get("indices") else None
        }

    card_a = _get_summary_card(ev1)
    card_b = _get_summary_card(ev2)

    frp_ratio = round(float(card_a["frp"] / card_b["frp"]), 2) if card_a["frp"] and card_b["frp"] and card_b["frp"] > 0 else 1.0

    return {
        "event_a": card_a,
        "event_b": card_b,
        "comparison_metrics": {
            "frp_ratio_a_to_b": frp_ratio,
            "active_days_delta": card_a["active_days"] - card_b["active_days"],
            "same_classification": card_a["classification"] == card_b["classification"],
            "same_priority": card_a["priority_level"] == card_b["priority_level"]
        }
    }

@router.get("/{event_id}", response_model=ThermalEventOut)
def get_event(event_id: int, db: Session = Depends(get_db)):
    event = db.query(ThermalEvent).filter(ThermalEvent.id == event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    return event

@router.get("/{event_id}/context")
def get_event_context(event_id: int, db: Session = Depends(get_db)):
    """
    Enriches the thermal event with nearby infrastructure and land cover.
    """
    event = db.query(ThermalEvent).filter(ThermalEvent.id == event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
        
    nearby_facilities = _query_nearby_facilities(db, event.longitude, event.latitude, 5000.0)
    nearest_facility = nearby_facilities[0] if nearby_facilities else None
    min_distance = nearest_facility["distance_meters"] if nearest_facility else None
            
    # Land Cover
    lc_provider = LandCoverProvider()
    land_cover = lc_provider.get_land_cover(event.latitude, event.longitude)
    
    return {
        "event": {
            "id": event.id,
            "detected_at": event.detected_at.isoformat() if event.detected_at else None,
            "latitude": event.latitude,
            "longitude": event.longitude,
            "confidence": event.confidence,
            "frp": event.frp,
            "satellite": event.satellite,
            "status": getattr(event, "status", "NEW") or "NEW",
            "source": event.source
        },
        "nearest_facility": nearest_facility,
        "distance_meters": min_distance,
        "nearby_facilities_count": len(nearby_facilities),
        "nearby_facilities": nearby_facilities,
        "land_cover": land_cover
    }

@router.get("/{event_id}/temporal-analysis")
def get_temporal_analysis(event_id: int, db: Session = Depends(get_db)):
    """
    Returns historical clustering and baseline comparison for persistence detection.
    """
    analyzer = TemporalAnalyzer()
    result = analyzer.analyze_event(db, event_id)
    if result.get("status") == "error":
        raise HTTPException(status_code=404, detail=result.get("message"))
    return result

@router.get("/{event_id}/features", response_model=ThermalFeatures)
def get_event_features(event_id: int, db: Session = Depends(get_db)):
    """
    Computes and returns the deterministic Phase 4 ThermalFeatures vector.
    """
    event = db.query(ThermalEvent).filter(ThermalEvent.id == event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
        
    context = get_event_context(event_id, db)
    temporal = get_temporal_analysis(event_id, db)
    
    return FeatureEngineer.extract_features(event, spatial_context=context, temporal_data=temporal)

@router.get("/{event_id}/classification", response_model=ClassificationResponse)
def get_event_classification(event_id: int, db: Session = Depends(get_db)):
    """
    Retrieves the latest intelligence classification assessment for an event.
    """
    event = db.query(ThermalEvent).filter(ThermalEvent.id == event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    assessment = (
        db.query(EventAssessment)
        .filter(EventAssessment.event_id == event_id)
        .order_by(EventAssessment.created_at.desc())
        .first()
    )
    if not assessment:
        raise HTTPException(status_code=404, detail="No assessment found for this event. Run POST /classification first.")

    context = get_event_context(event_id, db)
    temporal = get_temporal_analysis(event_id, db)
    features = FeatureEngineer.extract_features(event, spatial_context=context, temporal_data=temporal)

    evidence_factors = assessment.evidence_factors
    if not evidence_factors and assessment.explanation:
        evidence_factors = [e.get("text", "") for e in assessment.explanation if isinstance(e, dict)]

    return ClassificationResponse(
        event_id=event.id,
        classification=assessment.classification,
        confidence_score=assessment.confidence_score,
        confidence_type=getattr(assessment, "confidence_type", "heuristic"),
        priority_score=assessment.priority_score,
        priority_level=assessment.priority_level,
        model_type=getattr(assessment, "model_type", "rule_based_prototype"),
        model_version=assessment.model_version,
        evidence_factors=evidence_factors or [],
        explanation=assessment.explanation,
        features=features,
        created_at=assessment.created_at
    )

@router.post("/{event_id}/classification", response_model=ClassificationResponse)
def classify_event(event_id: int, db: Session = Depends(get_db)):
    """
    Executes the multimodal intelligence pipeline on an event:
    Spatial Context -> Temporal Analysis -> Feature Engineering -> ML Classifier -> Priority Engine -> EventAssessment Persistence.
    """
    event = db.query(ThermalEvent).filter(ThermalEvent.id == event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    context = get_event_context(event_id, db)
    temporal = get_temporal_analysis(event_id, db)
    features = FeatureEngineer.extract_features(event, spatial_context=context, temporal_data=temporal)

    # Use MLClassifier if available, fallback to PrototypeClassifier
    try:
        classifier = MLClassifier()
        classification_res = classifier.classify(features)
    except Exception as e:
        logger.warning(f"MLClassifier unavailable in classify route: {e}, falling back to prototype")
        classifier = PrototypeClassifier()
        classification_res = classifier.classify(features)

    priority_score, priority_level = PriorityEngine.evaluate_priority(
        features=features,
        classification=classification_res["classification"]
    )

    assessment = EventAssessment(
        event_id=event.id,
        classification=classification_res["classification"],
        confidence_score=classification_res["confidence_score"],
        confidence_type=classification_res["confidence_type"],
        priority_score=priority_score,
        priority_level=priority_level,
        evidence_factors=classification_res["evidence_factors"],
        explanation=classification_res.get("explanation"),
        model_type=classification_res["model_type"],
        model_version=classification_res["model_version"],
        feature_schema_version="v2.0"
    )

    db.add(assessment)
    db.commit()
    db.refresh(assessment)

    return ClassificationResponse(
        event_id=event.id,
        classification=assessment.classification,
        confidence_score=assessment.confidence_score,
        confidence_type=assessment.confidence_type,
        priority_score=assessment.priority_score,
        priority_level=assessment.priority_level,
        model_type=assessment.model_type,
        model_version=assessment.model_version,
        evidence_factors=assessment.evidence_factors,
        explanation=assessment.explanation,
        features=features,
        created_at=assessment.created_at
    )

@router.get("/{event_id}/investigation")
def get_event_investigation(event_id: int, db: Session = Depends(get_db)):
    """
    Phase 5 Consolidated Event Investigation Workspace Endpoint.
    Returns complete spatial, temporal, satellite, ML, review, and provenance data in a single optimized payload.
    """
    event = db.query(ThermalEvent).filter(ThermalEvent.id == event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    # 1. Nearby infrastructure
    nearby_facilities = _query_nearby_facilities(db, event.longitude, event.latitude, 5000.0)
    nearest_facility = nearby_facilities[0] if nearby_facilities else None
    min_distance = nearest_facility["distance_meters"] if nearest_facility else None

    # 2. Land Cover
    lc_provider = LandCoverProvider()
    land_cover = lc_provider.get_land_cover(event.latitude, event.longitude)

    # 3. Temporal Intelligence
    analyzer = TemporalAnalyzer()
    temporal_data = analyzer.analyze_event(db, event.id)

    # 4. Satellite Remote Sensing
    sat_provider = Sentinel2Provider()
    sat_evidence = sat_provider.search_imagery(
        latitude=event.latitude,
        longitude=event.longitude,
        target_time=event.detected_at
    )

    # 5. Multimodal Features
    spatial_context = {
        "nearest_facility": nearest_facility,
        "distance_meters": min_distance,
        "nearby_facilities": nearby_facilities,
        "land_cover": land_cover
    }
    features = FeatureEngineer.extract_features(event, spatial_context=spatial_context, temporal_data=temporal_data)

    # 6. ML Inference
    try:
        ml_classifier = MLClassifier()
        classification_res = ml_classifier.classify(features)
        is_fallback = False
    except Exception as e:
        logger.warning(f"MLClassifier unavailable for event {event_id}: {e}. Using prototype fallback.")
        proto = PrototypeClassifier()
        classification_res = proto.classify(features)
        is_fallback = True
        classification_res["model_type"] = "prototype_heuristic"
        classification_res["model_version"] = "phase3-v1.0"

    priority_score, priority_level = PriorityEngine.evaluate_priority(
        features=features,
        classification=classification_res["classification"]
    )
    classification_res["priority_score"] = priority_score
    classification_res["priority_level"] = priority_level
    classification_res["fallback"] = is_fallback

    # 7. Historical detections in cluster
    historical_events = _query_historical_cluster(db, event.longitude, event.latitude, 1500.0, target_id=event.id)

    # 8. Analyst Reviews
    reviews_db = ReviewService.get_reviews(db, event.id)
    reviews = [
        {
            "id": r.id,
            "analyst_id": r.analyst_id,
            "decision": r.decision,
            "comment": r.comment,
            "previous_classification": r.previous_classification,
            "final_classification": r.final_classification,
            "reviewed_by": r.reviewed_by,
            "created_at": r.created_at.isoformat() if r.created_at else None
        }
        for r in reviews_db
    ]

    # 9. Risk Assessment & Alerts Evaluation
    try:
        from app.services.risk.engine import RiskEngine
        from app.services.alert.engine import AlertEngine
        risk_data = RiskEngine.evaluate_risk(
            features={"model_probability": classification_res.get("model_probability", 0.8), "frp": event.frp},
            classification=classification_res["classification"],
            spatial_context=spatial_context,
            temporal_data=temporal_data,
            satellite_data=sat_evidence
        )
        active_alerts = AlertEngine.evaluate_event_alerts(
            db=db,
            event=event,
            risk_data=risk_data,
            classification=classification_res["classification"],
            spatial_context=spatial_context,
            temporal_data=temporal_data,
            satellite_data=sat_evidence
        )
    except Exception as e:
        logger.warning(f"Error evaluating risk/alerts for event {event.id}: {e}")
        risk_data = {
            "risk_score": 50.0,
            "risk_level": "MODERATE",
            "risk_model_version": "risk-v1",
            "breakdown": {"factors": [], "total_score": 50.0, "risk_level": "MODERATE", "model_version": "risk-v1"}
        }
        active_alerts = []

    # 10. Provenance
    lc_meta = land_cover or {}
    sat_meta = sat_evidence or {}
    provenance = {
        "thermal_source": "NASA FIRMS NRT (VIIRS/MODIS)",
        "infrastructure_source": "OpenStreetMap (OSM) Infrastructure DB",
        "land_cover_source": f"ESA WorldCover 10m {lc_meta.get('dataset_version', 'v200')}",
        "satellite_source": f"Copernicus Sentinel-2 MSI ({sat_meta.get('scene_id', 'L2A')})",
        "ml_model_version": classification_res.get("model_version", "xgb-v1"),
        "risk_model_version": risk_data.get("risk_model_version", "risk-v1"),
        "feature_schema_version": "v2.0",
        "analysis_timestamp": datetime.now(timezone.utc).isoformat()
    }

    return {
        "event": {
            "id": event.id,
            "event_code": f"INF-2026-{event.id:06d}",
            "detected_at": event.detected_at.isoformat() if event.detected_at else None,
            "latitude": event.latitude,
            "longitude": event.longitude,
            "confidence": event.confidence,
            "frp": event.frp,
            "brightness_temperature": event.brightness_temperature,
            "satellite": event.satellite,
            "instrument": event.instrument,
            "status": getattr(event, "status", "NEW") or "NEW",
            "source": event.source
        },
        "classification": classification_res,
        "temporal_analysis": temporal_data,
        "nearby_facilities": nearby_facilities,
        "nearest_facility": nearest_facility,
        "satellite_evidence": sat_evidence,
        "land_cover": land_cover,
        "historical_events": historical_events,
        "reviews": reviews,
        "risk_assessment": risk_data,
        "active_alerts_count": len(active_alerts),
        "provenance": provenance
    }

@router.get("/{event_id}/timeline")
def get_event_timeline(event_id: int, db: Session = Depends(get_db)):
    """
    Returns the chronological detection sequence for this thermal event's cluster for bottom timeline playback.
    """
    event = db.query(ThermalEvent).filter(ThermalEvent.id == event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    historical = _query_historical_cluster(db, event.longitude, event.latitude, 1500.0, target_id=event.id)
    
    analyzer = TemporalAnalyzer()
    temp = analyzer.analyze_event(db, event.id)
    cluster_id = temp.get("cluster_id", f"cluster_{round(event.latitude, 2)}_{round(event.longitude, 2)}")

    return {
        "event_id": event.id,
        "cluster_id": cluster_id,
        "total_detections": len(historical),
        "timeline": historical
    }

@router.get("/{event_id}/evidence")
def get_event_evidence(event_id: int, db: Session = Depends(get_db)):
    """
    Consolidated model and remote-sensing evidence factors.
    """
    investigation = get_event_investigation(event_id, db)
    return {
        "event_id": event_id,
        "classification": investigation["classification"]["classification"],
        "model_version": investigation["classification"].get("model_version"),
        "model_probability": investigation["classification"].get("confidence_score") or investigation["classification"].get("model_probability"),
        "evidence_factors": investigation["classification"].get("evidence_factors", []),
        "explanation": investigation["classification"].get("explanation", []),
        "feature_attributions": investigation["classification"].get("feature_attributions", []),
        "satellite_evidence": investigation["satellite_evidence"],
        "land_cover": investigation["land_cover"],
        "temporal_analysis": investigation["temporal_analysis"],
        "provenance": investigation["provenance"]
    }

@router.get("/{event_id}/nearby-facilities")
def get_event_nearby_facilities(
    event_id: int,
    radius_km: float = Query(5.0, gt=0),
    db: Session = Depends(get_db)
):
    """
    Returns nearby infrastructure facilities sorted by distance.
    """
    event = db.query(ThermalEvent).filter(ThermalEvent.id == event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    facilities = _query_nearby_facilities(db, event.longitude, event.latitude, radius_km * 1000.0)
    return {
        "event_id": event.id,
        "latitude": event.latitude,
        "longitude": event.longitude,
        "search_radius_km": radius_km,
        "facilities_count": len(facilities),
        "facilities": facilities
    }

@router.patch("/{event_id}/status")
def update_event_status(event_id: int, body: EventStatusUpdate, db: Session = Depends(get_db)):
    """
    Transitions the lifecycle state of a thermal event with state machine validation:
    NEW -> INVESTIGATING -> CONFIRMED / REJECTED -> CLOSED.
    """
    try:
        new_status = ReviewService.transition_event_status(db, event_id, body.status, body.reason)
        return {
            "event_id": event_id,
            "status": new_status,
            "reason": body.reason,
            "updated_at": datetime.now(timezone.utc).isoformat()
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/{event_id}/reviews", response_model=List[AnalystReviewOut])
def get_event_reviews(event_id: int, db: Session = Depends(get_db)):
    """
    Returns all analyst reviews for an event.
    """
    event = db.query(ThermalEvent).filter(ThermalEvent.id == event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    return ReviewService.get_reviews(db, event_id)

@router.post("/{event_id}/reviews", response_model=AnalystReviewOut)
def submit_event_review(event_id: int, review_in: AnalystReviewCreate, db: Session = Depends(get_db)):
    """
    Submits an analyst review without overwriting original AI classifications.
    """
    try:
        return ReviewService.submit_review(db, event_id, review_in)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.get("/{event_id}/satellite")
def get_event_satellite_evidence(event_id: int, db: Session = Depends(get_db)):
    """
    Retrieves Sentinel-2 MSI satellite imagery metadata, surface reflectance bands,
    and derived spectral indices (NDVI, NBR, NDWI, SWIR ratio).
    """
    event = db.query(ThermalEvent).filter(ThermalEvent.id == event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    provider = Sentinel2Provider()
    evidence = provider.search_imagery(
        latitude=event.latitude,
        longitude=event.longitude,
        target_time=event.detected_at
    )
    return {
        "event_id": event.id,
        "latitude": event.latitude,
        "longitude": event.longitude,
        "detected_at": event.detected_at.isoformat() if event.detected_at else None,
        "satellite_evidence": evidence
    }

@router.get("/{event_id}/landcover")
def get_event_landcover(event_id: int, db: Session = Depends(get_db)):
    """
    Retrieves ESA WorldCover 10m land cover classification, tile metadata, and category.
    """
    event = db.query(ThermalEvent).filter(ThermalEvent.id == event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    provider = LandCoverProvider()
    land_cover = provider.get_land_cover(event.latitude, event.longitude)
    return {
        "event_id": event.id,
        "latitude": event.latitude,
        "longitude": event.longitude,
        "land_cover": land_cover
    }
