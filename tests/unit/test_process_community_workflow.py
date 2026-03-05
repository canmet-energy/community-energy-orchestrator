"""Unit tests for workflow processing functions.

Tests focus on critical business logic and data handling functions.
Integration tests (in tests/integration/) cover end-to-end workflows.
"""

import math
import os
import tempfile
from pathlib import Path

import pytest

import workflow.process_community_workflow as workflow

pytestmark = pytest.mark.unit


# =============================================================================
# create_community_directories - Directory structure setup
# =============================================================================


def test_create_community_directories_structure(monkeypatch, tmp_path):
    """Test that create_community_directories creates expected structure."""
    monkeypatch.setattr(workflow, "communities_dir", lambda: tmp_path)

    base_path = workflow.create_community_directories("TestCommunity")

    assert base_path.exists()
    assert base_path == tmp_path / "TestCommunity"
    assert (base_path / "archetypes").is_dir()
    assert (base_path / "timeseries").is_dir()
    assert (base_path / "analysis").is_dir()


def test_create_community_directories_idempotent(monkeypatch, tmp_path):
    """Test that creating directories twice doesn't fail (idempotent)."""
    monkeypatch.setattr(workflow, "communities_dir", lambda: tmp_path)

    base_path1 = workflow.create_community_directories("TestCommunity")
    base_path2 = workflow.create_community_directories("TestCommunity")

    assert base_path1 == base_path2


# =============================================================================
# create_manifest - Documentation generation
# =============================================================================


def test_create_manifest_includes_requirements(monkeypatch, tmp_path):
    """Test that manifest file contains all required sections and data."""
    monkeypatch.setattr(workflow, "communities_dir", lambda: tmp_path)
    monkeypatch.setattr(workflow, "get_weather_location", lambda x: "MOCK_WEATHER_STATION")

    requirements = {"pre-2000-single": 5, "2001-2015-semi": 3, "post-2016-row-mid": 2}
    manifest_path = workflow.create_manifest("TestCommunity", requirements)

    assert manifest_path.exists()
    content = manifest_path.read_text(encoding="utf-8")

    # Validate structure and content
    assert "# TestCommunity" in content
    assert "MOCK_WEATHER_STATION" in content
    assert "### Pre-2000" in content
    assert "### 2001-2015" in content
    assert "### Post-2016" in content
    assert "Single Detached: 5" in content
    assert "Semi-Detached: 3" in content
    assert "Row House Middle: 2" in content
    assert "## Simulation Status" in content


def test_create_manifest_with_empty_requirements(monkeypatch, tmp_path):
    """Test manifest creation with empty requirements dict."""
    monkeypatch.setattr(workflow, "communities_dir", lambda: tmp_path)
    monkeypatch.setattr(workflow, "get_weather_location", lambda x: "TEST_LOCATION")

    manifest_path = workflow.create_manifest("TestCommunity", {})

    assert manifest_path.exists()
    content = manifest_path.read_text(encoding="utf-8")
    assert "Single Detached: 0" in content


# =============================================================================
# duplicate_missing_timeseries - Critical function for meeting requirements
# =============================================================================


def test_duplicate_missing_timeseries_creates_files():
    """Test that duplicate_missing_timeseries creates missing files when needed."""
    with tempfile.TemporaryDirectory() as tmpdir:
        timeseries_dir = Path(tmpdir)

        # Create one source file
        source_content = "Time,Heating,Cooling\n1,100,50\n2,110,55\n"
        source_file = timeseries_dir / "pre-2000-single_EX-0001-results_timeseries.csv"
        source_file.write_text(source_content, encoding="utf-8")

        # Request 3 files (need 2 more duplicates)
        count = workflow.duplicate_missing_timeseries(str(timeseries_dir), "pre-2000-single", 3)

        assert count == 3
        files = list(timeseries_dir.glob("pre-2000-single*-results_timeseries.csv"))
        assert len(files) == 3

        # Verify duplicates have correct naming and content
        duplicate_files = [f for f in files if "_DUPLICATE_" in f.name]
        assert len(duplicate_files) == 2
        for dup_file in duplicate_files:
            assert dup_file.read_text(encoding="utf-8") == source_content


