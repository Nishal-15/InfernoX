import logging
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.api.deps import get_db
from app.models.ai_models import EventAssessment, AnalystReview
from app.models.thermal_event import ThermalEvent
from app.schemas.review import AnalystReviewCreate, AnalystReviewOut, TrainingDataRecord
from app.schemas.classification import ClassificationResponse
from app.services.temporal.analyzer import TemporalAnalyzer
from app.services.features.engineer import FeatureEngineer
from app.services.classification.classifier import PrototypeClassifier
from app.services.priority.engine import PriorityEngine
from app.services.review.service import ReviewService
from app.api.v1.endpoints.events import get_event_context

logger = logging.getLogger(__name__)
router = APIRouter()

class AnalystReviewRequest(BaseModel):
    action: Optional[str] = None # CONFIRM, REJECT, NEEDS_INVESTIGATION
    decision: Optional[str] = None
    note: Optional[str] = None
    comment: Optional[str] = None
    analyst_id: Optional[str] = "analyst-1"

class BatchInferenceRequest(BaseModel):
    event_ids: List[int]

@router.post("/predict/{event_id}")
def predict_event(event_id: int, db: Session = Depends(get_db)):
    """
    Runs Phase 3 prototype classification pipeline on a single thermal event.
    Explicitly labeled as rule_based_prototype with heuristic confidence.
    """
    event = db.query(ThermalEvent).filter(ThermalEvent.id == event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
        
    context = get_event_context(event_id, db)
    analyzer = TemporalAnalyzer()
    temporal_data = analyzer.analyze_event(db, event_id)
    
    features = FeatureEngineer.extract_features(event, spatial_context=context, temporal_data=temporal_data)
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
        feature_schema_version="v1.1",
        prediction_timestamp=datetime.now(timezone.utc),
        feature_snapshot=features.to_ml_dict()
    )
    
    db.add(assessment)
    db.commit()
    db.refresh(assessment)
    
    return assessment

@router.post("/predict/batch")
def predict_batch(request: BatchInferenceRequest, db: Session = Depends(get_db)):
    """
    Runs batch inference on a list of thermal event IDs.
    """
    if len(request.event_ids) > 100:
        raise HTTPException(status_code=400, detail="Batch limit is 100")
        
    results = []
    analyzer = TemporalAnalyzer()
    classifier = PrototypeClassifier()
    
    for event_id in request.event_ids:
        event = db.query(ThermalEvent).filter(ThermalEvent.id == event_id).first()
        if not event:
            continue
            
        context = get_event_context(event_id, db)
        temporal_data = analyzer.analyze_event(db, event_id)
        features = FeatureEngineer.extract_features(event, spatial_context=context, temporal_data=temporal_data)
        
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
            feature_schema_version="v1.1",
            prediction_timestamp=datetime.now(timezone.utc),
            feature_snapshot=features.to_ml_dict()
        )
        db.add(assessment)
        results.append(assessment)
        
    db.commit()
    return {"processed": len(results)}

@router.get("/events/{event_id}/assessment")
def get_assessment(event_id: int, db: Session = Depends(get_db)):
    """
    Gets the latest assessment for an event.
    """
    assessment = (
        db.query(EventAssessment)
        .filter(EventAssessment.event_id == event_id)
        .order_by(EventAssessment.created_at.desc())
        .first()
    )
    if not assessment:
        raise HTTPException(status_code=404, detail="No assessment found for this event")
    return assessment

@router.post("/events/{event_id}/review")
def submit_review(event_id: int, request: AnalystReviewRequest, db: Session = Depends(get_db)):
    """
    Submits analyst review feedback for an event (Human-in-the-loop).
    Does NOT overwrite original AI assessment.
    """
    decision = request.decision or request.action or "CONFIRM"
    comment = request.comment or request.note or ""
    
    review_in = AnalystReviewCreate(
        decision=decision,
        comment=comment,
        analyst_id=request.analyst_id or "analyst-1"
    )
    
    try:
        return ReviewService.submit_review(db, event_id, review_in)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.get("/training-data/export", response_model=List[TrainingDataRecord])
def export_training_data(db: Session = Depends(get_db)):
    """
    Exports verified, analyst-confirmed thermal events as labelled training data
    for Phase 4 machine learning models.
    """
    return ReviewService.export_training_data(db)
