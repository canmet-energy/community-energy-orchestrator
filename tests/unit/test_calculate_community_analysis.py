"""Unit tests for community analysis calculations."""

import tempfile
from pathlib import Path

import pandas as pd
import pytest

import workflow.calculate_community_analysis as analysis
import workflow.config as config

pytestmark = pytest.mark.unit


def test_read_timeseries_valid_file():
    """Test reading timeseries data with all fuel types"""
    csv_content = """Load: Heating: Delivered,End Use: Electricity: Heating,End Use: Fuel Oil: Heating,End Use: Propane: Heating
100,10,20,30
200,20,40,60
"""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False, encoding="utf-8") as f:
        f.write(csv_content)
        temp_path = f.name

    try:
        df = analysis.read_timeseries(temp_path)
        assert "Heating_Load_GJ" in df.columns
        assert "Heating_Electricity_GJ" in df.columns
        assert "Heating_Oil_GJ" in df.columns
        assert "Heating_Propane_GJ" in df.columns
        assert df["Heating_Load_GJ"].iloc[0] == pytest.approx(100 * config.KBTU_TO_GJ)
    finally:
        Path(temp_path).unlink()


def test_read_timeseries_missing_file():
    """Test that reading non-existent file raises FileNotFoundError"""
    with pytest.raises(FileNotFoundError):
        analysis.read_timeseries("/nonexistent/path/file.csv")


def test_read_timeseries_electricity_only():
    """Test reading timeseries with only electricity heating"""
    csv_content = """Load: Heating: Delivered,End Use: Electricity: Heating
100,10
200,20
"""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False, encoding="utf-8") as f:
        f.write(csv_content)
        temp_path = f.name

    try:
        df = analysis.read_timeseries(temp_path)
        assert df["Heating_Electricity_GJ"].iloc[0] == pytest.approx(10 * config.KBTU_TO_GJ)
        assert df["Heating_Oil_GJ"].iloc[0] == 0
        assert df["Heating_Propane_GJ"].iloc[0] == 0
    finally:
        Path(temp_path).unlink()


def test_read_timeseries_handles_invalid_numeric_data():
    """Test that invalid numeric values are handled gracefully"""
    csv_content = """Load: Heating: Delivered,End Use: Electricity: Heating
invalid,10
200,abc
"""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False, encoding="utf-8") as f:
        f.write(csv_content)
        temp_path = f.name

    try:
        df = analysis.read_timeseries(temp_path)
        # Should convert to NaN with errors='coerce'
        assert pd.isna(df["Heating_Load_GJ"].iloc[0])
    finally:
        Path(temp_path).unlink()
