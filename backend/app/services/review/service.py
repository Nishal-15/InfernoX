import logging
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from app.models.thermal_event import ThermalEvent
from app.models.ai_models import EventAssessment, AnalystReview
from app.schemas.review import AnalystReviewCreate, AnalystReviewOut, TrainingDataRecord
from app.services.features.engineer import FeatureEngineer
from app.services.temporal.analyzer import TemporalAnalyzer

logger = logging.getLogger(__name__)

class ReviewService:
    """
    Human-in-the-Loop Analyst Review Service.
    Manages analyst feedback without overwriting original AI assessments,
    and curates analyst-confirmed events into verified training datasets.
    """

    VALID_STATUS_TRANSITIONS = {
        "NEW": {"INVESTIGATING"},
        "INVESTIGATING": {"CONFIRMED", "REJECTED", "CLOSED", "NEW"},
        "CONFIRMED": {"CLOSED", "INVESTIGATING"},
        "REJECTED": {"CLOSED", "INVESTIGATING"},
        "CLOSED": {"INVESTIGATING"}
    }

    @classmethod
    def transition_event_status(cls, db: Session, event_id: int, target_status: str, reason: Optional[str] = None) -> str:
        event = db.query(ThermalEvent).filter(ThermalEvent.id == event_id).first()
        if not event:
            raise ValueError(f"Event {event_id} not found")

        current_status = getattr(event, "status", None) or "NEW"
        target = target_status.upper()
        if target == current_status:
            return current_status

        allowed = cls.VALID_STATUS_TRANSITIONS.get(current_status, set())
        if target not in allowed:
            raise ValueError(f"Invalid status transition from {current_status} to {target}. Allowed transitions: {sorted(list(allowed))}")

        event.status = target
        db.commit()
        db.refresh(event)
        logger.info(f"Event {event_id} status transitioned from {current_status} to {target} (reason: {reason})")
        return target

    @classmethod
    def submit_review(cls, db: Session, event_id: int, review_in: AnalystReviewCreate) -> AnalystReview:
        event = db.query(ThermalEvent).filter(ThermalEvent.id == event_id).first()
        if not event:
            raise ValueError(f"Event {event_id} not found")

        # Get latest AI assessment for this event
        latest_assessment = (
            db.query(EventAssessment)
            .filter(EventAssessment.event_id == event_id)
            .order_by(EventAssessment.created_at.desc())
            .first()
        )

        decision = (review_in.decision or review_in.action or "CONFIRM").upper()
        comment = review_in.comment or review_in.note or ""
        prev_classification = latest_assessment.classification if latest_assessment else "UNKNOWN"
        final_classification = review_in.final_classification or prev_classification

        review = AnalystReview(
            event_id=event_id,
            assessment_id=latest_assessment.id if latest_assessment else None,
            analyst_id=review_in.analyst_id or "analyst-1",
            decision=decision,
            action=decision, # backwards compatibility
            comment=comment,
            note=comment, # backwards compatibility
            previous_classification=prev_classification,
            final_classification=final_classification,
            reviewed_by=review_in.analyst_id or "analyst-1",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )

        # Update event status according to analyst review decision
        current_status = getattr(event, "status", None) or "NEW"
        if decision == "CONFIRM":
            if current_status in ("NEW", "INVESTIGATING"):
                event.status = "CONFIRMED"
        elif decision == "REJECT":
            if current_status in ("NEW", "INVESTIGATING"):
                event.status = "REJECTED"
        elif decision in ("NEEDS_INVESTIGATION", "INVESTIGATING"):
            if current_status in ("NEW", "CLOSED", "CONFIRMED", "REJECTED"):
                event.status = "INVESTIGATING"

        db.add(review)
        db.commit()
        db.refresh(review)
        return review

    @staticmethod
    def get_reviews(db: Session, event_id: int) -> List[AnalystReview]:
        return (
            db.query(AnalystReview)
            .filter(AnalystReview.event_id == event_id)
            .order_by(AnalystReview.created_at.desc())
            .all()
        )

    @staticmethod
    def export_training_data(db: Session) -> List[TrainingDataRecord]:
        """
        Exports all analyst-confirmed events as labelled training data for Phase 4 ML models.
        Only CONFIRM reviews with verified labels are included.
        """
        confirmed_reviews = (
            db.query(AnalystReview)
            .filter(AnalystReview.decision == "CONFIRM")
            .order_by(AnalystReview.created_at.desc())
            .all()
        )

        records: List[TrainingDataRecord] = []
        analyzer = TemporalAnalyzer()

        for rev in confirmed_reviews:
            event = db.query(ThermalEvent).filter(ThermalEvent.id == rev.event_id).first()
            if not event:
                continue

            # Compute features
            try:
                temporal_data = analyzer.analyze_event(db, event.id)
            except Exception:
                temporal_data = {}

            features = FeatureEngineer.extract_features(event, temporal_data=temporal_data)

            records.append(
                TrainingDataRecord(
                    event_id=event.id,
                    features=features.model_dump(),
                    label=rev.final_classification or rev.previous_classification or "UNKNOWN",
                    review_status="CONFIRMED",
                    reviewed_by=rev.reviewed_by or rev.analyst_id,
                    reviewed_at=rev.created_at
                )
            )

        return records
