import os
import json
import logging
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.api.deps import get_db
from app.core.config import settings
from app.models.thermal_event import ThermalEvent
from app.models.ai_models import EventAssessment
from app.services.features.engineer import FeatureEngineer
from app.services.landcover.provider import LandCoverProvider
from app.services.satellite.provider import Sentinel2Provider
from app.services.temporal.analyzer import TemporalAnalyzer
from app.services.priority.engine import PriorityEngine
from app.services.ml.classifier import MLClassifier
from app.services.ml.trainer import MLTrainer
from app.services.ml.dataset import DatasetBuilder

logger = logging.getLogger(__name__)

router = APIRouter()

@router.get("/models")
def list_models():
    """
    Lists all trained ML model versions present in the model registry.
    """
    registry_path = settings.MODEL_REGISTRY_PATH
    if not os.path.exists(registry_path):
        return {"models": [], "active_version": settings.ACTIVE_MODEL_VERSION}

    models: List[Dict[str, Any]] = []
    for entry in os.listdir(registry_path):
        entry_path = os.path.join(registry_path, entry)
        if os.path.isdir(entry_path):
            meta_file = os.path.join(entry_path, "metadata.json")
            if os.path.exists(meta_file):
                try:
                    with open(meta_file, "r", encoding="utf-8") as f:
                        meta = json.load(f)
                        models.append({
                            "model_version": meta.get("model_version", entry),
                            "model_type": meta.get("model_type", "xgboost"),
                            "training_date": meta.get("training_date"),
                            "accuracy": meta.get("metrics", {}).get("accuracy"),
                            "macro_f1": meta.get("metrics", {}).get("macro_f1"),
                            "classes": meta.get("classes", [])
                        })
                except Exception as e:
                    logger.error(f"Error reading metadata from {meta_file}: {e}")

    return {
        "models": models,
        "active_version": settings.ACTIVE_MODEL_VERSION,
        "registry_path": registry_path
    }

@router.get("/models/current")
def get_current_model():
    """
    Returns the metadata, evaluation metrics, and feature importances
    for the currently active production ML model.
    """
    active_version = settings.ACTIVE_MODEL_VERSION
    version_dir = os.path.join(settings.MODEL_REGISTRY_PATH, active_version)
    metadata_path = os.path.join(version_dir, "metadata.json")

    if not os.path.exists(metadata_path):
        raise HTTPException(
            status_code=404,
            detail=f"Active model '{active_version}' not found in registry. Please run POST /api/v1/ml/train first."
        )

    try:
        with open(metadata_path, "r", encoding="utf-8") as f:
            metadata = json.load(f)
        return metadata
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to read model metadata: {e}")

@router.get("/dataset/status")
def get_dataset_status(db: Session = Depends(get_db)):
    """
    Returns summary statistics, class distributions, and data leakage prevention strategy
    for the current training dataset.
    """
    return DatasetBuilder.get_dataset_status(db=db)

@router.post("/train")
def train_model(
    model_version: Optional[str] = None,
    dataset_version: str = "v1.0",
    test_size: float = Query(0.25, gt=0.0, lt=0.5),
    db: Session = Depends(get_db)
):
    """
    Triggers the end-to-end Machine Learning training and evaluation pipeline.
    Uses GroupShuffleSplit on spatial cluster/facility to prevent temporal and spatial data leakage.
    Saves the serialized model artifact and evaluation metadata to the model registry.
    """
    target_version = model_version or settings.ACTIVE_MODEL_VERSION
    trainer = MLTrainer(model_version=target_version)

    try:
        # Build dataset combining analyst-confirmed DB records and authoritative reference points
        records = DatasetBuilder.build_dataset(db=db, version=dataset_version)
        result = trainer.train_and_evaluate(records=records, test_size=test_size, dataset_version=dataset_version)
        return result
    except Exception as e:
        logger.error(f"Model training failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Training pipeline error: {str(e)}")

@router.post("/predict/{event_id}")
def predict_event(event_id: int, db: Session = Depends(get_db)):
    """
    Runs production Machine Learning inference on a thermal event.
    Enriches with OSM facilities, ESA WorldCover 10m, and Sentinel-2 satellite data,
    executes the XGBoost classifier, assesses operational priority, and records provenance.
    """
    event = db.query(ThermalEvent).filter(ThermalEvent.id == event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    # 1. Temporal analysis
    analyzer = TemporalAnalyzer()
    try:
        temporal_data = analyzer.analyze_event(db, event_id)
    except Exception:
        temporal_data = {}

    # 2. Land Cover (ESA WorldCover 10m)
    lc_provider = LandCoverProvider()
    land_cover = lc_provider.get_land_cover(event.latitude, event.longitude)

    # 3. Satellite Evidence (Sentinel-2)
    sat_provider = Sentinel2Provider()
    satellite_data = sat_provider.search_imagery(
        latitude=event.latitude,
        longitude=event.longitude,
        target_time=event.detected_at
    )

    # 4. Feature Extraction
    from app.api.v1.endpoints.events import get_event_context
    spatial_context = get_event_context(event_id, db)
    spatial_context["land_cover"] = land_cover

    features = FeatureEngineer.extract_features(
        event=event,
        spatial_context=spatial_context,
        temporal_data=temporal_data,
        satellite_data=satellite_data
    )

    # 5. ML Inference
    classifier = MLClassifier()
    prediction = classifier.classify(features)

    # 6. Operational Priority
    priority_score, priority_level = PriorityEngine.evaluate_priority(
        features=features,
        classification=prediction["classification"]
    )

    # 7. Persist Assessment
    assessment = EventAssessment(
        event_id=event.id,
        classification=prediction["classification"],
        confidence_score=prediction["confidence_score"],
        confidence_type=prediction["confidence_type"],
        priority_score=priority_score,
        priority_level=priority_level,
        evidence_factors=prediction.get("evidence_factors", []),
        explanation=[{"feature": a["feature"], "impact": a["importance_weight"], "text": a["description"]} for a in prediction.get("top_contributing_features", [])],
        model_type=prediction.get("model_type", "xgboost"),
        model_version=prediction.get("model_version", settings.ACTIVE_MODEL_VERSION),
        feature_schema_version=prediction.get("feature_schema_version", "v2.0")
    )
    db.add(assessment)
    db.commit()
    db.refresh(assessment)

    # Provenance tracking
    provenance = {
        "firms_source": event.source,
        "osm_source": "OpenStreetMap Overpass API",
        "worldcover_version": land_cover.get("dataset_version") if land_cover else "None",
        "sentinel_scene_id": satellite_data.get("scene_id") if satellite_data else None,
        "ml_model_version": prediction.get("model_version"),
        "feature_schema_version": prediction.get("feature_schema_version", "v2.0"),
        "prediction_timestamp": assessment.created_at.isoformat()
    }

    return {
        "event_id": event.id,
        "classification": prediction["classification"],
        "model_probability": prediction.get("model_probability"),
        "confidence_score": prediction["confidence_score"],
        "confidence_type": prediction["confidence_type"],
        "priority_score": priority_score,
        "priority_level": priority_level,
        "model_type": prediction.get("model_type"),
        "model_version": prediction.get("model_version"),
        "probabilities": prediction.get("probabilities", {}),
        "top_contributing_features": prediction.get("top_contributing_features", []),
        "evidence_factors": prediction.get("evidence_factors", []),
        "provenance": provenance,
        "features": features.model_dump(),
        "is_fallback": prediction.get("is_fallback", False),
        "created_at": assessment.created_at
    }
