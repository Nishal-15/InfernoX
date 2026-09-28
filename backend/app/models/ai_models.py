from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, JSON, Text
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from app.db.database import Base

class EventAssessment(Base):
    __tablename__ = "event_assessments"

    id = Column(Integer, primary_key=True, index=True)
    event_id = Column(Integer, ForeignKey("thermal_events.id"), index=True, nullable=False)
    
    classification = Column(String, nullable=False)
    confidence_score = Column(Float, nullable=False)
    confidence_type = Column(String, default="heuristic", nullable=False)
    priority_score = Column(Float, nullable=False)
    priority_level = Column(String, nullable=False) # LOW, MEDIUM, HIGH, CRITICAL
    
    explanation = Column(JSON, nullable=True) # Legacy explanation list
    evidence_factors = Column(JSON, nullable=True) # Phase 3 concrete feature evidence list
    
    model_type = Column(String, default="rule_based_prototype", nullable=False)
    model_version = Column(String, default="phase3-v1.0", nullable=False)
    feature_schema_version = Column(String, default="v1.1", nullable=False)
    
    # Phase 10: Model inference reproducibility and telemetry (Section 11)
    prediction_timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=True)
    feature_snapshot = Column(JSON, nullable=True)

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

class AnalystReview(Base):
    __tablename__ = "analyst_reviews"

    id = Column(Integer, primary_key=True, index=True)
    event_id = Column(Integer, ForeignKey("thermal_events.id"), index=True, nullable=False)
    assessment_id = Column(Integer, ForeignKey("event_assessments.id"), nullable=True)
    
    analyst_id = Column(String, default="analyst-1", nullable=False)
    decision = Column(String, nullable=True) # CONFIRM, REJECT, NEEDS_INVESTIGATION
    action = Column(String, nullable=True) # Backwards compatibility alias for decision
    
    comment = Column(Text, nullable=True)
    note = Column(Text, nullable=True) # Backwards compatibility alias for comment
    
    previous_classification = Column(String, nullable=True)
    final_classification = Column(String, nullable=True)
    reviewed_by = Column(String, default="analyst")
    
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)
