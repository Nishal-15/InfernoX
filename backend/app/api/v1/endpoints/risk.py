from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.models.thermal_event import ThermalEvent
from app.models.risk_alert import RiskAssessment
from app.schemas.risk_alert import RiskAssessmentResponse
from app.services.risk.engine import RiskEngine
from app.services.temporal.analyzer import TemporalAnalyzer
from app.services.landcover.provider import LandCoverProvider
from app.services.satellite.provider import Sentinel2Provider
from app.services.features.engineer import FeatureEngineer
from app.services.ml.classifier import MLClassifier
from app.services.classification.classifier import PrototypeClassifier
from app.api.v1.endpoints.events import _query_nearby_facilities

router = APIRouter()


@router.get("/events/{event_id}/risk", response_model=RiskAssessmentResponse)
def get_event_risk(event_id: int, db: Session = Depends(get_db)):
    """
    Retrieves latest risk assessment or calculates real-time risk score for an event.
    """
    event = db.query(ThermalEvent).filter(ThermalEvent.id == event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail=f"Thermal event {event_id} not found")

    # Check for recent risk assessment
    existing = db.query(RiskAssessment).filter(
        RiskAssessment.event_id == event_id
    ).order_by(RiskAssessment.calculated_at.desc()).first()

    if existing:
        return RiskAssessmentResponse(
            id=existing.id,
            event_id=existing.event_id,
            risk_score=existing.risk_score,
            risk_level=existing.risk_level,
            risk_model_version=existing.risk_model_version,
            breakdown=existing.breakdown_json,
            input_snapshot=existing.input_snapshot_json,
            calculated_at=existing.calculated_at
        )

    # Calculate real-time risk assessment
    analyzer = TemporalAnalyzer()
    temp_data = analyzer.analyze_event(db, event.id)
    facs = _query_nearby_facilities(db, event.longitude, event.latitude, 5000.0)
    nearest = facs[0] if facs else None
    spatial_ctx = {
        "nearest_facility": nearest,
        "distance_meters": nearest["distance_meters"] if nearest else None
    }
    sat_data = Sentinel2Provider().search_imagery(event.latitude, event.longitude, event.detected_at)
    lc_data = LandCoverProvider().get_land_cover(event.latitude, event.longitude)

    features = FeatureEngineer.extract_features(
        event,
        spatial_context={"nearest_facility": nearest, "distance_meters": nearest["distance_meters"] if nearest else None, "land_cover": lc_data},
        temporal_data=temp_data
    )

    try:
        clf_res = MLClassifier().classify(features)
        classification = clf_res["classification"]
    except Exception:
        clf_res = PrototypeClassifier().classify(features)
        classification = clf_res["classification"]

    record = RiskEngine.record_risk_assessment(
        db=db,
        event_id=event.id,
        features={"model_probability": clf_res.get("model_probability", 0.8), "frp": event.frp},
        classification=classification,
        spatial_context=spatial_ctx,
        temporal_data=temp_data,
        satellite_data=sat_data
    )

    return RiskAssessmentResponse(
        id=record.id,
        event_id=record.event_id,
        risk_score=record.risk_score,
        risk_level=record.risk_level,
        risk_model_version=record.risk_model_version,
        breakdown=record.breakdown_json,
        input_snapshot=record.input_snapshot_json,
        calculated_at=record.calculated_at
    )


@router.get("/events/{event_id}/risk/history", response_model=List[RiskAssessmentResponse])
def get_event_risk_history(event_id: int, db: Session = Depends(get_db)):
    """
    Returns historical sequence of risk assessments for an event to monitor escalation.
    """
    event = db.query(ThermalEvent).filter(ThermalEvent.id == event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail=f"Thermal event {event_id} not found")

    records = db.query(RiskAssessment).filter(
        RiskAssessment.event_id == event_id
    ).order_by(RiskAssessment.calculated_at.desc()).all()

    return [
        RiskAssessmentResponse(
            id=r.id,
            event_id=r.event_id,
            risk_score=r.risk_score,
            risk_level=r.risk_level,
            risk_model_version=r.risk_model_version,
            breakdown=r.breakdown_json,
            input_snapshot=r.input_snapshot_json,
            calculated_at=r.calculated_at
        ) for r in records
    ]
