import pytest
import workflow.requirements as req

pytestmark = pytest.mark.unit


def test_get_community_requirements(sample_data):
    requirements = req.get_community_requirements(sample_data["community_name"])
    assert isinstance(requirements, dict)
    assert requirements != {}, "Expected non-empty requirements for the community"
    valid_eras = ["pre-2000", "2001-2015", "post-2016"]
    valid_types = ["single", "semi", "row-mid", "row-end"]

    for key, value in requirements.items():
        # Check for era in key
        assert any(era in key for era in valid_eras), f"Key '{key}' does not contain a valid era"

        # Check for type in key
        assert any(t in key for t in valid_types), f"Key '{key}' does not contain a valid type"

        # Check that value is an int
        assert isinstance(value, int), f"Value for key '{key}' is not an integer"

        # Check value is non-negative
        assert value >= 0, f"Value for key '{key}' is negative"


def test_get_community_requirements_invalid_community():
    requirements = req.get_community_requirements("NonExistentCommunity")
    assert requirements == {}, "Expected empty requirements for a non-existent community"


def test_get_community_requirements_case_insensitive():
    req1 = req.get_community_requirements("Norman's Bay")
    req2 = req.get_community_requirements("NORMAN'S BAY")
    assert req1 == req2, "Expected case-insensitive community names to return the same requirements"


def test_get_weather_location(sample_data):
    location = req.get_weather_location(sample_data["community_name"])
    assert isinstance(location, str)
    assert location != "", "Expected a non-empty weather location string"


def test_get_weather_location_invalid_community():
    location = req.get_weather_location("NonExistentCommunity")
    assert location == "", "Expected empty string for non-existent community weather location"


def test_get_weather_location_case_insensitive():
    loc1 = req.get_weather_location("Norman's Bay")
    loc2 = req.get_weather_location("NORMAN'S BAY")
    assert (
        loc1 == loc2
    ), "Expected case-insensitive community names to return the same weather location"
