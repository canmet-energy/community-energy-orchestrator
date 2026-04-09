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
    import workflow.outputs

    # Patch communities_dir where it's used (workflow.outputs)
    original_communities_dir = workflow.outputs.communities_dir
    workflow.outputs.communities_dir = lambda: tmp_path

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
        workflow.outputs.communities_dir = original_communities_dir
        with app.main._lock:
            app.main._current_run_id = None
            app.main._runs.clear()


# =============================================================================
# GET /runs/{run_id}/analysis-data - Get analysis data (JSON)
# =============================================================================


def test_get_analysis_data_returns_404_when_run_not_found(client):
    """Test that analysis data endpoint returns 404 for nonexistent run."""
    response = client.get("/runs/invalid-uuid-12345/analysis-data")
    assert response.status_code == 404


def test_get_analysis_data_returns_json_when_file_exists(client, tmp_path):
    """Test that analysis data endpoint returns JSON content when file exists."""
    import json

    import app.main
    import workflow.outputs

    original_communities_dir = workflow.outputs.communities_dir
    workflow.outputs.communities_dir = lambda: tmp_path

    run_id = "test-run-analysis-data"
    with app.main._lock:
        app.main._runs[run_id] = {
            "run_id": run_id,
            "community_name": "TestCommunity",
            "status": "completed",
            "error": None,
        }

    # Create the analysis JSON file
    analysis_dir = tmp_path / "TestCommunity" / "analysis"
    analysis_dir.mkdir(parents=True)
    analysis_file = analysis_dir / "TestCommunity_analysis.json"
    test_data = {
        "heating_load": {"total_annual_gj": 1000.0},
        "heating_energy": {"total_annual_gj": 1200.0},
    }
    analysis_file.write_text(json.dumps(test_data), encoding="utf-8")

    try:
        response = client.get(f"/runs/{run_id}/analysis-data")
        assert response.status_code == 200
        data = response.json()
        assert data["community_name"] == "TestCommunity"
        assert "data" in data
        # Data is now a dict directly (no JSON string)
        assert data["data"] == test_data
    finally:
        workflow.outputs.communities_dir = original_communities_dir
        with app.main._lock:
            app.main._current_run_id = None
            app.main._runs.clear()


# =============================================================================
# GET /runs/{run_id}/download/analysis-md - Download analysis markdown
# =============================================================================


def test_download_analysis_md_returns_404_when_run_not_found(client):
    """Test that download returns 404 for nonexistent run."""
    response = client.get("/runs/invalid-id/download/analysis-md")
    assert response.status_code == 404


def test_download_analysis_md_returns_file(client, tmp_path):
    """Test that download returns markdown file with correct headers."""
    import app.main
    import workflow.outputs

    original_communities_dir = workflow.outputs.communities_dir
    workflow.outputs.communities_dir = lambda: tmp_path

    run_id = "test-run-md-download"
    with app.main._lock:
        app.main._runs[run_id] = {
            "run_id": run_id,
            "community_name": "TestCommunity",
            "status": "completed",
            "error": None,
        }

    # Create a fake markdown file
    analysis_dir = tmp_path / "TestCommunity" / "analysis"
    analysis_dir.mkdir(parents=True)
    md_file = analysis_dir / "TestCommunity_analysis.md"
    md_file.write_text("# Test Analysis\n\nContent here.", encoding="utf-8")

    try:
        response = client.get(f"/runs/{run_id}/download/analysis-md")
        assert response.status_code == 200
        assert "text/markdown" in response.headers["content-type"]
        assert "TestCommunity_analysis.md" in response.headers.get("content-disposition", "")
    finally:
        workflow.outputs.communities_dir = original_communities_dir
        with app.main._lock:
            app.main._runs.clear()


# =============================================================================
# GET /communities - List all communities
# =============================================================================


def test_get_communities_returns_list(client):
    """Test that communities endpoint returns a list with expected fields."""
    response = client.get("/communities")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) > 0

    # Check structure of first community
    community = data[0]
    assert "name" in community
    assert "province_territory" in community
    assert "population" in community
    assert "total_houses" in community
    assert "hdd" in community
    assert "weather_location" in community


