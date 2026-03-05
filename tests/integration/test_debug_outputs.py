"""Integration tests for debug_outputs orchestrator functions.

Tests focus on file system operations, parallel processing, and log file generation.
"""

import tempfile
from pathlib import Path

import pytest

import workflow.debug_outputs as debug
from workflow.core import csv_dir

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
    requirements = {"pre-2000-single": 2, "2001-2015-semi": 1}

    # Create the required files
    for i in range(2):
        file_dir = output_dir / f"pre-2000-single_{i+1}" / "run"
        file_dir.mkdir(parents=True)
        (file_dir / "results_timeseries.csv").write_text("dummy data", encoding="utf-8")

    file_dir = output_dir / "2001-2015-semi_1" / "run"
    file_dir.mkdir(parents=True)
    (file_dir / "results_timeseries.csv").write_text("dummy data", encoding="utf-8")

    # Mock dependencies
    monkeypatch.setattr(debug, "communities_dir", lambda: tmp_path)
    monkeypatch.setattr(debug, "get_community_requirements", lambda x: requirements)

    # Run the function
    log_path = debug.debug_timeseries_outputs(community_name)

    # Verify log file was created
    assert log_path.exists()

    # Read and verify log content
    log_content = log_path.read_text(encoding="utf-8")
    assert f"Timeseries output debug for {community_name}" in log_content
    assert "pre-2000-single: required=2, found=2" in log_content
    assert "2001-2015-semi: required=1, found=1" in log_content
    assert "All required timeseries outputs found." in log_content
    assert "Missing timeseries outputs by type:" not in log_content


def test_debug_timeseries_outputs_some_files_missing(monkeypatch, tmp_path):
    """Test debug_timeseries_outputs when some files are missing."""
    community_name = "TestCommunity"

    output_dir = tmp_path / community_name / "archetypes" / "output"
    output_dir.mkdir(parents=True)

    requirements = {"pre-2000-single": 3, "2001-2015-semi": 2}

    # Create only 1 file for pre-2000-single (need 3)
    file_dir = output_dir / "pre-2000-single_1" / "run"
    file_dir.mkdir(parents=True)
    (file_dir / "results_timeseries.csv").write_text("dummy", encoding="utf-8")

    # Create both files for 2001-2015-semi
    for i in range(2):
        file_dir = output_dir / f"2001-2015-semi_{i+1}" / "run"
        file_dir.mkdir(parents=True)
        (file_dir / "results_timeseries.csv").write_text("dummy", encoding="utf-8")

    monkeypatch.setattr(debug, "communities_dir", lambda: tmp_path)
    monkeypatch.setattr(debug, "get_community_requirements", lambda x: requirements)

    log_path = debug.debug_timeseries_outputs(community_name)

    log_content = log_path.read_text(encoding="utf-8")
    assert "pre-2000-single: required=3, found=1" in log_content
    assert "2001-2015-semi: required=2, found=2" in log_content
    assert "Missing timeseries outputs by type:" in log_content
    assert "pre-2000-single: 2 missing" in log_content


def test_debug_timeseries_outputs_no_output_directory(monkeypatch, tmp_path):
    """Test debug_timeseries_outputs when output directory doesn't exist."""
    community_name = "TestCommunity"

    requirements = {"pre-2000-single": 2}

    monkeypatch.setattr(debug, "communities_dir", lambda: tmp_path)
    monkeypatch.setattr(debug, "get_community_requirements", lambda x: requirements)

    log_path = debug.debug_timeseries_outputs(community_name)

    log_content = log_path.read_text(encoding="utf-8")
    assert "pre-2000-single: required=2, found=0" in log_content
    assert "Missing timeseries outputs by type:" in log_content
    assert "pre-2000-single: 2 missing" in log_content


def test_debug_timeseries_outputs_empty_output_directory(monkeypatch, tmp_path):
    """Test debug_timeseries_outputs when output directory exists but is empty."""
    community_name = "TestCommunity"

    output_dir = tmp_path / community_name / "archetypes" / "output"
    output_dir.mkdir(parents=True)

    requirements = {"pre-2000-single": 2}

    monkeypatch.setattr(debug, "communities_dir", lambda: tmp_path)
    monkeypatch.setattr(debug, "get_community_requirements", lambda x: requirements)

    log_path = debug.debug_timeseries_outputs(community_name)

    log_content = log_path.read_text(encoding="utf-8")
    assert "pre-2000-single: required=2, found=0" in log_content
    assert "pre-2000-single: 2 missing" in log_content


