"""Unit tests for core path utilities."""

from pathlib import Path

import pytest

import workflow.core as core

pytestmark = pytest.mark.unit


def test_project_root_returns_path():
    """Test that project_root returns a valid Path object"""
    root = core.project_root()
    assert isinstance(root, Path)
    assert root.exists()


def test_communities_dir_returns_path():
    """Test that communities_dir returns valid path"""
    comm_dir = core.communities_dir()
    assert isinstance(comm_dir, Path)
    assert comm_dir.name == "communities"


def test_csv_dir_returns_path():
    """Test that csv_dir returns valid path"""
    csv_path = core.csv_dir()
    assert isinstance(csv_path, Path)
    assert csv_path.name == "csv"
    assert csv_path.exists()


def test_logs_dir_returns_path():
    """Test that logs_dir returns valid path"""
    log_path = core.logs_dir()
    assert isinstance(log_path, Path)
    assert log_path.name == "logs"


def test_source_archetypes_dir_returns_path():
    """Test that source_archetypes_dir returns valid path"""
    arch_path = core.source_archetypes_dir()
    assert isinstance(arch_path, Path)
    assert arch_path.name == "source-archetypes"