# =============================================================================
# GET /runs/{run_id}/daily-load-data - Get daily load data
# =============================================================================


def test_get_daily_load_data_returns_404_when_run_not_found(client):
    """Test that daily load data endpoint returns 404 for nonexistent run."""
    response = client.get("/runs/invalid-uuid-12345/daily-load-data")
    assert response.status_code == 404


def test_get_daily_load_data_returns_404_when_file_not_found(client, monkeypatch):
    """Test that daily load data endpoint returns 404 when CSV file doesn't exist."""
    import app.main
    import workflow.service

    monkeypatch.setattr(workflow.service, "run_community_workflow", lambda x: None)

    # Create a run
    create_response = client.post("/runs", json={"community_name": "TestCommunity"})
    run_id = create_response.json()["run_id"]

    # Try to get daily load data before file exists
    response = client.get(f"/runs/{run_id}/daily-load-data")
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()

    # Cleanup
    with app.main._lock:
        app.main._current_run_id = None
        app.main._runs.clear()


def test_get_daily_load_data_returns_json_when_file_exists(client, tmp_path):
    """Test that daily load data endpoint returns processed JSON when file exists."""
    import app.main
    import workflow.outputs

    # Patch communities_dir
    original_communities_dir = workflow.outputs.communities_dir
    workflow.outputs.communities_dir = lambda: tmp_path

    # Manually create a completed run
    run_id = "test-run-daily-load"
    with app.main._lock:
        app.main._runs[run_id] = {
            "run_id": run_id,
            "community_name": "TestCommunity",
            "status": "completed",
            "error": None,
        }

    # Create the community-total CSV file with 48 hours of data (2 days)
    analysis_dir = tmp_path / "TestCommunity" / "analysis"
    analysis_dir.mkdir(parents=True)
    csv_file = analysis_dir / "TestCommunity-community_total.csv"

    # Create CSV with header and 48 rows (2 days)
    csv_lines = [
        "Time,Heating_Load_GJ,Heating_Propane_GJ,Heating_Oil_GJ,Heating_Electricity_GJ,Total_Heating_Energy_GJ"
    ]
    for day in range(2):
        for hour in range(24):
            # Day 0: loads 1.0-2.0, Day 1: loads 2.0-3.0
            load = 1.0 + day + (hour / 24.0)
            csv_lines.append(f"2024-01-{day+1:02d} {hour:02d}:00:00,{load},0.5,0.3,0.2,1.0")

    csv_file.write_text("\n".join(csv_lines), encoding="utf-8")

    try:
        # Get daily load data
        response = client.get(f"/runs/{run_id}/daily-load-data")
        assert response.status_code == 200
        data = response.json()
        assert data["community_name"] == "TestCommunity"
        assert "data" in data

        # Data is now a list of dicts directly (no JSON string)
        daily_data = data["data"]

        # Should have 2 days
        assert len(daily_data) == 2

        # Check structure of first day
        assert "day" in daily_data[0]
        assert "avg_energy" in daily_data[0]
        assert "peak_energy" in daily_data[0]
        assert daily_data[0]["day"] == 1

    finally:
        # Cleanup
        workflow.outputs.communities_dir = original_communities_dir
        with app.main._lock:
            app.main._current_run_id = None
            app.main._runs.clear()


# =============================================================================
# GET /runs/{run_id}/download/community-total - Download community total CSV
# =============================================================================


def test_download_community_total_returns_404_when_run_not_found(client):
    """Test that download returns 404 for nonexistent run."""
    response = client.get("/runs/invalid-id/download/community-total")
    assert response.status_code == 404


def test_download_community_total_returns_404_when_file_missing(client, tmp_path):
    """Test that download returns 404 when CSV doesn't exist."""
    import app.main
    import workflow.outputs

    original_communities_dir = workflow.outputs.communities_dir
    workflow.outputs.communities_dir = lambda: tmp_path

    run_id = "test-run-no-csv"
    with app.main._lock:
        app.main._runs[run_id] = {
            "run_id": run_id,
            "community_name": "TestCommunity",
            "status": "completed",
            "error": None,
        }

    try:
        response = client.get(f"/runs/{run_id}/download/community-total")
        assert response.status_code == 404
    finally:
        workflow.outputs.communities_dir = original_communities_dir
        with app.main._lock:
            app.main._runs.clear()


