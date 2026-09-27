import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.api.deps import get_db
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool
from sqlalchemy.orm import sessionmaker
from app.models.ai_models import EventAssessment, AnalystReview
from app.models.ingestion_job import IngestionJob

@pytest.fixture
def client_with_db():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool
    )
    EventAssessment.__table__.create(bind=engine)
    AnalystReview.__table__.create(bind=engine)
    IngestionJob.__table__.create(bind=engine)
    
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = TestingSessionLocal()

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.clear()
    session.close()

def test_api_health(client_with_db):
    response = client_with_db.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["service"] == "thermal-intelligence-api"

def test_api_ingestion_status_empty(client_with_db):
    response = client_with_db.get("/api/v1/ingestion/status")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert data["records_fetched"] == 0

def test_api_training_data_export(client_with_db):
    response = client_with_db.get("/api/v1/ai/training-data/export")
    assert response.status_code == 200
    assert isinstance(response.json(), list)
