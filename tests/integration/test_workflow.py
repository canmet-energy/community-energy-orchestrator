"""Integration tests - Component coordination and workflow orchestration.

Tests focus on how components work together: JSON â†’ Requirements â†’ Workflow â†’ Files.
Unit tests cover individual function behavior; integration tests verify coordination.
"""

import time

import pytest
import workflow.requirements as req
from workflow.paths import output_dir

pytestmark = pytest.mark.integration


# =============================================================================
# JSON â†’ Requirements Integration
# =============================================================================


def test_json_provides_valid_requirements_for_known_community(sample_data):
    """Test that JSON data correctly populates requirements for a known community.

    Integration point: JSON file â†’ requirements module â†’ workflow
    """
    community_name = sample_data["community_name"]  # "Ogoki"
    requirements = req.get_community_requirements(community_name)
    weather = req.get_weather_location(community_name)

    # Verify JSON integration
    assert requirements, f"{community_name} should have requirements from JSON"
    assert sum(requirements.values()) > 0, f"{community_name} should have houses"

    # Verify weather location is also populated from JSON
    assert weather, f"{community_name} should have weather location from JSON"
    assert weather == "LANSDOWNE HOUSE", "Expected specific weather location for Ogoki"

    # Verify specific data for Ogoki (55 houses of 2002-2016-single)
    assert (
        requirements.get("2002-2016-single") == 55
    ), "Ogoki should have 55 2002-2016-single houses"


def test_nonexistent_community_returns_empty_requirements():
    """Test that nonexistent community gracefully returns empty requirements.

    Integration point: Workflow handles missing JSON data gracefully
    """
    fake_community = "NonExistentCommunity999"
    requirements = req.get_community_requirements(fake_community)
    weather = req.get_weather_location(fake_community)

    assert requirements == {}, "Nonexistent community should return empty requirements"
    assert weather == "", "Nonexistent community should return empty weather location"


# =============================================================================
# API â†’ Workflow Integration
# =============================================================================


def test_api_accepts_valid_community_and_queues_workflow(client, sample_data):
    """Test that API correctly accepts and queues workflow for valid community.

    Integration point: API â†’ Workflow service â†’ Background task
    """
    community_name = sample_data["community_name"]

    # Verify community exists in JSON first
    requirements = req.get_community_requirements(community_name)
    assert requirements, f"{community_name} should exist in JSON"

    # Create a run through API
    response = client.post("/runs", json={"community_name": community_name})

    # Accept 200 (queued) or 409 (another run active from previous test)
    assert response.status_code in [200, 409], "Should accept valid community"

    if response.status_code == 200:
        data = response.json()
        assert "run_id" in data
        assert data["community_name"] == community_name
        assert data["status"] == "queued"

        # Cleanup - mark run as completed to avoid blocking future tests
        import app.main

        with app.main._lock:
            if data["run_id"] in app.main._runs:
                app.main._runs[data["run_id"]]["status"] = "completed"
            app.main._current_run_id = None


def test_api_handles_nonexistent_community_gracefully(client):
    """Test that API+workflow handles nonexistent community without crashing.

    Integration point: API â†’ Workflow â†’ JSON validation â†’ Graceful failure
    The workflow raises ValueError for unknown communities, which the API
    background task catches and records as a failed run.
    """
    import app.main

    fake_community = "NonExistentCommunity999"

    # Verify it doesn't exist
    requirements = req.get_community_requirements(fake_community)
    assert not requirements, "Test community should not exist in JSON"

    # API should accept the request (validation happens in background task)
    response = client.post("/runs", json={"community_name": fake_community})
    if response.status_code == 409:
        with app.main._lock:
            app.main._current_run_id = None
            app.main._runs.clear()
        response = client.post("/runs", json={"community_name": fake_community})

    assert response.status_code == 200, "API should accept request even for nonexistent community"
    run_id = response.json()["run_id"]

    # Wait for background task to complete
    time.sleep(0.5)

    # Run should be marked as failed with a meaningful error
    status_response = client.get(f"/runs/{run_id}")
    data = status_response.json()
    assert data["status"] == "failed", "Nonexistent community should fail"
    assert "not found in database" in data["error"], "Error should mention community not found"

    # Cleanup
    with app.main._lock:
        app.main._current_run_id = None
        app.main._runs.clear()


# =============================================================================
# Workflow â†’ File System Integration
# =============================================================================


def test_workflow_creates_directory_structure(monkeypatch, tmp_path):
    """Test that workflow creates expected directory structure.

    Integration point: Workflow â†’ File system operations
    """
    from workflow import process_community_workflow as workflow

    # Use tmp_path for isolation
    monkeypatch.setattr(workflow, "output_dir", lambda: tmp_path)

    community_name = "TestCommunity"

    # Create directories (this is what workflow does first)
    base_path = workflow.create_community_directories(community_name)

    # Verify structure matches workflow expectations
    assert (base_path / "archetypes").exists(), "Should create archetypes directory"
    assert (base_path / "timeseries").exists(), "Should create timeseries directory"
    assert (base_path / "analysis").exists(), "Should create analysis directory"