def test_debug_timeseries_outputs_creates_log_directory(monkeypatch, tmp_path):
    """Test that debug_timeseries_outputs creates log directory if it doesn't exist."""
    community_name = "TestCommunity"

    requirements = {"pre-2000-single": 1}

    monkeypatch.setattr(debug, "communities_dir", lambda: tmp_path)
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

    requirements = {"pre-2000-single": 1}

    monkeypatch.setattr(debug, "communities_dir", lambda: tmp_path)
    monkeypatch.setattr(debug, "get_community_requirements", lambda x: requirements)

    returned_log_path = debug.debug_timeseries_outputs(community_name)

    # Verify file was overwritten
    log_content = returned_log_path.read_text(encoding="utf-8")
    assert "Old content" not in log_content
    assert "Timeseries output debug for" in log_content


# =============================================================================
# debug_weather_h2k tests
# =============================================================================


def test_debug_weather_h2k_no_h2k_files(monkeypatch, tmp_path):
    """Test debug_weather_h2k when no H2K files are found."""
    community_name = "TestCommunity"

    # Create archetype directory but no H2K files
    archetype_dir = tmp_path / community_name / "archetypes"
    archetype_dir.mkdir(parents=True)

    # Create a pre-existing log file to test append mode
    analysis_dir = tmp_path / community_name / "analysis"
    analysis_dir.mkdir(parents=True)
    log_path = analysis_dir / "output_debug.log"
    log_path.write_text("Previous content\n", encoding="utf-8")

    monkeypatch.setattr(debug, "communities_dir", lambda: tmp_path)

    returned_log_path = debug.debug_weather_h2k(community_name)

    # Verify log was appended to
    log_content = returned_log_path.read_text(encoding="utf-8")
    assert "Previous content" in log_content, "Should preserve existing content (append mode)"
    assert "Weather Location Code Validation" in log_content
    assert "No H2K files found." in log_content


def test_debug_weather_h2k_all_files_valid(monkeypatch, tmp_path):
    """Test debug_weather_h2k when all H2K files pass validation."""
    # Use real community "Aklavik" which uses OLD CROW weather station (code 400)
    community_name = "Aklavik"

    archetype_dir = tmp_path / community_name / "archetypes"
    archetype_dir.mkdir(parents=True)

    # Create valid H2K files with location code 400 (OLD CROW)
    xml_content = """<?xml version="1.0"?>
<HouseFile><ProgramInformation><Weather><Location code="400" /></Weather></ProgramInformation></HouseFile>"""

    for i in range(3):
        h2k_file = archetype_dir / f"test_{i}.h2k"
        h2k_file.write_text(xml_content, encoding="latin-1")

    monkeypatch.setattr(debug, "communities_dir", lambda: tmp_path)

    # Create pre-existing log
    analysis_dir = tmp_path / community_name / "analysis"
    analysis_dir.mkdir(parents=True)
    log_path = analysis_dir / "output_debug.log"
    log_path.write_text("Previous content\n", encoding="utf-8")

    returned_log_path = debug.debug_weather_h2k(community_name)

    log_content = returned_log_path.read_text(encoding="utf-8")
    assert "Previous content" in log_content
    assert "Weather Location Code Validation" in log_content
    assert "All H2K files passed location code validation." in log_content


def test_debug_weather_h2k_some_files_invalid(monkeypatch, tmp_path):
    """Test debug_weather_h2k when some H2K files fail validation."""
    # Use real community "Aklavik" which uses OLD CROW weather station (code 400)
    community_name = "Aklavik"

    archetype_dir = tmp_path / community_name / "archetypes"
    archetype_dir.mkdir(parents=True)

    # Create H2K files - one with wrong location code (999 instead of 400)
    valid_xml = """<?xml version="1.0"?>
<HouseFile><ProgramInformation><Weather><Location code="400" /></Weather></ProgramInformation></HouseFile>"""

    invalid_xml = """<?xml version="1.0"?>
<HouseFile><ProgramInformation><Weather><Location code="999" /></Weather></ProgramInformation></HouseFile>"""

    (archetype_dir / "test_0.h2k").write_text(valid_xml, encoding="latin-1")
    (archetype_dir / "test_1.h2k").write_text(invalid_xml, encoding="latin-1")  # Wrong code
    (archetype_dir / "test_2.h2k").write_text(valid_xml, encoding="latin-1")

    monkeypatch.setattr(debug, "communities_dir", lambda: tmp_path)

    # Create pre-existing log
    analysis_dir = tmp_path / community_name / "analysis"
    analysis_dir.mkdir(parents=True)
    log_path = analysis_dir / "output_debug.log"
    log_path.write_text("", encoding="utf-8")

    returned_log_path = debug.debug_weather_h2k(community_name)

    log_content = returned_log_path.read_text(encoding="utf-8")
    assert "Weather Location Code Validation" in log_content
    assert "Validation: FAILED" in log_content
    assert "999" in log_content  # The wrong location code
    assert "test_1.h2k" in log_content
    # Should NOT say all passed
    assert "All H2K files passed" not in log_content


