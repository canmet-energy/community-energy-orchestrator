"""Unit tests for API endpoints - HTTP contract only, no workflow logic.

Tests focus on API behavior: validation, status codes, response structure.
Workflow execution logic is tested in integration tests.
"""

import pytest

pytestmark = pytest.mark.unit


# =============================================================================
# GET /health - System health check
# =============================================================================


def test_health_endpoint_returns_status(client):
    """Test that health endpoint returns correct structure and status."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "warning" in data
    assert "active_runs" in data
    assert isinstance(data["active_runs"], int)


# =============================================================================
# POST /runs - Create new workflow run
# =============================================================================


def test_post_run_creates_run_successfully(client, monkeypatch):
    """Test that POST /runs creates a run with valid community name."""
    # Mock workflow so it doesn't actually run
    import workflow.service

    monkeypatch.setattr(workflow.service, "run_community_workflow", lambda x: None)

    response = client.post("/runs", json={"community_name": "TestCommunity"})

    assert response.status_code == 200
    data = response.json()
    assert "run_id" in data
    assert data["community_name"] == "TestCommunity"
    assert data["status"] == "queued"
    assert data["error"] is None


def test_post_run_validates_missing_fields(client):
    """Test that POST /runs validates required fields."""
    response = client.post("/runs", json={})
    assert response.status_code == 422


def test_post_run_rejects_empty_name(client):
    """Test that POST /runs rejects empty or whitespace-only names."""
    for empty_name in ["", "   ", "\t\n"]:
        response = client.post("/runs", json={"community_name": empty_name})
        assert response.status_code == 400


def test_post_run_rejects_invalid_characters(client):
    """Test that POST /runs rejects dangerous file system characters."""
    # Test path traversal and dangerous characters
    invalid_names = [
        "../etc/passwd",  # Path traversal
        "community/subdir",  # Forward slash
        "community\\subdir",  # Backslash
        "community<script>",  # Angle brackets
        "community|rm",  # Pipe
    ]
    for name in invalid_names:
        response = client.post("/runs", json={"community_name": name})
        assert response.status_code == 400, f"Should reject: {name}"


def test_post_run_rejects_concurrent_requests(client, monkeypatch):
    """Test that POST /runs returns 409 when another run is active."""
    import app.main

    # Mock workflow to prevent actual execution
    import workflow.service

    monkeypatch.setattr(workflow.service, "run_community_workflow", lambda x: None)

    # Manually set up a run in progress
    with app.main._lock:
        app.main._current_run_id = "test-run-123"
        app.main._runs["test-run-123"] = {
            "run_id": "test-run-123",
            "community_name": "ExistingCommunity",
            "status": "running",
            "error": None,
        }

    try:
        response = client.post("/runs", json={"community_name": "NewCommunity"})
        assert response.status_code == 409
        assert "already in progress" in response.json()["detail"].lower()
    finally:
        with app.main._lock:
            app.main._current_run_id = None
            app.main._runs.clear()


# =============================================================================
# GET /runs - List all runs
# =============================================================================


def test_get_runs_returns_empty_dict_initially(client):
    """Test that GET /runs returns empty dict when no runs exist."""
    response = client.get("/runs")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, dict)
    assert len(data) == 0


def test_get_runs_lists_multiple_runs(client, monkeypatch):
    """Test that GET /runs returns all created runs."""
    import app.main
    import workflow.service

    monkeypatch.setattr(workflow.service, "run_community_workflow", lambda x: None)

    # Create multiple runs
    client.post("/runs", json={"community_name": "Community1"})

    # Wait for first to clear (we need to manually clear for test)
    with app.main._lock:
        app.main._current_run_id = None

    client.post("/runs", json={"community_name": "Community2"})

    response = client.get("/runs")
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 2

    # Cleanup
    with app.main._lock:
        app.main._current_run_id = None
        app.main._runs.clear()


# =============================================================================
# GET /runs/current - Get active run
# =============================================================================


def test_get_current_run_when_idle(client):
    """Test that GET /runs/current returns null when no run is active."""
    response = client.get("/runs/current")
    assert response.status_code == 200
    data = response.json()
    assert "current_run_id" in data
    assert data["current_run_id"] is None


def test_get_current_run_when_active(client, monkeypatch):
    """Test that GET /runs/current returns run details when active."""
    import app.main

    # Manually set up an active run (avoids background task timing issues)
    with app.main._lock:
        app.main._current_run_id = "test-run-active"
        app.main._runs["test-run-active"] = {
            "run_id": "test-run-active",
            "community_name": "TestCommunity",
            "status": "running",
            "error": None,
        }

    try:
        # Get current run
        response = client.get("/runs/current")
        assert response.status_code == 200
        data = response.json()
        assert data["run_id"] == "test-run-active"
        assert data["community_name"] == "TestCommunity"
        assert data["status"] == "running"
    finally:
        # Cleanup
        with app.main._lock:
            app.main._current_run_id = None
            app.main._runs.clear()


# =============================================================================
# GET /runs/{run_id} - Get specific run status
# =============================================================================


def test_get_run_returns_run_details(client, monkeypatch):
    """Test that GET /runs/{run_id} returns run details for valid ID."""
    import workflow.service

    monkeypatch.setattr(workflow.service, "run_community_workflow", lambda x: None)

    # Create a run
    create_response = client.post("/runs", json={"community_name": "TestCommunity"})
    run_id = create_response.json()["run_id"]

    # Get specific run
    response = client.get(f"/runs/{run_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["run_id"] == run_id
    assert data["community_name"] == "TestCommunity"
    assert "status" in data

    # Cleanup
    import app.main

    with app.main._lock:
        app.main._current_run_id = None
        app.main._runs.clear()


def test_get_run_returns_404_for_nonexistent_run(client):
    """Test that GET /runs/{run_id} returns 404 for invalid run ID."""
    response = client.get("/runs/nonexistent-run-id")
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


# =============================================================================
# GET /runs/{run_id}/analysis-md - Get analysis markdown
# =============================================================================


def test_get_analysis_returns_404_when_run_not_found(client):
    """Test that analysis endpoint returns 404 for nonexistent run."""
    response = client.get("/runs/invalid-uuid-12345/analysis-md")
    assert response.status_code == 404


def test_get_analysis_returns_404_when_file_not_found(client, monkeypatch):
    """Test that analysis endpoint returns 404 when markdown file doesn't exist."""
    import app.main
    import workflow.service

    monkeypatch.setattr(workflow.service, "run_community_workflow", lambda x: None)

    # Create a run
    create_response = client.post("/runs", json={"community_name": "TestCommunity"})
    run_id = create_response.json()["run_id"]

    # Try to get analysis before file exists
    response = client.get(f"/runs/{run_id}/analysis-md")
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()

    # Cleanup
    with app.main._lock:
        app.main._current_run_id = None
        app.main._runs.clear()


