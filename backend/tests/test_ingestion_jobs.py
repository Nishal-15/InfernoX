import pytest
from datetime import datetime, timezone
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.models.ingestion_job import IngestionJob
from app.services.firms.ingestion import FirmsIngestionService

@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")
    IngestionJob.__table__.create(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()

def test_ingestion_job_persistence(db_session):
    job = IngestionJob(
        source="TEST_SOURCE",
        status="RUNNING",
        started_at=datetime.now(timezone.utc)
    )
    db_session.add(job)
    db_session.commit()
    db_session.refresh(job)
    
    assert job.id is not None
    assert job.status == "RUNNING"
    assert job.records_received == 0

    # Simulate completion
    job.status = "COMPLETED"
    job.records_received = 100
    job.records_inserted = 95
    job.records_skipped = 5
    job.completed_at = datetime.now(timezone.utc)
    db_session.commit()

    saved_job = db_session.query(IngestionJob).filter(IngestionJob.id == job.id).first()
    assert saved_job.status == "COMPLETED"
    assert saved_job.records_inserted == 95

@pytest.mark.asyncio
async def test_firms_ingestion_missing_key_behavior(db_session):
    service = FirmsIngestionService()
    service.client.api_key = "" # Ensure no key
    
    # Without demo mode -> should fail safely with clear configuration error
    res = await service.ingest_data(db_session, use_demo_if_missing_key=False)
    assert res["status"] == "FAILED"
    assert "FIRMS_MAP_KEY is not configured" in res["error"]
