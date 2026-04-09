"""Unit tests for community analysis data processing functions.

Tests focus on data loading and transformation logic.
Integration tests cover the full aggregation workflow.
"""

import tempfile
from pathlib import Path

import pandas as pd
import pytest

import workflow.calculate_community_analysis as analysis
import workflow.config as config

pytestmark = pytest.mark.unit


# =============================================================================
# read_timeseries - Data loading and transformation
# =============================================================================


def test_read_timeseries_loads_all_fuel_types():
    """Test reading timeseries with all fuel types (electricity, oil, propane, natural gas, wood)."""
    csv_content = """Load: Heating: Delivered,End Use: Electricity: Heating,End Use: Fuel Oil: Heating,End Use: Propane: Heating,End Use: Natural Gas: Heating,End Use: Wood Cord: Heating
kBtu,kBtu,kBtu,kBtu,kBtu,kBtu
100,10,20,30,40,50
200,20,40,60,80,100
"""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False, encoding="utf-8") as f:
        f.write(csv_content)
        temp_path = f.name

    try:
        df = analysis.read_timeseries(temp_path)

        # Verify all columns are created
        assert "Heating_Load_GJ" in df.columns
        assert "Heating_Electricity_GJ" in df.columns
        assert "Heating_Oil_GJ" in df.columns
        assert "Heating_Propane_GJ" in df.columns
        assert "Heating_Natural_Gas_GJ" in df.columns
        assert "Heating_Wood_GJ" in df.columns

        # Verify conversion: all to GJ
        assert df["Heating_Load_GJ"].iloc[0] == pytest.approx(100 * config.KBTU_TO_GJ)
        assert df["Heating_Electricity_GJ"].iloc[0] == pytest.approx(10 * config.KWH_TO_GJ)
        assert df["Heating_Oil_GJ"].iloc[0] == pytest.approx(20 * config.KBTU_TO_GJ)
        assert df["Heating_Propane_GJ"].iloc[0] == pytest.approx(30 * config.KBTU_TO_GJ)
        assert df["Heating_Natural_Gas_GJ"].iloc[0] == pytest.approx(40 * config.KBTU_TO_GJ)
        assert df["Heating_Wood_GJ"].iloc[0] == pytest.approx(50 * config.KBTU_TO_GJ)
    finally:
        Path(temp_path).unlink()


def test_read_timeseries_missing_file_raises_error():
    """Test that reading non-existent file raises FileNotFoundError."""
    with pytest.raises(FileNotFoundError, match="Timeseries file not found"):
        analysis.read_timeseries("/nonexistent/path/file.csv")


def test_read_timeseries_fills_missing_fuel_columns_with_zeros():
    """Test that missing fuel type columns are filled with zeros."""
    # Only electricity heating, no oil, propane, natural gas, or wood
    csv_content = """Load: Heating: Delivered,End Use: Electricity: Heating
kBtu,kWh
100,10
200,20
"""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False, encoding="utf-8") as f:
        f.write(csv_content)
        temp_path = f.name

    try:
        df = analysis.read_timeseries(temp_path)

        # Electricity should have values converted to GJ
        assert df["Heating_Electricity_GJ"].iloc[0] == pytest.approx(10 * config.KWH_TO_GJ)

        # Missing fuel types should be filled with 0
        assert df["Heating_Oil_GJ"].iloc[0] == 0
        assert df["Heating_Propane_GJ"].iloc[0] == 0
        assert df["Heating_Natural_Gas_GJ"].iloc[0] == 0
        assert df["Heating_Wood_GJ"].iloc[0] == 0
    finally:
        Path(temp_path).unlink()


def test_read_timeseries_uses_system_column_names_as_fallback():
    """Test that function falls back to System Use column names if End Use columns missing."""
    # Use System Use columns instead of End Use
    csv_content = """Load: Heating: Delivered,System Use: HeatingSystem1: Electricity: Heating,System Use: HeatingSystem1: Fuel Oil: Heating
kBtu,kWh,kBtu
100,10,20
200,20,40
"""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False, encoding="utf-8") as f:
        f.write(csv_content)
        temp_path = f.name

    try:
        df = analysis.read_timeseries(temp_path)

        # Should successfully read from System Use columns (converted to GJ)
        assert df["Heating_Electricity_GJ"].iloc[0] == pytest.approx(10 * config.KWH_TO_GJ)
        assert df["Heating_Oil_GJ"].iloc[0] == pytest.approx(20 * config.KBTU_TO_GJ)
        assert df["Heating_Propane_GJ"].iloc[0] == 0  # Not present
    finally:
        Path(temp_path).unlink()


