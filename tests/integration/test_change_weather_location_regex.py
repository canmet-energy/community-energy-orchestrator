"""Integration tests for change_weather_code function."""

import tempfile
from pathlib import Path

import pytest

import workflow.change_weather_location_regex as weather

pytestmark = pytest.mark.integration


# Sample H2K file content with Weather section
SAMPLE_H2K_CONTENT = """<?xml version="1.0" encoding="UTF-8"?>
<HouseFile>
    <ProgramInformation>
        <Weather depthOfFrost="1.2192" heatingDegreeDay="5000" library="SOME_LOCATION.wth">
            <Region code="1">
                <English>BRITISH COLUMBIA</English>
                <French>COLOMBIE-BRITANNIQUE</French>
            </Region>
            <Location code="100">
                <English>OLD LOCATION</English>
                <French>OLD LOCATION</French>
            </Location>
        </Weather>
    </ProgramInformation>
</HouseFile>"""


def test_change_weather_code_success(tmp_path):
    """Test successfully changing weather location in H2K file using real CSV files."""
    # Create test H2K file
    h2k_file = tmp_path / "test.h2k"
    h2k_file.write_text(SAMPLE_H2K_CONTENT, encoding="utf-8")

    # Change weather location (uses real CSV files from project)
    result = weather.change_weather_code(h2k_file, location="FORT SIMPSON", debug=False)

    # Should return True (changes were made)
    assert result is True

    # Verify file was modified
    content = h2k_file.read_text(encoding="utf-8")
    assert "FORT SIMPSON" in content
    assert "NORTHWEST TERRITORIES" in content
    assert "TERRITOIRES DU NORD-OUEST" in content
    assert 'code="12"' in content  # Region code


def test_change_weather_code_nonexistent_file():
    """Test changing weather code with non-existent file raises error."""
    with pytest.raises(FileNotFoundError):
        weather.change_weather_code("/nonexistent/file.h2k", location="FORT SIMPSON")


def test_change_weather_code_non_xml_file(tmp_path):
    """Test changing weather code with non-XML file returns False."""
    # Create non-XML file
    text_file = tmp_path / "test.h2k"
    text_file.write_text("This is not XML content", encoding="utf-8")

    result = weather.change_weather_code(text_file, location="FORT SIMPSON", debug=False)

    # Should return False (not valid XML)
    assert result is False


def test_change_weather_code_no_weather_section(tmp_path):
    """Test file with no Weather section returns False."""
    # Create H2K file without Weather section
    h2k_content = """<?xml version="1.0" encoding="UTF-8"?>
<HouseFile>
    <ProgramInformation>
        <SomeOtherElement>Data</SomeOtherElement>
    </ProgramInformation>
</HouseFile>"""

    h2k_file = tmp_path / "test.h2k"
    h2k_file.write_text(h2k_content, encoding="utf-8")

    result = weather.change_weather_code(h2k_file, location="FORT SIMPSON", debug=False)

    # Should return False (no Weather section to replace)
    assert result is False


def test_change_weather_code_invalid_location(tmp_path, capsys):
    """Test changing to invalid location returns False."""
    h2k_file = tmp_path / "test.h2k"
    h2k_file.write_text(SAMPLE_H2K_CONTENT, encoding="utf-8")

    result = weather.change_weather_code(h2k_file, location="NONEXISTENT_PLACE", debug=False)

    # Should return False
    assert result is False

    # Should print error message
    captured = capsys.readouterr()
    assert "not found" in captured.out.lower()


def test_change_weather_code_missing_location_csv(tmp_path, monkeypatch, capsys):
    """Test missing location_code.csv returns False and prints error."""
    # Create empty csv dir with only weather_details.csv
    csv_dir = tmp_path / "csv"
    csv_dir.mkdir()

    weather_details = csv_dir / "weather_details.csv"
    weather_details.write_text(
        "Location,HDD,Library\nFORT SIMPSON,6500,FORT SIMPSON.wth\n", encoding="utf-8"
    )

    monkeypatch.setattr(weather, "csv_dir", lambda: csv_dir)

    h2k_file = tmp_path / "test.h2k"
    h2k_file.write_text(SAMPLE_H2K_CONTENT, encoding="utf-8")

    # Should return False (error caught internally)
    result = weather.change_weather_code(h2k_file, location="FORT SIMPSON")
    assert result is False

    # Should print error message
    captured = capsys.readouterr()
    assert "location_code" in captured.out.lower()


