"""Unit tests for debug and validation functions."""

import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

import workflow.debug_outputs as debug

pytestmark = pytest.mark.unit


# =============================================================================
# get_location_code_from_h2k tests
# =============================================================================


def test_get_location_code_from_h2k_valid_xml():
    """Test extracting location code from valid XML with proper structure."""
    xml_content = """<?xml version="1.0"?>
<Root>
    <H2K>
        <Weather>
            <Location code="400"/>
        </Weather>
    </H2K>
</Root>"""

    with tempfile.NamedTemporaryFile(mode="w", suffix=".h2k", delete=False, encoding="utf-8") as f:
        f.write(xml_content)
        temp_path = f.name

    try:
        code = debug.get_location_code_from_h2k(temp_path)
        assert code == "400"
    finally:
        Path(temp_path).unlink()


def test_get_location_code_from_h2k_missing_location():
    """Test extracting from XML missing Location element returns None."""
    xml_content = """<?xml version="1.0"?>
<H2K>
    <Weather>
    </Weather>
</H2K>"""

    with tempfile.NamedTemporaryFile(mode="w", suffix=".h2k", delete=False, encoding="utf-8") as f:
        f.write(xml_content)
        temp_path = f.name

    try:
        code = debug.get_location_code_from_h2k(temp_path)
        assert code is None
    finally:
        Path(temp_path).unlink()


def test_get_location_code_from_h2k_missing_weather():
    """Test extracting from XML missing Weather element returns None."""
    xml_content = """<?xml version="1.0"?>
<H2K>
    <SomeOtherElement/>
</H2K>"""

    with tempfile.NamedTemporaryFile(mode="w", suffix=".h2k", delete=False, encoding="utf-8") as f:
        f.write(xml_content)
        temp_path = f.name

    try:
        code = debug.get_location_code_from_h2k(temp_path)
        assert code is None
    finally:
        Path(temp_path).unlink()


def test_get_location_code_from_h2k_malformed_xml():
    """Test extracting from malformed XML returns None."""
    xml_content = """<?xml version="1.0"?>
<H2K>
    <Weather>
        <Location code="400"
    </Weather>
</H2K>"""  # Missing closing bracket and tag

    with tempfile.NamedTemporaryFile(mode="w", suffix=".h2k", delete=False, encoding="utf-8") as f:
        f.write(xml_content)
        temp_path = f.name

    try:
        code = debug.get_location_code_from_h2k(temp_path)
        assert code is None
    finally:
        Path(temp_path).unlink()


def test_get_location_code_from_h2k_encoding_fallback():
    """Test that function tries multiple encodings."""
    # Create content with Latin-1 specific character
    xml_content = """<?xml version="1.0" encoding="utf-8"?>
<H2K>
    <Weather>
        <Location code="400"/>
    </Weather>
</H2K>"""

    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".h2k", delete=False, encoding="latin-1"
    ) as f:
        f.write(xml_content)
        temp_path = f.name

    try:
        # Should still extract code even with encoding mismatch
        code = debug.get_location_code_from_h2k(temp_path)
        assert code == "400"
    finally:
        Path(temp_path).unlink()


def test_get_location_code_from_h2k_nonexistent_file():
    """Test extracting from non-existent file raises FileNotFoundError."""
    with pytest.raises(FileNotFoundError):
        debug.get_location_code_from_h2k("/nonexistent/path/file.h2k")


# =============================================================================
# validate_location_code tests
# =============================================================================


def test_validate_location_code_with_none():
    """Test validate_location_code returns False when code is None."""
    result = debug.validate_location_code("Ogoki", None)
    assert result is False


def test_validate_location_code_matching(monkeypatch, tmp_path):
    """Test validate_location_code returns True when codes match."""
    # Create mock CSV files
    weather_csv = tmp_path / "communities-hdd-and-weather-location.csv"
    weather_csv.write_text(
        "Community,WEATHER\nTestCommunity,TestWeatherStation\n", encoding="utf-8"
    )

    location_csv = tmp_path / "location_code.csv"
    location_csv.write_text("Location,Code\nTESTWEATHERSTATION,400\n", encoding="utf-8")

    # Mock csv_dir to return our tmp_path
    monkeypatch.setattr(debug, "csv_dir", lambda: tmp_path)

    # Mock load_csv_data to return our location code mapping
    def mock_load_csv_data(path):
        return {"TESTWEATHERSTATION": "400"}

    monkeypatch.setattr("workflow.debug_outputs.load_csv_data", mock_load_csv_data)

    # Test with matching code
    result = debug.validate_location_code("TestCommunity", "400")
    assert result is True


def test_validate_location_code_mismatch(monkeypatch, tmp_path):
    """Test validate_location_code returns False when codes don't match."""
    weather_csv = tmp_path / "communities-hdd-and-weather-location.csv"
    weather_csv.write_text(
        "Community,WEATHER\nTestCommunity,TestWeatherStation\n", encoding="utf-8"
    )

    location_csv = tmp_path / "location_code.csv"
    location_csv.write_text("Location,Code\nTESTWEATHERSTATION,400\n", encoding="utf-8")

    monkeypatch.setattr(debug, "csv_dir", lambda: tmp_path)

    def mock_load_csv_data(path):
        return {"TESTWEATHERSTATION": "400"}

    monkeypatch.setattr("workflow.debug_outputs.load_csv_data", mock_load_csv_data)

    # Test with wrong code
    result = debug.validate_location_code("TestCommunity", "999")
    assert result is False


