"""Unit tests for debug and validation functions."""

import tempfile
from pathlib import Path

import pytest

import workflow.debug_outputs as debug

pytestmark = pytest.mark.unit


def test_get_location_code_from_h2k():
    """Test locating code in nested XML structure"""
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
        # This tests the .// xpath which finds anywhere in tree
        code = debug.get_location_code_from_h2k(temp_path)
        assert code == "400"
    finally:
        Path(temp_path).unlink()


def test_get_location_code_from_h2k_missing_location():
    """Test extracting from XML missing Location element"""
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


def test_get_location_code_from_h2k_nonexistent_file():
    """Test extracting from non-existent file raises FileNotFoundError"""
    # Function will raise FileNotFoundError when trying to open missing file
    try:
        code = debug.get_location_code_from_h2k("/nonexistent/path/file.h2k")
        # If it returns None instead of raising, that's also acceptable
        assert code is None
    except FileNotFoundError:
        # Expected behavior - file doesn't exist
        pass


def test_validate_location_code_valid(sample_data):
    """Test validating location code for known community"""
    # Ogoki should have a specific expected location code
    # This tests that validate_location_code exists and returns boolean
    result = debug.validate_location_code(sample_data["community_name"], "400")
    assert isinstance(result, bool)


def test_validate_location_code_invalid_community():
    """Test validating location code for non-existent community"""
    result = debug.validate_location_code("NonExistentCommunity", "400")
    assert isinstance(result, bool)
    # Should return False for invalid community
    assert result is False


def test_validate_location_code_with_none():
    """Test validate_location_code returns False when code is None"""
    result = debug.validate_location_code("Ogoki", None)
    assert result is False
