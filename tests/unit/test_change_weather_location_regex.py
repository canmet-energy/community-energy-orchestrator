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


def test_load_csv_data_valid_file():
    """Test loading CSV file with valid data"""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False, encoding="utf-8") as f:
        f.write("FORT SIMPSON,400\n")
        f.write("IQALUIT,601\n")
        temp_path = f.name

    try:
        data = weather.load_csv_data(temp_path)
        assert data["FORT SIMPSON"] == "400"
        assert data["IQALUIT"] == "601"
    finally:
        Path(temp_path).unlink()


def test_load_csv_data_with_empty_lines():
    """Test loading CSV file skips empty lines"""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False, encoding="utf-8") as f:
        f.write("FORT SIMPSON,400\n")
        f.write("\n")  # empty line
        f.write("IQALUIT,601\n")
        temp_path = f.name

    try:
        data = weather.load_csv_data(temp_path)
        assert len(data) == 2
        assert data["FORT SIMPSON"] == "400"
    finally:
        Path(temp_path).unlink()


def test_load_csv_data_nonexistent_file():
    """Test loading non-existent CSV file raises FileNotFoundError"""
    with pytest.raises(FileNotFoundError):
        weather.load_csv_data("/nonexistent/path/to/file.csv")


def test_load_csv_data_partial_lines():
    """Test loading CSV with lines that have less than 2 parts"""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False, encoding="utf-8") as f:
        f.write("FORT SIMPSON,400\n")
        f.write("INCOMPLETE\n")  # Missing value
        f.write("IQALUIT,601\n")
        temp_path = f.name

    try:
        data = weather.load_csv_data(temp_path)
        assert "FORT SIMPSON" in data
        assert "IQALUIT" in data
        # Incomplete line should be skipped
        assert "INCOMPLETE" not in data
    finally:
        Path(temp_path).unlink()