def test_duplicate_missing_timeseries_with_sufficient_files():
    """Test that no duplicates are created when we already have enough files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        timeseries_dir = Path(tmpdir)

        # Create 3 source files
        for i in range(1, 4):
            file_path = timeseries_dir / f"pre-2000-single_EX-000{i}-results_timeseries.csv"
            file_path.write_text(f"Time,Heating\n1,{100+i}\n", encoding="utf-8")

        count = workflow.duplicate_missing_timeseries(str(timeseries_dir), "pre-2000-single", 3)

        assert count == 3
        files = list(timeseries_dir.glob("pre-2000-single*-results_timeseries.csv"))
        assert len(files) == 3

        # Verify no duplicates were created
        duplicate_files = [f for f in files if "_DUPLICATE_" in f.name]
        assert len(duplicate_files) == 0


def test_duplicate_missing_timeseries_no_source_files(capsys):
    """Test error handling when no source files exist."""
    with tempfile.TemporaryDirectory() as tmpdir:
        timeseries_dir = Path(tmpdir)

        count = workflow.duplicate_missing_timeseries(str(timeseries_dir), "pre-2000-single", 3)

        assert count == 0
        captured = capsys.readouterr()
        assert "[ERROR]" in captured.out
        assert "No source files found" in captured.out


# =============================================================================
# copy_archetype_files - Critical function for selecting and copying archetypes
# =============================================================================


def test_copy_archetype_files_validates_source_directory(monkeypatch, tmp_path):
    """Test that copy_archetype_files fails gracefully with missing source directory."""
    monkeypatch.setattr(workflow, "communities_dir", lambda: tmp_path)
    nonexistent_dir = tmp_path / "nonexistent-archetypes"
    monkeypatch.setattr(workflow, "source_archetypes_dir", lambda: nonexistent_dir)

    requirements = {"pre-2000-single": 1}

    with pytest.raises(FileNotFoundError, match="Source archetypes directory not found"):
        workflow.copy_archetype_files("TestCommunity", requirements)


def test_copy_archetype_files_applies_n_plus_20_percent_rule(monkeypatch, tmp_path):
    """Test that copy_archetype_files applies N+20% rule correctly."""
    # Setup directories
    source_dir = tmp_path / "source-archetypes"
    source_dir.mkdir()
    comm_dir = tmp_path / "communities"
    comm_dir.mkdir()

    monkeypatch.setattr(workflow, "source_archetypes_dir", lambda: source_dir)
    monkeypatch.setattr(workflow, "communities_dir", lambda: comm_dir)
    monkeypatch.setattr(workflow, "logs_dir", lambda: tmp_path / "logs")
    monkeypatch.setattr(workflow, "get_max_workers", lambda: 1)

    # Create more than enough source files
    for i in range(1, 21):
        (source_dir / f"pre-2000-single_EX-{i:04d}.H2K").write_text("test content")

    requirements = {"pre-2000-single": 10}

    # For 10 required, expect ceil(10 * 1.2) = 12 files copied
    workflow.copy_archetype_files("TestCommunity", requirements)

    copied_files = list((comm_dir / "TestCommunity" / "archetypes").glob("*.H2K"))
    assert len(copied_files) == 12, f"Expected 12 files (10 * 1.2), got {len(copied_files)}"


def test_copy_archetype_files_handles_zero_requirements(monkeypatch, tmp_path, capsys):
    """Test that copy_archetype_files skips zero-count requirements."""
    source_dir = tmp_path / "source-archetypes"
    source_dir.mkdir()
    comm_dir = tmp_path / "communities"
    comm_dir.mkdir()

    monkeypatch.setattr(workflow, "source_archetypes_dir", lambda: source_dir)
    monkeypatch.setattr(workflow, "communities_dir", lambda: comm_dir)
    monkeypatch.setattr(workflow, "logs_dir", lambda: tmp_path / "logs")

    # Create some source files
    (source_dir / "pre-2000-single_EX-0001.H2K").write_text("test")

    requirements = {"pre-2000-single": 0, "2001-2015-semi": 0}

    workflow.copy_archetype_files("TestCommunity", requirements)

    # Should create directory but no files
    archetype_dir = comm_dir / "TestCommunity" / "archetypes"
    assert archetype_dir.exists()
    copied_files = list(archetype_dir.glob("*.H2K"))
    assert len(copied_files) == 0


def test_copy_archetype_files_handles_empty_requirements(monkeypatch, tmp_path, capsys):
    """Test that copy_archetype_files handles empty requirements dict."""
    source_dir = tmp_path / "source-archetypes"
    source_dir.mkdir()
    comm_dir = tmp_path / "communities"
    comm_dir.mkdir()

    monkeypatch.setattr(workflow, "source_archetypes_dir", lambda: source_dir)
    monkeypatch.setattr(workflow, "communities_dir", lambda: comm_dir)
    monkeypatch.setattr(workflow, "logs_dir", lambda: tmp_path / "logs")

    workflow.copy_archetype_files("TestCommunity", {})

    captured = capsys.readouterr()
    assert "[WARNING] No archetype files to copy" in captured.out


def test_copy_archetype_files_warns_when_no_matching_files(monkeypatch, tmp_path, capsys):
    """Test that copy_archetype_files warns when no files match the pattern."""
    source_dir = tmp_path / "source-archetypes"
    source_dir.mkdir()
    comm_dir = tmp_path / "communities"
    comm_dir.mkdir()

    monkeypatch.setattr(workflow, "source_archetypes_dir", lambda: source_dir)
    monkeypatch.setattr(workflow, "communities_dir", lambda: comm_dir)
    monkeypatch.setattr(workflow, "logs_dir", lambda: tmp_path / "logs")
    monkeypatch.setattr(workflow, "get_max_workers", lambda: 1)

    # Create files that DON'T match the requirement pattern
    (source_dir / "2001-2015-single_EX-0001.H2K").write_text("test")

    # Request files that don't exist
    requirements = {"pre-2000-single": 5}

    workflow.copy_archetype_files("TestCommunity", requirements)

    captured = capsys.readouterr()
    assert "[WARNING] No archetype files found for 'pre-2000-single'" in captured.out


def test_copy_archetype_files_handles_insufficient_files(monkeypatch, tmp_path, capsys):
    """Test behavior when not enough source files exist to meet N+20% rule."""
    source_dir = tmp_path / "source-archetypes"
    source_dir.mkdir()
    comm_dir = tmp_path / "communities"
    comm_dir.mkdir()

    monkeypatch.setattr(workflow, "source_archetypes_dir", lambda: source_dir)
    monkeypatch.setattr(workflow, "communities_dir", lambda: comm_dir)
    monkeypatch.setattr(workflow, "logs_dir", lambda: tmp_path / "logs")
    monkeypatch.setattr(workflow, "get_max_workers", lambda: 1)

    # Create only 5 source files
    for i in range(1, 6):
        (source_dir / f"pre-2000-single_EX-{i:04d}.H2K").write_text("test content")

    # Request 10 (would need 12 with +20% rule, but only 5 exist)
    requirements = {"pre-2000-single": 10}

    workflow.copy_archetype_files("TestCommunity", requirements)

    # Should copy all 5 available files
    copied_files = list((comm_dir / "TestCommunity" / "archetypes").glob("*.H2K"))
    assert len(copied_files) == 5, f"Should copy all 5 available files, got {len(copied_files)}"


# =============================================================================
# update_weather_location - Updates HOT2000 files with correct weather data
# =============================================================================


def test_update_weather_location_with_no_files(monkeypatch, tmp_path, capsys):
    """Test that update_weather_location handles missing H2K files gracefully."""
    comm_dir = tmp_path / "communities"
    (comm_dir / "TestCommunity" / "archetypes").mkdir(parents=True)

    monkeypatch.setattr(workflow, "communities_dir", lambda: comm_dir)
    monkeypatch.setattr(workflow, "get_weather_location", lambda x: "TEST_LOCATION")

    workflow.update_weather_location("TestCommunity")

    captured = capsys.readouterr()
    assert "[WARNING]" in captured.out
    assert "No H2K files found" in captured.out


def test_update_weather_location_processes_files(monkeypatch, tmp_path, capsys):
    """Test that update_weather_location attempts to process all H2K files."""
    comm_dir = tmp_path / "communities"
    archetype_dir = comm_dir / "TestCommunity" / "archetypes"
    archetype_dir.mkdir(parents=True)

    # Create test H2K files
    for i in range(1, 4):
        (archetype_dir / f"test-{i}.H2K").write_text("dummy content")

    monkeypatch.setattr(workflow, "communities_dir", lambda: comm_dir)
    monkeypatch.setattr(workflow, "get_weather_location", lambda x: "TEST_LOCATION")
    monkeypatch.setattr(workflow, "get_max_workers", lambda: 1)

    # Mock change_weather_code to avoid actual XML processing
    # We can't easily mock update_single_weather_file due to pickling in ProcessPoolExecutor
    # So we mock the underlying change_weather_code function
    from workflow import change_weather_location_regex

    def mock_change_weather_code(file_path, location, validate=True, debug=False):
        pass  # Do nothing

    monkeypatch.setattr(
        change_weather_location_regex, "change_weather_code", mock_change_weather_code
    )

    workflow.update_weather_location("TestCommunity")

    captured = capsys.readouterr()
    # Just verify it attempted to process files
    assert "Updating weather location" in captured.out


# =============================================================================
# collect_timeseries_parallel - Gathers simulation results
# =============================================================================


def test_collect_timeseries_parallel_with_no_buildings(tmp_path):
    """Test that collect_timeseries_parallel handles empty output directory."""
    output_dir = tmp_path / "output"
    output_dir.mkdir()
    timeseries_dir = tmp_path / "timeseries"
    timeseries_dir.mkdir()

    collected = workflow.collect_timeseries_parallel(output_dir, timeseries_dir)

    assert collected == 0


def test_collect_timeseries_parallel_collects_files(tmp_path):
    """Test that collect_timeseries_parallel collects available timeseries files."""
    output_dir = tmp_path / "output"
    timeseries_dir = tmp_path / "timeseries"
    timeseries_dir.mkdir()

    # Create mock building directories with results
    for i in range(1, 4):
        building_dir = output_dir / f"pre-2000-single_EX-{i:04d}"
        run_dir = building_dir / "run"
        run_dir.mkdir(parents=True)
        (run_dir / "results_timeseries.csv").write_text(f"Time,Energy\n1,{100+i}\n")

    collected = workflow.collect_timeseries_parallel(output_dir, timeseries_dir)

    assert collected == 3
    timeseries_files = list(timeseries_dir.glob("*-results_timeseries.csv"))
    assert len(timeseries_files) == 3


def test_collect_timeseries_parallel_handles_missing_results(tmp_path):
    """Test that collect_timeseries_parallel skips buildings without results."""
    output_dir = tmp_path / "output"
    timeseries_dir = tmp_path / "timeseries"
    timeseries_dir.mkdir()

    # Create building with run directory but no results file
    building_dir = output_dir / "pre-2000-single_EX-0001"
    run_dir = building_dir / "run"
    run_dir.mkdir(parents=True)
    # No results_timeseries.csv file created

    # Create building without run directory
    (output_dir / "pre-2000-single_EX-0002").mkdir(parents=True)

    collected = workflow.collect_timeseries_parallel(output_dir, timeseries_dir)

    assert collected == 0
    timeseries_files = list(timeseries_dir.glob("*-results_timeseries.csv"))
    assert len(timeseries_files) == 0
