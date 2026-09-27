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

def test_api_list_models(client_with_db):
    response = client_with_db.get("/api/v1/ml/models")
    assert response.status_code == 200
    data = response.json()
    assert "models" in data
    assert "active_version" in data

def test_api_current_model(client_with_db):
    response = client_with_db.get("/api/v1/ml/models/current")
    assert response.status_code == 200
    data = response.json()
    assert "model_version" in data
    assert "model_type" in data
    assert "metrics" in data
    assert "classes" in data
    assert "feature_importances" in data

def test_api_dataset_status(client_with_db):
    response = client_with_db.get("/api/v1/ml/dataset/status")
    assert response.status_code == 200
    data = response.json()
    assert "dataset_version" in data
    assert "total_records" in data
    assert "class_distribution" in data
    assert "leakage_prevention_strategy" in data
    assert data["total_records"] > 0
