import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def sample_data():
    return {"community_name": "Ogoki"}


@pytest.fixture
def client():
    """FastAPI test client for integration tests"""
    return TestClient(app)