def test_read_timeseries_does_not_double_count_end_use_and_system_use():
    """Test that when both End Use and System Use columns exist, only one is used."""
    # Both End Use and System Use columns present with identical values
    csv_content = """Load: Heating: Delivered,End Use: Fuel Oil: Heating,System Use: HeatingSystem1: Fuel Oil: Heating
kBtu,kBtu,kBtu
100,20,20
200,40,40
"""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False, encoding="utf-8") as f:
        f.write(csv_content)
        temp_path = f.name

    try:
        df = analysis.read_timeseries(temp_path)

        # Should use End Use (preferred) and NOT also add System Use
        assert df["Heating_Oil_GJ"].iloc[0] == pytest.approx(20 * config.KBTU_TO_GJ)
        assert df["Heating_Oil_GJ"].iloc[1] == pytest.approx(40 * config.KBTU_TO_GJ)
    finally:
        Path(temp_path).unlink()


def test_read_timeseries_converts_invalid_data_to_nan():
    """Test that invalid numeric values are coerced to 0 (filled with fillna)."""
    csv_content = """Load: Heating: Delivered,End Use: Electricity: Heating
kBtu,kWh
invalid_value,10
200,not_a_number
"""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False, encoding="utf-8") as f:
        f.write(csv_content)
        temp_path = f.name

    try:
        df = analysis.read_timeseries(temp_path)

        # Invalid values should be coerced to NaN then filled with 0
        assert df["Heating_Load_GJ"].iloc[0] == 0
        assert df["Heating_Electricity_GJ"].iloc[0] == pytest.approx(10 * config.KWH_TO_GJ)
        assert df["Heating_Electricity_GJ"].iloc[1] == 0
    finally:
        Path(temp_path).unlink()


def test_read_timeseries_with_no_fuel_columns():
    """Test reading timeseries with only load data (no fuel type columns)."""
    csv_content = """Load: Heating: Delivered
kBtu
100
200
300
"""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False, encoding="utf-8") as f:
        f.write(csv_content)
        temp_path = f.name

    try:
        df = analysis.read_timeseries(temp_path)

        # Load should be present
        assert "Heating_Load_GJ" in df.columns
        assert df["Heating_Load_GJ"].iloc[0] == pytest.approx(100 * config.KBTU_TO_GJ)

        # All fuel types should default to 0
        assert df["Heating_Electricity_GJ"].iloc[0] == 0
        assert df["Heating_Oil_GJ"].iloc[0] == 0
        assert df["Heating_Propane_GJ"].iloc[0] == 0
        assert df["Heating_Natural_Gas_GJ"].iloc[0] == 0
        assert df["Heating_Wood_GJ"].iloc[0] == 0
    finally:
        Path(temp_path).unlink()


def test_read_timeseries_includes_auxiliary_electricity_in_total():
    """Test that fans/pumps and heat pump backup electricity are added to heating electricity."""
    csv_content = """Load: Heating: Delivered,End Use: Electricity: Heating,End Use: Electricity: Heating Fans/Pumps,End Use: Electricity: Heating Heat Pump Backup
kBtu,kWh,kWh,kWh
100,10,3,2
200,20,6,4
"""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False, encoding="utf-8") as f:
        f.write(csv_content)
        temp_path = f.name

    try:
        df = analysis.read_timeseries(temp_path)

        # Electricity should include main + fans/pumps + HP backup: (10 + 3 + 2) * KWH_TO_GJ
        assert df["Heating_Electricity_GJ"].iloc[0] == pytest.approx(15 * config.KWH_TO_GJ)
        assert df["Heating_Electricity_GJ"].iloc[1] == pytest.approx(30 * config.KWH_TO_GJ)
    finally:
        Path(temp_path).unlink()

