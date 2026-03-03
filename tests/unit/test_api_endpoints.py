"""Unit tests for API endpoints - HTTP contract only, no workflow logic."""

import pytest

pytestmark = pytest.mark.unit


def test_health_endpoint(client):
    """Test that health endpoint returns correct structure"""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"


def test_get_runs_returns_dict(client):
    """Test that GET /runs returns a dictionary"""
    response = client.get("/runs")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, dict)


def test_get_current_run_returns_expected_format(client):
    """Test that GET /runs/current returns expected format"""
    response = client.get("/runs/current")
    assert response.status_code == 200
    data = response.json()
    # Should have current_run_id key when idle, or run fields when active
    assert "current_run_id" in data or "run_id" in data or "status" in data


def test_post_run_validates_missing_fields(client):
    """Test that POST /runs validates required fields"""
    response = client.post("/runs", json={})
    assert response.status_code == 422


def test_post_run_validates_invalid_name(client):
    """Test that POST /runs rejects empty community names"""
    response = client.post("/runs", json={"community_name": ""})
    assert response.status_code == 400  # API returns 400 for empty names


def test_get_analysis_validates_run_id_format(client):
    """Test that GET /runs/{run_id}/analysis-md validates run_id"""
    response = client.get("/runs/invalid-uuid-12345/analysis-md")
    assert response.status_code == 404
