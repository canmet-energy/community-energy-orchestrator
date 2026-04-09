import re

import pytest

import workflow.requirements as req

pytestmark = pytest.mark.unit


def test_get_community_requirements(sample_data):
    """Test that get_community_requirements returns valid housing type data.

    Validates:
    - Returns a dict with data for an existing community
    - All keys follow exact format: "{era}-{type}"
    - All values are non-negative integers
    - Keys use only valid eras and types
    """
    requirements = req.get_community_requirements(sample_data["community_name"])
    assert isinstance(requirements, dict), "Requirements should be a dict"
    assert requirements != {}, "Expected non-empty requirements for the community"

    # Define valid patterns for strict validation
    valid_eras = ["pre-2002", "2002-2016", "post-2016"]
    valid_types = ["single", "semi", "row-mid", "row-end"]

    # Compile regex for strict format validation: "era-type" (nothing before or after)
    # Pattern: ^(era1|era2|era3)-(type1|type2|type3|type4)$
    era_pattern = "|".join(re.escape(era) for era in valid_eras)
    type_pattern = "|".join(re.escape(t) for t in valid_types)
    key_regex = re.compile(f"^({era_pattern})-({type_pattern})$")

    for key, value in requirements.items():
        # Strictly validate key format (must be exactly "era-type")
        assert key_regex.match(key), (
            f"Key '{key}' does not match expected format 'era-type'. "
            f"Valid eras: {valid_eras}, Valid types: {valid_types}"
        )

        # Validate value is a non-negative integer
        assert isinstance(value, int), f"Value for key '{key}' is not an integer: {type(value)}"
        assert value >= 0, f"Value for key '{key}' is negative: {value}"


def test_get_community_requirements_invalid_community():
    """Test graceful fallback for non-existent community."""
    requirements = req.get_community_requirements("NonExistentCommunity")
    assert requirements == {}, "Expected empty requirements for a non-existent community"


def test_get_community_requirements_empty_string():
    """Test that empty string community name returns empty dict."""
    requirements = req.get_community_requirements("")
    assert requirements == {}, "Expected empty dict for empty string community name"


def test_get_community_requirements_whitespace_only():
    """Test that whitespace-only community name returns empty dict."""
    requirements = req.get_community_requirements("   ")
    assert requirements == {}, "Expected empty dict for whitespace-only community name"


def test_get_community_requirements_case_insensitive():
    """Test that community name lookup is case-insensitive."""
    req1 = req.get_community_requirements("Norman's Bay")
    req2 = req.get_community_requirements("NORMAN'S BAY")
    assert req1 == req2, "Expected case-insensitive community names to return the same requirements"

    # Also verify both return the same type (both dict, not one None)
    assert isinstance(req1, dict), "First result should be a dict"
    assert isinstance(req2, dict), "Second result should be a dict"


def test_get_weather_location(sample_data):
    """Test that get_weather_location returns a valid location string."""
    location = req.get_weather_location(sample_data["community_name"])
    assert isinstance(location, str), "Weather location should be a string"
    assert location != "", "Expected a non-empty weather location string"
    assert (
        location.strip() == location
    ), "Weather location should not have leading/trailing whitespace"


def test_get_weather_location_invalid_community():
    """Test graceful fallback for non-existent community."""
    location = req.get_weather_location("NonExistentCommunity")
    assert location == "", "Expected empty string for non-existent community weather location"


def test_get_weather_location_empty_string():
    """Test that empty string community name returns empty string."""
    location = req.get_weather_location("")
    assert location == "", "Expected empty string for empty community name"


def test_get_weather_location_whitespace_only():
    """Test that whitespace-only community name returns empty string."""
    location = req.get_weather_location("   ")
    assert location == "", "Expected empty string for whitespace-only community name"


def test_get_weather_location_case_insensitive():
    """Test that community name lookup is case-insensitive."""
    loc1 = req.get_weather_location("Norman's Bay")
    loc2 = req.get_weather_location("NORMAN'S BAY")
    assert (
        loc1 == loc2
    ), "Expected case-insensitive community names to return the same weather location"

    # Also verify both return strings
    assert isinstance(loc1, str), "First result should be a string"
    assert isinstance(loc2, str), "Second result should be a string"


def test_get_community_requirements_missing_json_raises_error(monkeypatch, tmp_path):
    """Test that missing JSON file raises FileNotFoundError.

    This validates error handling when the communities JSON is not found,
    which could happen if the file is deleted or the path is misconfigured.

    Note: Uses monkeypatch to patch where json_dir is USED (in workflow.requirements),
    not where it's defined (in workflow.paths).
    """
    import workflow.requirements

    # Point to non-existent directory - patch where it's used, not where it's defined
    monkeypatch.setattr(workflow.requirements, "json_dir", lambda: tmp_path / "nonexistent")

    with pytest.raises(FileNotFoundError, match="Communities JSON not found"):
        req.get_community_requirements("TestCommunity")


def test_get_weather_location_missing_json_raises_error(monkeypatch, tmp_path):
    """Test that missing JSON file raises FileNotFoundError.

    This validates error handling when the communities JSON is not found,
    which could happen if the file is deleted or the path is misconfigured.

    Note: Uses monkeypatch to patch where json_dir is USED (in workflow.requirements),
    not where it's defined (in workflow.paths).
    """
    import workflow.requirements

    # Point to non-existent directory - patch where it's used, not where it's defined
    monkeypatch.setattr(workflow.requirements, "json_dir", lambda: tmp_path / "nonexistent")

    with pytest.raises(FileNotFoundError, match="Communities JSON not found"):
        req.get_weather_location("TestCommunity")

