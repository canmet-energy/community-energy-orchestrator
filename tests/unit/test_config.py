import os
import pytest
import workflow.config as cfg

pytestmark = pytest.mark.unit


def test_get_max_workers_default():
    """Test that get_max_workers returns a positive integer"""
    workers = cfg.get_max_workers()
    assert isinstance(workers, int)
    assert workers > 0, "Expected at least 1 worker"


def test_get_max_workers_with_env_variable(monkeypatch):
    """Test MAX_PARALLEL_WORKERS env variable behavior"""
    # Valid env variable overrides default
    monkeypatch.setenv("MAX_PARALLEL_WORKERS", "4")
    assert cfg.get_max_workers() == 4

    # Invalid env variable falls back to default logic
    monkeypatch.setenv("MAX_PARALLEL_WORKERS", "invalid")
    workers = cfg.get_max_workers()
    assert isinstance(workers, int)
    assert workers > 0


def test_get_max_workers_cpu_scaling(monkeypatch):
    """Test that worker count scales based on CPU count"""
    # Test small system
    monkeypatch.setattr("os.cpu_count", lambda: 2)
    assert cfg.get_max_workers() == 1

    # Test medium system
    monkeypatch.setattr("os.cpu_count", lambda: 10)
    assert cfg.get_max_workers() == 8  # 80% of 10


def test_get_analysis_random_seed(monkeypatch):
    """Test ANALYSIS_RANDOM_SEED env variable behavior"""
    # Returns None when not set
    seed = cfg.get_analysis_random_seed()
    assert seed is None

    # Returns integer when set
    monkeypatch.setenv("ANALYSIS_RANDOM_SEED", "42")
    seed = cfg.get_analysis_random_seed()
    assert seed == 42
    assert isinstance(seed, int)


def test_get_archetype_selection_seed(monkeypatch):
    """Test ARCHETYPE_SELECTION_SEED env variable behavior"""
    # Returns None when not set
    seed = cfg.get_archetype_selection_seed()
    assert seed is None

    # Returns string when set
    monkeypatch.setenv("ARCHETYPE_SELECTION_SEED", "test-seed-123")
    seed = cfg.get_archetype_selection_seed()
    assert seed == "test-seed-123"
    assert isinstance(seed, str)