def test_change_weather_code_missing_weather_details_csv(tmp_path, monkeypatch, capsys):
    """Test missing weather_details.csv returns False and prints error."""
    # Create empty csv dir with only location_code.csv
    csv_dir = tmp_path / "csv"
    csv_dir.mkdir()

    location_codes = csv_dir / "location_code.csv"
    location_codes.write_text("FORT SIMPSON,400\n", encoding="utf-8")

    monkeypatch.setattr(weather, "csv_dir", lambda: csv_dir)

    h2k_file = tmp_path / "test.h2k"
    h2k_file.write_text(SAMPLE_H2K_CONTENT, encoding="utf-8")

    # Should return False (error caught internally)
    result = weather.change_weather_code(h2k_file, location="FORT SIMPSON")
    assert result is False

    # Should print error message
    captured = capsys.readouterr()
    assert "weather_details" in captured.out.lower()


def test_change_weather_code_location_not_in_region_map(tmp_path, monkeypatch, capsys):
    """Test location exists in CSVs but not in region map."""
    # Create temporary CSV directory with a fake location
    csv_dir = tmp_path / "csv"
    csv_dir.mkdir()

    location_codes = csv_dir / "location_code.csv"
    location_codes.write_text("FORT SIMPSON,400\n" "FAKE_LOCATION,999\n", encoding="utf-8")

    weather_details = csv_dir / "weather_details.csv"
    weather_details.write_text(
        "Location,HDD,Library\n"
        "FORT SIMPSON,6500,FORT SIMPSON.wth\n"
        "FAKE_LOCATION,5000,FAKE.wth\n",
        encoding="utf-8",
    )

    # Mock csv_dir() to return our temporary directory
    monkeypatch.setattr("workflow.change_weather_location_regex.csv_dir", lambda: csv_dir)

    h2k_file = tmp_path / "test.h2k"
    h2k_file.write_text(SAMPLE_H2K_CONTENT, encoding="utf-8")

    result = weather.change_weather_code(h2k_file, location="FAKE_LOCATION", debug=False)

    # Should return False
    assert result is False

    # Should print error about region
    captured = capsys.readouterr()
    assert "region" in captured.out.lower()


def test_change_weather_code_preserves_encoding(tmp_path):
    """Test that special characters in location names are preserved."""
    # Use DÉLINE which has special character (uses real CSV files)
    h2k_file = tmp_path / "test.h2k"
    h2k_file.write_text(SAMPLE_H2K_CONTENT, encoding="utf-8")

    result = weather.change_weather_code(h2k_file, location="DÉLINE", debug=False)

    assert result is True

    # Read back and verify special character preserved
    content = h2k_file.read_text(encoding="utf-8")
    assert "DÉLINE" in content


def test_change_weather_code_idempotent(tmp_path):
    """Test that running twice doesn't modify file second time."""
    h2k_file = tmp_path / "test.h2k"
    h2k_file.write_text(SAMPLE_H2K_CONTENT, encoding="utf-8")

    # First change
    result1 = weather.change_weather_code(h2k_file, location="FORT SIMPSON", debug=False)
    assert result1 is True

    content_after_first = h2k_file.read_text(encoding="utf-8")

    # Second change (same location)
    result2 = weather.change_weather_code(h2k_file, location="FORT SIMPSON", debug=False)
    assert result2 is False  # No changes needed

    content_after_second = h2k_file.read_text(encoding="utf-8")

    # Content should be identical
    assert content_after_first == content_after_second


def test_change_weather_code_debug_mode(tmp_path, capsys):
    """Test that debug mode prints information."""
    h2k_file = tmp_path / "test.h2k"
    h2k_file.write_text(SAMPLE_H2K_CONTENT, encoding="utf-8")

    result = weather.change_weather_code(h2k_file, location="IQALUIT", debug=True)

    assert result is True

    # Verify debug output
    captured = capsys.readouterr()
    assert "Found location" in captured.out or "IQALUIT" in captured.out
    assert "Successfully updated" in captured.out
