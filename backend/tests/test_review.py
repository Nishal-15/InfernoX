import pytest
from datetime import datetime, timezone
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.db.database import Base
from app.models.ai_models import EventAssessment, AnalystReview
from app.models.ingestion_job import IngestionJob
from app.schemas.review import AnalystReviewCreate
from app.services.review.service import ReviewService

@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")
    # Create tables for models that do not require PostGIS extension
    EventAssessment.__table__.create(bind=engine)
    AnalystReview.__table__.create(bind=engine)
    IngestionJob.__table__.create(bind=engine)
    
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()

def test_analyst_review_workflow(db_session, monkeypatch):
    # Mock event query to return dummy object
    class DummyEvent:
        id = 101
        latitude = 22.0
        longitude = 70.0
        detected_at = datetime.now(timezone.utc)
        satellite = "VIIRS"
        frp = 100.0


    # Insert an initial AI assessment
    assessment = EventAssessment(
        event_id=101,
        classification="Possible Industrial Fire",
        confidence_score=85.0,
        priority_score=75.0,
        priority_level="HIGH",
        model_type="rule_based_prototype",
        model_version="phase3-v1.0",
        feature_schema_version="v1.1",
        evidence_factors=["FRP is 3x higher than baseline"]
    )
    db_session.add(assessment)
    db_session.commit()

    # Create dummy query for ThermalEvent
    from app.models.thermal_event import ThermalEvent
    original_query = db_session.query

    def custom_query(model):
        if model == ThermalEvent:
            class DummyQuery:
                def filter(self, *args, **kwargs):
                    return self
                def first(self):
                    return DummyEvent()
            return DummyQuery()
        return original_query(model)

    monkeypatch.setattr(db_session, "query", custom_query)

    # 1. Analyst confirms
    review_in = AnalystReviewCreate(
        decision="CONFIRM",
        comment="Confirmed flare abnormal venting",
        analyst_id="lead-analyst"
    )
    rev = ReviewService.submit_review(db_session, 101, review_in)
    assert rev.id is not None
    assert rev.decision == "CONFIRM"
    assert rev.previous_classification == "Possible Industrial Fire"
    assert rev.final_classification == "Possible Industrial Fire"

    # Original assessment is unchanged
    assess_check = db_session.query(EventAssessment).filter(EventAssessment.event_id == 101).first()
    assert assess_check.classification == "Possible Industrial Fire"

    # 2. Get reviews
    reviews = ReviewService.get_reviews(db_session, 101)
    assert len(reviews) == 1
    assert reviews[0].analyst_id == "lead-analyst"
