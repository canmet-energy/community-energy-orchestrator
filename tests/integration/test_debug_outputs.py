"""Integration tests for debug_outputs orchestrator functions.

Tests focus on file system operations, parallel processing, and log file generation.
"""

import tempfile
from pathlib import Path

import pytest
import workflow.debug_outputs as debug

pytestmark = pytest.mark.integration


# Removed test_community_csv_files fixture - tests now use real community "Aklavik"
# from the actual CSV files instead of mocking, which works properly with multiprocessing


# =============================================================================
# debug_timeseries_outputs tests
# =============================================================================


def test_debug_timeseries_outputs_all_files_found(monkeypatch, tmp_path):
    """Test debug_timeseries_outputs when all required files are present."""
    community_name = "TestCommunity"

    # Create directory structure
    output_dir = tmp_path / community_name / "archetypes" / "output"
    output_dir.mkdir(parents=True)

    # Mock requirements
    requirements = {"pre-2002-single": 2, "2002-2016-semi": 1}

    # Create the required files
    for i in range(2):
        file_dir = output_dir / f"pre-2002-single_{i+1}" / "run"
        file_dir.mkdir(parents=True)
        (file_dir / "results_timeseries.csv").write_text("dummy data", encoding="utf-8")

    file_dir = output_dir / "2002-2016-semi_1" / "run"
    file_dir.mkdir(parents=True)
    (file_dir / "results_timeseries.csv").write_text("dummy data", encoding="utf-8")

    # Mock dependencies
    monkeypatch.setattr(debug, "output_dir", lambda: tmp_path)
    monkeypatch.setattr(debug, "get_community_requirements", lambda x: requirements)

    # Run the function
    log_path = debug.debug_timeseries_outputs(community_name)

    # Verify log file was created
    assert log_path.exists()

    # Read and verify log content
    log_content = log_path.read_text(encoding="utf-8")
    assert f"Timeseries output debug for {community_name}" in log_content
    assert "pre-2002-single: required=2, found=2" in log_content
    assert "2002-2016-semi: required=1, found=1" in log_content
    assert "All required timeseries outputs found." in log_content
    assert "Missing timeseries outputs by type:" not in log_content


def test_debug_timeseries_outputs_some_files_missing(monkeypatch, tmp_path):
    """Test debug_timeseries_outputs when some files are missing."""
    community_name = "TestCommunity"

    output_dir = tmp_path / community_name / "archetypes" / "output"
    output_dir.mkdir(parents=True)

    requirements = {"pre-2002-single": 3, "2002-2016-semi": 2}

    # Create only 1 file for pre-2002-single (need 3)
    file_dir = output_dir / "pre-2002-single_1" / "run"
    file_dir.mkdir(parents=True)
    (file_dir / "results_timeseries.csv").write_text("dummy", encoding="utf-8")

    # Create both files for 2002-2016-semi
    for i in range(2):
        file_dir = output_dir / f"2002-2016-semi_{i+1}" / "run"
        file_dir.mkdir(parents=True)
        (file_dir / "results_timeseries.csv").write_text("dummy", encoding="utf-8")

    monkeypatch.setattr(debug, "output_dir", lambda: tmp_path)
    monkeypatch.setattr(debug, "get_community_requirements", lambda x: requirements)

    log_path = debug.debug_timeseries_outputs(community_name)

    log_content = log_path.read_text(encoding="utf-8")
    assert "pre-2002-single: required=3, found=1" in log_content
    assert "2002-2016-semi: required=2, found=2" in log_content
    assert "Missing timeseries outputs by type:" in log_content
    assert "pre-2002-single: 2 missing" in log_content


def test_debug_timeseries_outputs_no_output_directory(monkeypatch, tmp_path):
    """Test debug_timeseries_outputs when output directory doesn't exist."""
    community_name = "TestCommunity"

    requirements = {"pre-2002-single": 2}

    monkeypatch.setattr(debug, "output_dir", lambda: tmp_path)
    monkeypatch.setattr(debug, "get_community_requirements", lambda x: requirements)

    log_path = debug.debug_timeseries_outputs(community_name)

    log_content = log_path.read_text(encoding="utf-8")
    assert "pre-2002-single: required=2, found=0" in log_content
    assert "Missing timeseries outputs by type:" in log_content
    assert "pre-2002-single: 2 missing" in log_content


def test_debug_timeseries_outputs_empty_output_directory(monkeypatch, tmp_path):
    """Test debug_timeseries_outputs when output directory exists but is empty."""
    community_name = "TestCommunity"

    output_dir = tmp_path / community_name / "archetypes" / "output"
    output_dir.mkdir(parents=True)

    requirements = {"pre-2002-single": 2}

    monkeypatch.setattr(debug, "output_dir", lambda: tmp_path)
    monkeypatch.setattr(debug, "get_community_requirements", lambda x: requirements)

    log_path = debug.debug_timeseries_outputs(community_name)

    log_content = log_path.read_text(encoding="utf-8")
    assert "pre-2002-single: required=2, found=0" in log_content
    assert "pre-2002-single: 2 missing" in log_content


def test_debug_timeseries_outputs_creates_log_directory(monkeypatch, tmp_path):
    """Test that debug_timeseries_outputs creates log directory if it doesn't exist."""
    community_name = "TestCommunity"

    requirements = {"pre-2002-single": 1}

    monkeypatch.setattr(debug, "output_dir", lambda: tmp_path)
    monkeypatch.setattr(debug, "get_community_requirements", lambda x: requirements)

    # Don't create analysis directory beforehand
    log_path = debug.debug_timeseries_outputs(community_name)

    # Verify directory was created
    assert log_path.parent.exists()
    assert log_path.parent.name == "analysis"
    assert log_path.exists()


def test_debug_timeseries_outputs_overwrites_existing_log(monkeypatch, tmp_path):
    """Test debug_timeseries_outputs overwrites existing log file (mode 'w')."""
    community_name = "TestCommunity"

    # Create analysis directory and pre-existing log
    analysis_dir = tmp_path / community_name / "analysis"
    analysis_dir.mkdir(parents=True)
    log_path = analysis_dir / "output_debug.log"
    log_path.write_text("Old content that should be overwritten", encoding="utf-8")

    requirements = {"pre-2002-single": 1}

    monkeypatch.setattr(debug, "output_dir", lambda: tmp_path)
    monkeypatch.setattr(debug, "get_community_requirements", lambda x: requirements)

    returned_log_path = debug.debug_timeseries_outputs(community_name)

    # Verify file was overwritten
    log_content = returned_log_path.read_text(encoding="utf-8")
    assert "Old content" not in log_content
    assert "Timeseries output debug for" in log_content


# Note: debug_weather_h2k tests removed as location code validation
# was removed from the workflow (March 2026). Weather location changes
# now only modify Region/English and Location/English fields.
