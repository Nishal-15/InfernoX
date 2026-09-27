from pydantic import BaseModel, ConfigDict
from typing import Optional, Dict, Any, List
from datetime import datetime

class AnalystReviewCreate(BaseModel):
    decision: Optional[str] = None # CONFIRM, REJECT, NEEDS_INVESTIGATION
    action: Optional[str] = None # Backwards compatibility alias
    comment: Optional[str] = None
    note: Optional[str] = None # Backwards compatibility alias
    final_classification: Optional[str] = None
    analyst_id: Optional[str] = "analyst-1"

class AnalystReviewOut(BaseModel):
    id: int
    event_id: int
    assessment_id: Optional[int] = None
    analyst_id: str
    decision: str
    comment: Optional[str] = None
    previous_classification: Optional[str] = None
    final_classification: Optional[str] = None
    reviewed_by: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

class TrainingDataRecord(BaseModel):
    event_id: int
    features: Dict[str, Any]
    label: str
    label_source: str = "ANALYST" # ANALYST, AUTHORITATIVE_DATASET, FLARE_DATABASE, EXPERT_ANNOTATION
    label_confidence: float = 1.0
    review_status: str = "CONFIRMED"
    reviewed_by: str = "analyst"
    reviewed_at: Optional[datetime] = None
    cluster_id: Optional[str] = None
    facility_id: Optional[str] = None
    dataset_version: str = "v1.0"
    created_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)