def test_download_community_total_returns_csv(client, tmp_path):
    """Test that download returns CSV file with correct headers."""
    import app.main
    import workflow.outputs

    original_communities_dir = workflow.outputs.communities_dir
    workflow.outputs.communities_dir = lambda: tmp_path

    run_id = "test-run-csv"
    with app.main._lock:
        app.main._runs[run_id] = {
            "run_id": run_id,
            "community_name": "TestCommunity",
            "status": "completed",
            "error": None,
        }

    # Create a fake CSV
    analysis_dir = tmp_path / "TestCommunity" / "analysis"
    analysis_dir.mkdir(parents=True)
    csv_file = analysis_dir / "TestCommunity-community_total.csv"
    csv_file.write_text("col1,col2\n1,2\n", encoding="utf-8")

    try:
        response = client.get(f"/runs/{run_id}/download/community-total")
        assert response.status_code == 200
        assert "text/csv" in response.headers["content-type"]
        assert "TestCommunity-community_total.csv" in response.headers.get(
            "content-disposition", ""
        )
    finally:
        workflow.outputs.communities_dir = original_communities_dir
        with app.main._lock:
            app.main._runs.clear()


# =============================================================================
# GET /runs/{run_id}/download/dwelling-timeseries - Download timeseries ZIP
# =============================================================================


def test_download_dwelling_timeseries_returns_404_when_run_not_found(client):
    """Test that download returns 404 for nonexistent run."""
    response = client.get("/runs/invalid-id/download/dwelling-timeseries")
    assert response.status_code == 404


def test_download_dwelling_timeseries_returns_404_when_dir_missing(client, tmp_path):
    """Test that download returns 404 when timeseries directory doesn't exist."""
    import app.main
    import workflow.outputs

    original_communities_dir = workflow.outputs.communities_dir
    workflow.outputs.communities_dir = lambda: tmp_path

    run_id = "test-run-no-ts"
    with app.main._lock:
        app.main._runs[run_id] = {
            "run_id": run_id,
            "community_name": "TestCommunity",
            "status": "completed",
            "error": None,
        }

    try:
        response = client.get(f"/runs/{run_id}/download/dwelling-timeseries")
        assert response.status_code == 404
    finally:
        workflow.outputs.communities_dir = original_communities_dir
        with app.main._lock:
            app.main._runs.clear()


def test_download_dwelling_timeseries_returns_zip(client, tmp_path):
    """Test that download returns valid ZIP with correct headers."""
    import zipfile
    from io import BytesIO

    import app.main
    import workflow.outputs

    original_communities_dir = workflow.outputs.communities_dir
    workflow.outputs.communities_dir = lambda: tmp_path

    run_id = "test-run-zip"
    with app.main._lock:
        app.main._runs[run_id] = {
            "run_id": run_id,
            "community_name": "TestCommunity",
            "status": "completed",
            "error": None,
        }

    # Create fake timeseries files
    ts_dir = tmp_path / "TestCommunity" / "timeseries"
    ts_dir.mkdir(parents=True)
    (ts_dir / "pre-2002-single_EX-001-results_timeseries.csv").write_text("a,b\n1,2\n")
    (ts_dir / "pre-2002-single_EX-002-results_timeseries.csv").write_text("a,b\n3,4\n")

    try:
        response = client.get(f"/runs/{run_id}/download/dwelling-timeseries")
        assert response.status_code == 200
        assert response.headers["content-type"] == "application/zip"
        assert "TestCommunity-dwelling-timeseries.zip" in response.headers["content-disposition"]

        # Verify it's a valid ZIP with the right files
        zf = zipfile.ZipFile(BytesIO(response.content))
        assert len(zf.namelist()) == 2
    finally:
        workflow.outputs.communities_dir = original_communities_dir
        with app.main._lock:
            app.main._runs.clear()