def test_debug_weather_h2k_case_insensitive_file_discovery(monkeypatch, tmp_path, capsys):
    """Test debug_weather_h2k finds .h2k and .H2K files (case-insensitive)."""
    # Use real community "Aklavik" which uses OLD CROW weather station (code 400)
    community_name = "Aklavik"

    archetype_dir = tmp_path / community_name / "archetypes"
    archetype_dir.mkdir(parents=True)

    xml_content = """<?xml version="1.0"?>
<HouseFile><ProgramInformation><Weather><Location code="400" /></Weather></ProgramInformation></HouseFile>"""

    # Create files with different case extensions
    (archetype_dir / "test1.h2k").write_text(xml_content, encoding="latin-1")
    (archetype_dir / "test2.H2K").write_text(xml_content, encoding="latin-1")

    monkeypatch.setattr(debug, "communities_dir", lambda: tmp_path)

    # Create log
    analysis_dir = tmp_path / community_name / "analysis"
    analysis_dir.mkdir(parents=True)
    log_path = analysis_dir / "output_debug.log"
    log_path.write_text("", encoding="utf-8")

    debug.debug_weather_h2k(community_name)

    # Verify both files were found (check the stdout message)
    captured = capsys.readouterr()
    assert "2 H2K files" in captured.out

    # Verify log shows success for both
    log_content = log_path.read_text(encoding="utf-8")
    assert "All H2K files passed location code validation." in log_content


def test_debug_weather_h2k_parallel_processing(monkeypatch, tmp_path, capsys):
    """Test debug_weather_h2k processes multiple files in parallel."""
    # Use real community "Aklavik" which uses OLD CROW weather station (code 400)
    community_name = "Aklavik"

    archetype_dir = tmp_path / community_name / "archetypes"
    archetype_dir.mkdir(parents=True)

    xml_content = """<?xml version="1.0"?>
<HouseFile><ProgramInformation><Weather><Location code="400" /></Weather></ProgramInformation></HouseFile>"""

    # Create 5 files to ensure parallel processing
    for i in range(5):
        h2k_file = archetype_dir / f"test_{i}.h2k"
        h2k_file.write_text(xml_content, encoding="latin-1")

    monkeypatch.setattr(debug, "communities_dir", lambda: tmp_path)

    analysis_dir = tmp_path / community_name / "analysis"
    analysis_dir.mkdir(parents=True)
    log_path = analysis_dir / "output_debug.log"
    log_path.write_text("", encoding="utf-8")

    returned_log_path = debug.debug_weather_h2k(community_name)

    # Verify parallel processing happened (check stdout)
    captured = capsys.readouterr()
    assert "5 H2K files" in captured.out
    assert "workers" in captured.out

    # Verify log shows success
    log_content = returned_log_path.read_text(encoding="utf-8")
    assert "All H2K files passed location code validation." in log_content


def test_debug_weather_h2k_appends_to_log(monkeypatch, tmp_path):
    """Test debug_weather_h2k appends to existing log file (mode 'a')."""
    community_name = "TestCommunity"

    archetype_dir = tmp_path / community_name / "archetypes"
    archetype_dir.mkdir(parents=True)

    xml_content = """<?xml version="1.0"?>
<H2K><Weather><Location code="400"/></Weather></H2K>"""

    h2k_file = archetype_dir / "test.h2k"
    h2k_file.write_text(xml_content, encoding="utf-8")

    def mock_validate(h2k_file, community):
        return (h2k_file, None, "400")

    monkeypatch.setattr(debug, "_validate_single_h2k", mock_validate)
    monkeypatch.setattr(debug, "communities_dir", lambda: tmp_path)

    # Create pre-existing log
    analysis_dir = tmp_path / community_name / "analysis"
    analysis_dir.mkdir(parents=True)
    log_path = analysis_dir / "output_debug.log"
    existing_content = "FIRST SECTION\nSome content\n"
    log_path.write_text(existing_content, encoding="utf-8")

    returned_log_path = debug.debug_weather_h2k(community_name)

    # Verify old content preserved
    log_content = returned_log_path.read_text(encoding="utf-8")
    assert existing_content in log_content
    assert "Weather Location Code Validation" in log_content
