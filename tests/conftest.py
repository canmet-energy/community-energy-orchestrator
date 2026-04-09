import pytest
from app.main import app
from fastapi.testclient import TestClient


@pytest.fixture
def sample_data():
    return {"community_name": "Ogoki"}


@pytest.fixture
def client():
    """FastAPI test client for integration tests"""
    return TestClient(app)