def test_validate_location_code_community_not_found(monkeypatch, tmp_path):
    """Test validate_location_code returns False when community not in CSV."""
    weather_csv = tmp_path / "communities-hdd-and-weather-location.csv"
    weather_csv.write_text("Community,WEATHER\nOtherCommunity,SomeStation\n", encoding="utf-8")

    monkeypatch.setattr(debug, "csv_dir", lambda: tmp_path)

    result = debug.validate_location_code("NonExistentCommunity", "400")
    assert result is False


def test_validate_location_code_missing_weather_csv(monkeypatch, tmp_path):
    """Test validate_location_code returns False when CSV file doesn't exist."""
    # Point to directory without the CSV file
    monkeypatch.setattr(debug, "csv_dir", lambda: tmp_path)

    result = debug.validate_location_code("TestCommunity", "400")
    assert result is False


def test_validate_location_code_missing_location_csv(monkeypatch, tmp_path):
    """Test validate_location_code returns False when location_code.csv doesn't exist."""
    # Create only the weather CSV, not the location CSV
    weather_csv = tmp_path / "communities-hdd-and-weather-location.csv"
    weather_csv.write_text(
        "Community,WEATHER\nTestCommunity,TestWeatherStation\n", encoding="utf-8"
    )

    monkeypatch.setattr(debug, "csv_dir", lambda: tmp_path)

    result = debug.validate_location_code("TestCommunity", "400")
    assert result is False


def test_validate_location_code_case_insensitive(monkeypatch, tmp_path):
    """Test validate_location_code handles community names case-insensitively."""
    weather_csv = tmp_path / "communities-hdd-and-weather-location.csv"
    weather_csv.write_text(
        "Community,WEATHER\nTESTCOMMUNITY,TestWeatherStation\n", encoding="utf-8"
    )

    location_csv = tmp_path / "location_code.csv"
    location_csv.write_text("Location,Code\nTESTWEATHERSTATION,400\n", encoding="utf-8")

    monkeypatch.setattr(debug, "csv_dir", lambda: tmp_path)

    def mock_load_csv_data(path):
        return {"TESTWEATHERSTATION": "400"}

    monkeypatch.setattr("workflow.debug_outputs.load_csv_data", mock_load_csv_data)

    # Test with lowercase community name (CSV has uppercase)
    result = debug.validate_location_code("testcommunity", "400")
    assert result is True


# =============================================================================
# _validate_single_h2k tests
# =============================================================================


def test_validate_single_h2k_valid_file(monkeypatch, tmp_path):
    """Test _validate_single_h2k returns success for valid file with matching code."""
    xml_content = """<?xml version="1.0"?>
<H2K>
    <Weather>
        <Location code="400"/>
    </Weather>
</H2K>"""

    h2k_file = tmp_path / "test.h2k"
    h2k_file.write_text(xml_content, encoding="utf-8")

    # Mock validate_location_code to return True
    monkeypatch.setattr(debug, "validate_location_code", lambda comm, code: True)

    file_path, error_msg, location_code = debug._validate_single_h2k(h2k_file, "TestCommunity")

    assert file_path == h2k_file
    assert error_msg is None, "Should return None for successful validation"
    assert location_code == "400"


def test_validate_single_h2k_non_xml_file(tmp_path):
    """Test _validate_single_h2k detects non-XML files."""
    h2k_file = tmp_path / "test.h2k"
    h2k_file.write_text("This is not XML content\nJust plain text", encoding="latin-1")

    file_path, error_msg, location_code = debug._validate_single_h2k(h2k_file, "TestCommunity")

    assert file_path == h2k_file
    assert error_msg == "Not an XML H2K file."
    assert location_code is None


def test_validate_single_h2k_missing_location_code(monkeypatch, tmp_path):
    """Test _validate_single_h2k handles missing location code."""
    xml_content = """<?xml version="1.0"?>
<H2K>
    <Weather>
    </Weather>
</H2K>"""

    h2k_file = tmp_path / "test.h2k"
    h2k_file.write_text(xml_content, encoding="utf-8")

    file_path, error_msg, location_code = debug._validate_single_h2k(h2k_file, "TestCommunity")

    assert file_path == h2k_file
    assert error_msg == "Could not find location code in H2K file."
    assert location_code is None


def test_validate_single_h2k_validation_failure(monkeypatch, tmp_path):
    """Test _validate_single_h2k reports validation failures."""
    xml_content = """<?xml version="1.0"?>
<H2K>
    <Weather>
        <Location code="400"/>
    </Weather>
</H2K>"""

    h2k_file = tmp_path / "test.h2k"
    h2k_file.write_text(xml_content, encoding="utf-8")

    # Mock validate_location_code to return False (code doesn't match)
    monkeypatch.setattr(debug, "validate_location_code", lambda comm, code: False)

    file_path, error_msg, location_code = debug._validate_single_h2k(h2k_file, "TestCommunity")

    assert file_path == h2k_file
    assert "FAILED" in error_msg
    assert "400" in error_msg
    assert "TestCommunity" in error_msg
    assert location_code == "400"


def test_validate_single_h2k_exception_handling(monkeypatch, tmp_path):
    """Test _validate_single_h2k handles exceptions during processing."""
    h2k_file = tmp_path / "test.h2k"
    h2k_file.write_text(
        "<?xml version='1.0'?><H2K><Weather><Location code='400'/></Weather></H2K>",
        encoding="utf-8",
    )

    # Mock get_location_code_from_h2k to raise an exception
    def mock_error(*args):
        raise RuntimeError("Test error")

    monkeypatch.setattr(debug, "get_location_code_from_h2k", mock_error)

    file_path, error_msg, location_code = debug._validate_single_h2k(h2k_file, "TestCommunity")

    assert file_path == h2k_file
    assert "Error processing file" in error_msg
    assert "Test error" in error_msg
    assert location_code is None
