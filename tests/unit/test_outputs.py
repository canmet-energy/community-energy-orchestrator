"""Unit tests for workflow outputs module."""

import io
import tempfile
import zipfile
from pathlib import Path

import pytest

import workflow.outputs as outputs

pytestmark = pytest.mark.unit


@pytest.fixture
def mock_community_structure(tmp_path, monkeypatch):
    """Create a mock community directory structure for testing."""
    # Create a temporary communities directory
    communities_dir = tmp_path / "communities"
    communities_dir.mkdir()

    # Mock the communities_dir function
    monkeypatch.setattr("workflow.outputs.communities_dir", lambda: communities_dir)

    # Create a sample community with expected structure
    community_name = "TestCommunity"
    community_dir = communities_dir / community_name
    analysis_dir = community_dir / "analysis"
    timeseries_dir = community_dir / "timeseries"

    analysis_dir.mkdir(parents=True)
    timeseries_dir.mkdir(parents=True)

    # Create sample output files
    (analysis_dir / f"{community_name}-community_total.csv").write_text("Total,1000\n")
    (analysis_dir / f"{community_name}_analysis.md").write_text("# Analysis\n")
    (timeseries_dir / "dwelling1-results_timeseries.csv").write_text("Time,Energy\n0,100\n")
    (timeseries_dir / "dwelling2-results_timeseries.csv").write_text("Time,Energy\n0,200\n")

    return {"community_name": community_name, "base_dir": communities_dir}


def test_get_community_total_path(mock_community_structure):
    """Test retrieving the community total CSV path."""
    community_name = mock_community_structure["community_name"]
    path = outputs.get_community_total_path(community_name)

    assert path.exists(), "Community total file should exist"
    assert path.name == f"{community_name}-community_total.csv"
    assert "analysis" in path.parts


def test_get_community_total_path_not_found(mock_community_structure):
    """Test error when community total file doesn't exist."""
    with pytest.raises(FileNotFoundError):
        outputs.get_community_total_path("NonExistentCommunity")


def test_get_analysis_markdown_path(mock_community_structure):
    """Test retrieving the analysis markdown path."""
    community_name = mock_community_structure["community_name"]
    path = outputs.get_analysis_markdown_path(community_name)

    assert path.exists(), "Analysis markdown should exist"
    assert path.name == f"{community_name}_analysis.md"
    assert "analysis" in path.parts


def test_get_analysis_markdown_path_not_found(mock_community_structure):
    """Test error when analysis markdown doesn't exist."""
    with pytest.raises(FileNotFoundError):
        outputs.get_analysis_markdown_path("NonExistentCommunity")


def test_get_timeseries_files(mock_community_structure):
    """Test retrieving timeseries CSV files."""
    community_name = mock_community_structure["community_name"]
    files = outputs.get_timeseries_files(community_name)

    assert len(files) == 2, "Should find 2 timeseries files"
    assert all(f.suffix == ".csv" for f in files), "All files should be CSV"
    assert all("timeseries" in str(f) for f in files), "All files should be in timeseries dir"


def test_get_timeseries_files_not_found(mock_community_structure):
    """Test error when no timeseries files exist."""
    with pytest.raises(FileNotFoundError):
        outputs.get_timeseries_files("NonExistentCommunity")


def test_create_timeseries_zip(mock_community_structure):
    """Test creating a ZIP archive of timeseries files."""
    community_name = mock_community_structure["community_name"]
    zip_buffer = outputs.create_timeseries_zip(community_name)

    assert isinstance(zip_buffer, io.BytesIO), "Should return BytesIO buffer"
    assert zip_buffer.tell() == 0, "Buffer should be at start position"

    # Verify ZIP contents
    with zipfile.ZipFile(zip_buffer, "r") as zip_file:
        names = zip_file.namelist()
        assert len(names) == 2, "ZIP should contain 2 files"
        assert all(name.endswith("-results_timeseries.csv") for name in names)


def test_create_timeseries_zip_not_found(mock_community_structure):
    """Test error when creating ZIP for non-existent community."""
    with pytest.raises(FileNotFoundError):
        outputs.create_timeseries_zip("NonExistentCommunity")

