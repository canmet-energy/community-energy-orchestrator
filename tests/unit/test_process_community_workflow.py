"""Unit tests for workflow processing functions."""

import tempfile
from pathlib import Path

import pytest

import workflow.core as core
import workflow.process_community_workflow as workflow

pytestmark = pytest.mark.unit


def test_create_manifest_includes_requirements():
    """Test that manifest file contains requirements data"""
    with tempfile.TemporaryDirectory() as tmpdir:
        base_path = Path(tmpdir)
        # Create archetypes directory
        archetypes_dir = base_path / "TestCommunity" / "archetypes"
        archetypes_dir.mkdir(parents=True, exist_ok=True)

        requirements = {"pre-2000-single": 5, "2001-2015-semi": 3, "post-2016-row-mid": 2}

        # Temporarily change communities_dir for this test
        original_communities_dir = core.communities_dir
        core.communities_dir = lambda: base_path

        try:
            manifest_path = workflow.create_manifest("TestCommunity", requirements)
            assert manifest_path.exists()

            content = manifest_path.read_text(encoding="utf-8")
            assert "TestCommunity" in content
            assert "Pre-2000" in content
            assert "Single Detached: 5" in content
        finally:
            core.communities_dir = original_communities_dir


def test_duplicate_missing_timeseries_creates_files():
    """Test that duplicate_missing_timeseries creates missing files"""
    with tempfile.TemporaryDirectory() as tmpdir:
        timeseries_dir = Path(tmpdir)

        # Create one source file
        source_file = timeseries_dir / "pre-2000-single_EX-0001-results_timeseries.csv"
        source_file.write_text("Time,Heating\n1,100\n", encoding="utf-8")

        # Request 3 files (need 2 more)
        count = workflow.duplicate_missing_timeseries(str(timeseries_dir), "pre-2000-single", 3)

        assert count == 3
        files = list(timeseries_dir.glob("pre-2000-single*-results_timeseries.csv"))
        assert len(files) == 3


def test_duplicate_missing_timeseries_no_source_files():
    """Test duplicate_missing_timeseries when no source files exist"""
    with tempfile.TemporaryDirectory() as tmpdir:
        timeseries_dir = Path(tmpdir)

        count = workflow.duplicate_missing_timeseries(str(timeseries_dir), "pre-2000-single", 3)

        # Should return 0 when no source files
        assert count == 0


def test_create_community_directories_structure():
    """Test that create_community_directories creates expected structure"""
    with tempfile.TemporaryDirectory() as tmpdir:
        original_communities_dir = core.communities_dir
        core.communities_dir = lambda: Path(tmpdir)

        try:
            base_path = workflow.create_community_directories("TestCommunity")

            assert base_path.exists()
            assert (base_path / "archetypes").exists()
            assert (base_path / "timeseries").exists()
            assert (base_path / "analysis").exists()
        finally:
            core.communities_dir = original_communities_dir
