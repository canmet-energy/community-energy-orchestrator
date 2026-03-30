"""Unit tests for weather location regex functions."""

import tempfile
from pathlib import Path

import pytest

import workflow.change_weather_location_regex as weather

pytestmark = pytest.mark.unit


def test_get_region_for_location_valid_location():
    """Test getting region for a known location"""
    region, province_en, province_fr = weather.get_region_for_location("FORT SIMPSON")
    assert region == "12"
    assert province_en == "NORTHWEST TERRITORIES"
    assert province_fr == "TERRITOIRES DU NORD-OUEST"


def test_get_region_for_location_invalid_location():
    """Test getting region for non-existent location returns None"""
    region, province_en, province_fr = weather.get_region_for_location("NONEXISTENT")
    assert region is None
    assert province_en is None
    assert province_fr is None


def test_get_region_for_location_case_insensitive():
    """Test getting region is case-insensitive"""
    # Test lowercase
    region1, prov_en1, prov_fr1 = weather.get_region_for_location("fort simpson")
    assert region1 == "12"

    # Test mixed case
    region2, prov_en2, prov_fr2 = weather.get_region_for_location("Fort Simpson")
    assert region2 == "12"

    # Test uppercase (explicit)
    region3, prov_en3, prov_fr3 = weather.get_region_for_location("FORT SIMPSON")
    assert region3 == "12"

    # All should return same values
    assert region1 == region2 == region3