def test_get_analysis_returns_markdown_when_file_exists(client, tmp_path):
    """Test that analysis endpoint returns markdown content when file exists."""
    import app.main

    # Patch communities_dir at the point of use in app.main
    original_communities_dir = app.main.communities_dir
    app.main.communities_dir = lambda: tmp_path

    # Manually create a completed run
    run_id = "test-run-completed"
    with app.main._lock:
        app.main._runs[run_id] = {
            "run_id": run_id,
            "community_name": "TestCommunity",
            "status": "completed",
            "error": None,
        }

    # Create the analysis markdown file
    analysis_dir = tmp_path / "TestCommunity" / "analysis"
    analysis_dir.mkdir(parents=True)
    analysis_file = analysis_dir / "TestCommunity_analysis.md"
    analysis_content = "# Test Analysis\n\nThis is test content."
    analysis_file.write_text(analysis_content, encoding="utf-8")

    try:
        # Get analysis
        response = client.get(f"/runs/{run_id}/analysis-md")
        assert response.status_code == 200
        data = response.json()
        assert data["community_name"] == "TestCommunity"
        assert "path" in data
        assert data["markdown"] == analysis_content
    finally:
        # Cleanup
        app.main.communities_dir = original_communities_dir
        with app.main._lock:
            app.main._current_run_id = None
            app.main._runs.clear()
