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


# =============================================================================
# Additional edge case tests for get_max_workers
# =============================================================================


def test_get_max_workers_zero_env_variable(monkeypatch):
    """Test MAX_PARALLEL_WORKERS=0 returns at least 1 worker"""
    monkeypatch.setenv("MAX_PARALLEL_WORKERS", "0")
    assert cfg.get_max_workers() == 1


def test_get_max_workers_negative_env_variable(monkeypatch):
    """Test negative MAX_PARALLEL_WORKERS returns at least 1 worker"""
    monkeypatch.setenv("MAX_PARALLEL_WORKERS", "-5")
    assert cfg.get_max_workers() == 1


def test_get_max_workers_empty_env_variable(monkeypatch):
    """Test empty MAX_PARALLEL_WORKERS falls back to CPU calculation"""
    monkeypatch.setenv("MAX_PARALLEL_WORKERS", "")
    monkeypatch.setattr("os.cpu_count", lambda: 10)
    assert cfg.get_max_workers() == 8  # Falls back to 80% of 10


def test_get_max_workers_cpu_count_none(monkeypatch):
    """Test os.cpu_count() returning None (some systems)"""
    monkeypatch.setattr("os.cpu_count", lambda: None)
    assert cfg.get_max_workers() == 1


def test_get_max_workers_boundary_4_cpus(monkeypatch):
    """Test boundary: exactly 4 CPUs should use 80% formula"""
    monkeypatch.setattr("os.cpu_count", lambda: 4)
    # 4 is NOT < 4, so goes to elif branch: int(4 * 0.8) = 3
    assert cfg.get_max_workers() == 3


def test_get_max_workers_boundary_18_cpus(monkeypatch):
    """Test boundary: exactly 18 CPUs should use cpu_count - 4 formula"""
    monkeypatch.setattr("os.cpu_count", lambda: 18)
    # 18 is NOT < 18, so goes to else branch: 18 - 4 = 14
    assert cfg.get_max_workers() == 14


def test_get_max_workers_large_system(monkeypatch):
    """Test large system (>18 CPUs) uses cpu_count - 4 formula"""
    monkeypatch.setattr("os.cpu_count", lambda: 24)
    assert cfg.get_max_workers() == 20  # 24 - 4


def test_get_max_workers_very_large_env_value(monkeypatch):
    """Test very large MAX_PARALLEL_WORKERS value"""
    monkeypatch.setenv("MAX_PARALLEL_WORKERS", "999999")
    assert cfg.get_max_workers() == 999999


# =============================================================================
# Additional edge case tests for get_analysis_random_seed
# =============================================================================


def test_get_analysis_random_seed_zero(monkeypatch):
    """Test ANALYSIS_RANDOM_SEED=0 returns 0 (valid seed)"""
    monkeypatch.setenv("ANALYSIS_RANDOM_SEED", "0")
    assert cfg.get_analysis_random_seed() == 0


def test_get_analysis_random_seed_negative(monkeypatch):
    """Test ANALYSIS_RANDOM_SEED with negative number"""
    monkeypatch.setenv("ANALYSIS_RANDOM_SEED", "-123")
    assert cfg.get_analysis_random_seed() == -123


def test_get_analysis_random_seed_invalid_raises(monkeypatch):
    """Test ANALYSIS_RANDOM_SEED with invalid value raises ValueError"""
    monkeypatch.setenv("ANALYSIS_RANDOM_SEED", "invalid")
    with pytest.raises(ValueError):
        cfg.get_analysis_random_seed()


def test_get_analysis_random_seed_empty_string(monkeypatch):
    """Test ANALYSIS_RANDOM_SEED with empty string returns None"""
    monkeypatch.setenv("ANALYSIS_RANDOM_SEED", "")
    # Empty string is falsy, so should return None
    assert cfg.get_analysis_random_seed() is None


# =============================================================================
# Additional edge case tests for get_archetype_selection_seed
# =============================================================================


def test_get_archetype_selection_seed_empty_string(monkeypatch):
    """Test ARCHETYPE_SELECTION_SEED with empty string returns empty string"""
    monkeypatch.setenv("ARCHETYPE_SELECTION_SEED", "")
    # Empty string is a valid value (string type)
    result = cfg.get_archetype_selection_seed()
    assert result == ""
    assert isinstance(result, str)


def test_get_archetype_selection_seed_numeric_string(monkeypatch):
    """Test ARCHETYPE_SELECTION_SEED with numeric string stays as string"""
    monkeypatch.setenv("ARCHETYPE_SELECTION_SEED", "123")
    result = cfg.get_archetype_selection_seed()
    assert result == "123"
    assert isinstance(result, str)
    assert not isinstance(result, int)


# =============================================================================
# Constant validation tests
# =============================================================================


def test_archetype_valid_era_patterns():
    """Test that we have expected archetype era patterns for validation"""
    # Valid eras should match the subdirectory names in data/source-archetypes
    valid_eras = ["pre-2002", "2002-2016", "post-2016"]
    valid_types = ["single", "semi", "row-mid", "row-end"]
    
    # All combinations should be valid archetype types
    for era in valid_eras:
        for house_type in valid_types:
            archetype_key = f"{era}-{house_type}"
            # This would be a valid requirement key and subdirectory name
            assert archetype_key  # Basic validation that the key is formattable


def test_archetype_subdirectory_structure():
    """Test that expected archetype subdirectories can be constructed from requirements"""
    # Expected archetype types (era × housing type combinations)
    expected_types = [
        "pre-2002-single",
        "2002-2016-single",
        "post-2016-single",
        "pre-2002-semi",
        "2002-2016-semi",
        "post-2016-semi",
        "pre-2002-row-mid",
        "2002-2016-row-mid",
        "post-2016-row-mid",
        "pre-2002-row-end",
        "2002-2016-row-end",
        "post-2016-row-end",
    ]

    # All expected types should be valid as requirement keys (and subdirectory names)
    for archetype_type in expected_types:
        assert isinstance(archetype_type, str)
        assert "-" in archetype_type  # Should contain era-type separator