def test_workflow_creates_manifest_with_csv_data(monkeypatch, tmp_path, sample_data):
    """Test that workflow integrates JSON data into manifest file.

    Integration point: JSON â†’ Requirements â†’ Manifest generation
    """
    from workflow import process_community_workflow as workflow

    monkeypatch.setattr(workflow, "output_dir", lambda: tmp_path)
    # Don't mock get_weather_location - let it read from actual JSON

    community_name = sample_data["community_name"]
    requirements = req.get_community_requirements(community_name)

    # Create manifest (workflow does this after reading JSON)
    manifest_path = workflow.create_manifest(community_name, requirements)

    assert manifest_path.exists(), "Manifest should be created"
    content = manifest_path.read_text(encoding="utf-8")

    # Verify JSON data is integrated into manifest
    assert community_name in content, "Manifest should contain community name"
    assert "LANSDOWNE HOUSE" in content, "Manifest should contain weather location from JSON"
    assert "55" in content, "Manifest should contain house count from JSON"


# =============================================================================
# Run State Transitions Integration
# =============================================================================


def test_run_transitions_through_states(client, monkeypatch):
    """Test that run properly transitions: queued â†’ running â†’ completed.

    Integration point: API â†’ Background task â†’ State management
    """
    import app.main
    from workflow import process_community_workflow

    # Mock at the main() level to track calls and complete quickly
    workflow_called = []
    original_main = process_community_workflow.main

    def mock_main(community_name):
        workflow_called.append(community_name)
        time.sleep(0.1)  # Brief delay to test state transition
        return 0  # Success

    monkeypatch.setattr(process_community_workflow, "main", mock_main)

    # Create a run
    response = client.post("/runs", json={"community_name": "TestCommunity"})

    # Handle case where another run is active
    if response.status_code == 409:
        # Clear any existing run
        with app.main._lock:
            app.main._current_run_id = None
            app.main._runs.clear()
        # Try again
        response = client.post("/runs", json={"community_name": "TestCommunity"})

    assert response.status_code == 200
    data = response.json()
    run_id = data["run_id"]

    # Initially queued
    assert data["status"] == "queued"

    # Wait for background task to complete
    max_wait = 5  # seconds
    waited = 0
    final_status = None

    while waited < max_wait:
        time.sleep(0.2)
        waited += 0.2

        # Check current status
        status_response = client.get(f"/runs/{run_id}")
        current_status = status_response.json()["status"]

        if current_status in ["completed", "failed"]:
            final_status = current_status
            break

    # Verify workflow completed
    assert final_status == "completed", f"Run should complete within {max_wait}s"
    assert len(workflow_called) == 1, "Workflow should be called once"
    assert workflow_called[0] == "TestCommunity", "Should receive community name from API"

    # Cleanup
    with app.main._lock:
        app.main._current_run_id = None
        app.main._runs.clear()


def test_concurrent_runs_are_prevented(client, monkeypatch):
    """Test that concurrent runs are properly blocked at the API level.

    Integration point: API concurrency control â†’ Run state management
    """
    import app.main
    import workflow.service

    # Mock workflow to run slowly
    def slow_workflow(community_name):
        time.sleep(2)

    monkeypatch.setattr(workflow.service, "run_community_workflow", slow_workflow)

    # Manually set up first run as active
    with app.main._lock:
        app.main._current_run_id = "run-1"
        app.main._runs["run-1"] = {
            "run_id": "run-1",
            "community_name": "Community1",
            "status": "running",
            "error": None,
        }

    try:
        # Try to create second run while first is active
        response = client.post("/runs", json={"community_name": "Community2"})

        # Should be rejected
        assert response.status_code == 409
        assert "already in progress" in response.json()["detail"].lower()

        # Verify first run is still active
        current = client.get("/runs/current")
        assert current.json()["run_id"] == "run-1"
    finally:
        # Cleanup
        with app.main._lock:
            app.main._current_run_id = None
            app.main._runs.clear()


# =============================================================================
# Error Propagation Integration
# =============================================================================


def test_workflow_error_propagates_to_api(client, monkeypatch):
    """Test that workflow errors are properly captured and exposed via API.

    Integration point: Workflow error â†’ Background task â†’ API state â†’ Client
    """
    import app.main
    from workflow import process_community_workflow

    # Mock at main() level to raise an error
    def failing_main(community_name):
        raise RuntimeError("Simulated workflow failure")

    monkeypatch.setattr(process_community_workflow, "main", failing_main)

    # Create a run
    response = client.post("/runs", json={"community_name": "TestCommunity"})

    if response.status_code == 409:
        with app.main._lock:
            app.main._current_run_id = None
            app.main._runs.clear()
        response = client.post("/runs", json={"community_name": "TestCommunity"})

    assert response.status_code == 200
    run_id = response.json()["run_id"]

    # Wait for failure
    time.sleep(0.5)

    # Check that error is captured
    status_response = client.get(f"/runs/{run_id}")
    data = status_response.json()

    assert data["status"] == "failed"
    assert data["error"] is not None
    assert "workflow failure" in data["error"].lower()

    # Cleanup
    with app.main._lock:
        app.main._current_run_id = None
        app.main._runs.clear()
