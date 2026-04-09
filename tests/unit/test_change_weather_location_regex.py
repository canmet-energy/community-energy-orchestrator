"""Unit tests for weather location regex functions."""

import tempfile
from pathlib import Path

import pytest
import workflow.change_weather_location_regex as weather
from workflow.requirements import get_weather_region

pytestmark = pytest.mark.unit


def test_get_region_for_location_valid_location():
    """Test getting region for a known location"""
    region_info = get_weather_region("FORT SIMPSON")
    assert region_info is not None
    assert region_info["code"] == "12"
    assert region_info["english"] == "NORTHWEST TERRITORIES"
    assert region_info["french"] == "TERRITOIRES DU NORD-OUEST"


def test_get_region_for_location_invalid_location():
    """Test getting region for non-existent location returns None"""
    region_info = get_weather_region("NONEXISTENT")
    assert region_info is None


def test_get_region_for_location_case_insensitive():
    """Test getting region is case-insensitive"""
    # Test lowercase
    region1 = get_weather_region("fort simpson")
    assert region1["code"] == "12"

    # Test mixed case
    region2 = get_weather_region("Fort Simpson")
    assert region2["code"] == "12"

    # Test uppercase (explicit)
    region3 = get_weather_region("FORT SIMPSON")
    assert region3["code"] == "12"

    # All should return same values
    assert region1 == region2 == region3
