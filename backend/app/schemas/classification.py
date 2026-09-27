from pydantic import BaseModel, ConfigDict
from typing import List, Optional
from datetime import datetime
from app.schemas.features import ThermalFeatures, FeatureAttribution

class ClassificationResponse(BaseModel):
    event_id: int
    classification: str
    confidence_score: float # 0 - 100
    confidence_type: str = "heuristic" # Explicitly indicates prototype heuristic vs statistical probability
    priority_score: float # 0 - 100
    priority_level: str # LOW, MEDIUM, HIGH, CRITICAL
    model_type: str = "rule_based_prototype"
    model_version: str = "phase3-v1.0"
    evidence_factors: List[str] # Human-readable factual feature evidence
    explanation: Optional[List[dict]] = None # Backwards compatibility with Phase 2 frontend
    features: ThermalFeatures
    created_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)
