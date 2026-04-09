"""Integration tests for community analysis aggregation and statistics.

Tests focus on the full data pipeline: file selection â†’ aggregation â†’ statistics â†’ output.
Unit tests cover individual data transformation functions.
"""

import tempfile
from pathlib import Path

import pandas as pd
import pytest

import workflow.calculate_community_analysis as analysis
import workflow.config as config

pytestmark = pytest.mark.integration


# =============================================================================
# select_and_sum_timeseries - Full aggregation pipeline
# =============================================================================


def test_aggregates_multiple_timeseries_files(monkeypatch, tmp_path):
    """Test that select_and_sum_timeseries correctly aggregates data from multiple files.

    Integration point: File selection â†’ Parallel processing â†’ Aggregation â†’ Statistics
    """
    from workflow import calculate_community_analysis as calc

    # Create community directory structure
    community_name = "TestCommunity"
    timeseries_dir = tmp_path / community_name / "timeseries"
    timeseries_dir.mkdir(parents=True)

    # Mock requirements - need 3 of one type
    requirements = {"2002-2016-single": 3}

    # Create 3 timeseries files with varying data across rows
    for i in range(3):
        rows = [
            "Time,Load: Heating: Delivered,End Use: Electricity: Heating,End Use: Fuel Oil: Heating",
            "time,kBtu,kBtu,kBtu",  # Units row
        ]
        # Create 24 hours of data with different values per file
        for hour in range(24):
            load = 100 + i * 10  # File 0: 100, File 1: 110, File 2: 120
            elec = 10 + i
            oil = 5 + i
            rows.append(f"2024-01-01 {hour:02d}:00:00,{load},{elec},{oil}")

        csv_content = "\n".join(rows)
        file_path = timeseries_dir / f"2002-2016-single_EX-{i:04d}-results_timeseries.csv"
        file_path.write_text(csv_content, encoding="utf-8")

    # Mock dependencies
    monkeypatch.setattr(calc, "communities_dir", lambda: tmp_path)
    monkeypatch.setattr(calc, "get_community_requirements", lambda x: requirements)
    monkeypatch.setattr(calc, "EXPECTED_ROWS", 24)  # Mock expected rows for test

    # Run aggregation
    calc.select_and_sum_timeseries(community_name)

    # Verify output files were created
    output_csv = tmp_path / community_name / "analysis" / f"{community_name}-community_total.csv"
    output_md = tmp_path / community_name / "analysis" / f"{community_name}_analysis.md"

    assert output_csv.exists(), "Should create community total CSV"
    assert output_md.exists(), "Should create analysis markdown"

    # Verify aggregated data
    df = pd.read_csv(output_csv)
    assert len(df) == 24, "Should have 24 rows"

    # Verify first row: sum of (100 + 110 + 120) = 330 kBTU â†’ GJ for load
    expected_load_first = 330 * config.KBTU_TO_GJ
    expected_elec_first = (10 + 11 + 12) * config.KWH_TO_GJ  # Electricity kWh â†’ GJ
    expected_oil_first = (5 + 6 + 7) * config.KBTU_TO_GJ

    assert df["Heating_Load_GJ"].iloc[0] == pytest.approx(expected_load_first, rel=0.01)
    assert df["Heating_Electricity_GJ"].iloc[0] == pytest.approx(expected_elec_first, rel=0.01)
    assert df["Heating_Oil_GJ"].iloc[0] == pytest.approx(expected_oil_first, rel=0.01)

    # Verify last row has same values (all rows identical in each file)
    assert df["Heating_Load_GJ"].iloc[-1] == pytest.approx(expected_load_first, rel=0.01)

    # Verify Time column preserved
    assert df["Time"].iloc[0] == "2024-01-01 00:00:00"
    assert df["Time"].iloc[-1] == "2024-01-01 23:00:00"

    # Verify total energy column calculation
    expected_total = expected_elec_first + expected_oil_first
    assert df["Total_Heating_Energy_GJ"].iloc[0] == pytest.approx(expected_total, rel=0.01)

    # Verify markdown contains statistics
    md_content = output_md.read_text(encoding="utf-8")
    assert "Total Annual Load:" in md_content
    assert "Total Annual Energy:" in md_content
    assert community_name in md_content


def test_handles_insufficient_files_by_duplicating(monkeypatch, tmp_path, capsys):
    """Test that when not enough files exist, function duplicates files to meet requirements.

    Integration point: File selection â†’ Duplication logic â†’ Aggregation
    """
    from workflow import calculate_community_analysis as calc

    community_name = "TestCommunity"
    timeseries_dir = tmp_path / community_name / "timeseries"
    timeseries_dir.mkdir(parents=True)

    # Require 5 files but only provide 2
    requirements = {"pre-2002-single": 5}

    # Create only 2 unique files with different values
    for i in range(2):
        rows = [
            "Time,Load: Heating: Delivered,End Use: Electricity: Heating",
            "time,kBtu,kBtu",  # Units row
        ]
        for hour in range(24):
            rows.append(f"2024-01-01 {hour:02d}:00:00,{100 + i * 10},{10 + i}")
        csv_content = "\n".join(rows)
        file_path = timeseries_dir / f"pre-2002-single_EX-{i:04d}-results_timeseries.csv"
        file_path.write_text(csv_content, encoding="utf-8")

    monkeypatch.setattr(calc, "communities_dir", lambda: tmp_path)
    monkeypatch.setattr(calc, "get_community_requirements", lambda x: requirements)
    monkeypatch.setattr(calc, "EXPECTED_ROWS", 24)

    # Run aggregation
    calc.select_and_sum_timeseries(community_name)

    # Should still succeed and produce output
    output_csv = tmp_path / community_name / "analysis" / f"{community_name}-community_total.csv"
    assert output_csv.exists()

    # Verify that 5 files worth of data was used (some duplicated)
    # Result should be MORE than just 2 files but deterministic pattern depends on duplication
    df = pd.read_csv(output_csv)
    load_first_row = df["Heating_Load_GJ"].iloc[0]
    # With duplication, should be more than 2 files: 2Ã—100 = 200 kBTU minimum
    min_expected = 200 * config.KBTU_TO_GJ
    assert load_first_row > min_expected, "Should use more than 2 files via duplication"

    # Check that warning was printed about duplication
    captured = capsys.readouterr()
    assert "WARNING" in captured.out and "Duplicating" in captured.out


def test_handles_multiple_building_types(monkeypatch, tmp_path):
    """Test aggregation with multiple building types (eras and types).

    Integration point: Multi-type file selection â†’ Mixed aggregation
    """
    from workflow import calculate_community_analysis as calc

    community_name = "TestCommunity"
    timeseries_dir = tmp_path / community_name / "timeseries"
    timeseries_dir.mkdir(parents=True)

    # Multiple building types
    requirements = {
        "pre-2002-single": 2,
        "2002-2016-semi": 1,
    }

    # Create files for each type
    for i in range(2):
        rows = [
            "Time,Load: Heating: Delivered,End Use: Electricity: Heating",
            "time,kBtu,kBtu",  # Units row
        ]
        for hour in range(24):
            rows.append(f"2024-01-01 {hour:02d}:00:00,100,10")
        csv_content = "\n".join(rows)
        file_path = timeseries_dir / f"pre-2002-single_EX-{i:04d}-results_timeseries.csv"
        file_path.write_text(csv_content, encoding="utf-8")

    rows = [
        "Time,Load: Heating: Delivered,End Use: Electricity: Heating",
        "time,kBtu,kBtu",  # Units row
    ]
    for hour in range(24):
        rows.append(f"2024-01-01 {hour:02d}:00:00,50,5")
    csv_content = "\n".join(rows)
    file_path = timeseries_dir / "2002-2016-semi_EX-0001-results_timeseries.csv"
    file_path.write_text(csv_content, encoding="utf-8")

    monkeypatch.setattr(calc, "communities_dir", lambda: tmp_path)
    monkeypatch.setattr(calc, "get_community_requirements", lambda x: requirements)
    monkeypatch.setattr(calc, "EXPECTED_ROWS", 24)

    # Run aggregation
    calc.select_and_sum_timeseries(community_name)

    # Verify output
    output_csv = tmp_path / community_name / "analysis" / f"{community_name}-community_total.csv"
    assert output_csv.exists()

    df = pd.read_csv(output_csv)

    # Should sum all building types: 2 * 100 + 1 * 50 = 250 kBTU
    expected_load = 250 * config.KBTU_TO_GJ
    assert df["Heating_Load_GJ"].iloc[0] == pytest.approx(expected_load, rel=0.01)


def test_handles_double_files_for_semi_requirements(monkeypatch, tmp_path):
    """Test that 'semi' requirements also match 'double' files (same era).

    Integration point: File pattern matching â†’ Semi/double equivalence
    """
    from workflow import calculate_community_analysis as calc

    community_name = "TestCommunity"
    timeseries_dir = tmp_path / community_name / "timeseries"
    timeseries_dir.mkdir(parents=True)

    requirements = {"2002-2016-semi": 2}

    # Create 1 semi file and 1 double file (both should match)
    rows = [
        "Time,Load: Heating: Delivered,End Use: Electricity: Heating",
        "time,kBtu,kBtu",  # Units row
    ]
    for hour in range(24):
        rows.append(f"2024-01-01 {hour:02d}:00:00,100,10")
    csv_content = "\n".join(rows)

    semi_file = timeseries_dir / "2002-2016-semi_EX-0001-results_timeseries.csv"
    semi_file.write_text(csv_content, encoding="utf-8")

    double_file = timeseries_dir / "2002-2016-double_EX-0001-results_timeseries.csv"
    double_file.write_text(csv_content, encoding="utf-8")

    monkeypatch.setattr(calc, "communities_dir", lambda: tmp_path)
    monkeypatch.setattr(calc, "get_community_requirements", lambda x: requirements)
    monkeypatch.setattr(calc, "EXPECTED_ROWS", 24)

    # Run aggregation
    calc.select_and_sum_timeseries(community_name)

    # Should successfully use both files
    output_csv = tmp_path / community_name / "analysis" / f"{community_name}-community_total.csv"
    assert output_csv.exists()

    df = pd.read_csv(output_csv)
    # Both files should be included: 2 * 100 kBTU
    expected_load = 200 * config.KBTU_TO_GJ
    assert df["Heating_Load_GJ"].iloc[0] == pytest.approx(expected_load, rel=0.01)


def test_calculates_correct_statistics(monkeypatch, tmp_path):
    """Test that statistics (total, max, avg) are calculated correctly.

    Integration point: Aggregation â†’ Statistics calculation â†’ Markdown output
    """
    from workflow import calculate_community_analysis as calc

    community_name = "TestCommunity"
    timeseries_dir = tmp_path / community_name / "timeseries"
    timeseries_dir.mkdir(parents=True)

    requirements = {"2002-2016-single": 1}

    # Create file with simple, known values for easy verification
    rows = [
        "Time,Load: Heating: Delivered,End Use: Electricity: Heating,End Use: Propane: Heating",
        "time,kBtu,kBtu,kBtu",  # Units row
    ]
    # 4 rows with known values
    rows.append("2024-01-01 00:00:00,100,10,5")  # Hour 0
    rows.append("2024-01-01 01:00:00,200,20,10")  # Hour 1 (max)
    rows.append("2024-01-01 02:00:00,50,5,2.5")  # Hour 2 (min)
    rows.append("2024-01-01 03:00:00,100,10,5")  # Hour 3

    csv_content = "\n".join(rows)
    file_path = timeseries_dir / "2002-2016-single_EX-0001-results_timeseries.csv"
    file_path.write_text(csv_content, encoding="utf-8")

    monkeypatch.setattr(calc, "communities_dir", lambda: tmp_path)
    monkeypatch.setattr(calc, "get_community_requirements", lambda x: requirements)
    monkeypatch.setattr(calc, "EXPECTED_ROWS", 4)

    # Run aggregation
    calc.select_and_sum_timeseries(community_name)

    # Calculate expected values
    total_load_kbtu = 100 + 200 + 50 + 100  # 450 kBTU
    total_load_gj = total_load_kbtu * config.KBTU_TO_GJ
    max_load_kbtu = 200
    max_load_gj = max_load_kbtu * config.KBTU_TO_GJ
    avg_load_kbtu = 450 / 4  # 112.5
    avg_load_gj = avg_load_kbtu * config.KBTU_TO_GJ

    total_elec = 10 + 20 + 5 + 10  # 45 (read as-is, no conversion)
    total_elec_gj = total_elec * config.KWH_TO_GJ
    total_propane_kbtu = 5 + 10 + 2.5 + 5  # 22.5 kBTU
    total_propane_gj = total_propane_kbtu * config.KBTU_TO_GJ
    total_energy_gj = total_elec_gj + total_propane_gj

    elec_percentage = (total_elec_gj / total_energy_gj) * 100  # 66.7%
    propane_percentage = (total_propane_gj / total_energy_gj) * 100  # 33.3%

    # Read and verify statistics in markdown
    output_md = tmp_path / community_name / "analysis" / f"{community_name}_analysis.md"
    md_content = output_md.read_text(encoding="utf-8")

    # Verify load statistics
    assert (
        f"{total_load_gj:,.1f}" in md_content
    ), f"Should contain total load {total_load_gj:,.1f} GJ"
    # Max hourly shown as kW (power), avg hourly shown as GJ (energy)
    max_load_kw = max_load_gj * config.GJ_TO_KW
    assert f"{max_load_kw:,.1f}" in md_content, f"Should contain max load {max_load_kw:,.1f} kW"
    assert f"{avg_load_gj:,.1f}" in md_content, f"Should contain avg load {avg_load_gj:,.1f} GJ"

    # Verify energy statistics
    assert (
        f"{total_energy_gj:,.1f}" in md_content
    ), f"Should contain total energy {total_energy_gj:,.1f} GJ"
    assert (
        f"{total_elec_gj:,.1f}" in md_content
    ), f"Should contain electricity {total_elec_gj:,.1f} GJ"
    assert (
        f"{total_propane_gj:,.1f}" in md_content
    ), f"Should contain propane {total_propane_gj:,.1f} GJ"

    # Verify percentages (within 1% due to rounding)
    assert (
        f"{elec_percentage:,.1f}%" in md_content
    ), f"Should contain electricity % {elec_percentage:,.1f}%"
    assert (
        f"{propane_percentage:,.1f}%" in md_content
    ), f"Should contain propane % {propane_percentage:,.1f}%"


def test_fails_when_no_files_can_be_processed(monkeypatch, tmp_path):
    """Test that function raises error when no valid files can be processed.

    Integration point: Error handling â†’ Validation
    """
    from workflow import calculate_community_analysis as calc

    community_name = "TestCommunity"
    timeseries_dir = tmp_path / community_name / "timeseries"
    timeseries_dir.mkdir(parents=True)

    requirements = {"2002-2016-single": 1}

    # Create a malformed file (missing required columns) - just 2 rows for error test
    csv_content = """Wrong,Columns,Here
1,2,3
"""
    file_path = timeseries_dir / "2002-2016-single_EX-0001-results_timeseries.csv"
    file_path.write_text(csv_content, encoding="utf-8")

    monkeypatch.setattr(calc, "communities_dir", lambda: tmp_path)
    monkeypatch.setattr(calc, "get_community_requirements", lambda x: requirements)

    # Should raise ValueError
    with pytest.raises(ValueError, match="All input files failed processing"):
        calc.select_and_sum_timeseries(community_name)


def test_uses_all_available_files_when_no_requirements(monkeypatch, tmp_path):
    """Test that when no JSON requirements exist, function uses all available files.

    Integration point: Fallback mode â†’ Dynamic requirements
    """
    from workflow import calculate_community_analysis as calc

    community_name = "TestCommunity"
    timeseries_dir = tmp_path / community_name / "timeseries"
    timeseries_dir.mkdir(parents=True)

    # No requirements (empty dict)
    monkeypatch.setattr(calc, "get_community_requirements", lambda x: {})

    # Create various files
    for building_type in ["pre-2002-single", "2002-2016-semi"]:
        for i in range(2):
            rows = [
                "Time,Load: Heating: Delivered,End Use: Electricity: Heating",
                "time,kBtu,kBtu",  # Units row
            ]
            for hour in range(24):
                rows.append(f"2024-01-01 {hour:02d}:00:00,100,10")
            csv_content = "\n".join(rows)
            file_path = timeseries_dir / f"{building_type}_EX-{i:04d}-results_timeseries.csv"
            file_path.write_text(csv_content, encoding="utf-8")

    monkeypatch.setattr(calc, "communities_dir", lambda: tmp_path)
    monkeypatch.setattr(calc, "EXPECTED_ROWS", 24)

    # Run aggregation (should use all 4 files)
    calc.select_and_sum_timeseries(community_name)

    # Verify output includes all files
    output_csv = tmp_path / community_name / "analysis" / f"{community_name}-community_total.csv"
    assert output_csv.exists()

    df = pd.read_csv(output_csv)
    # Should sum all 4 files: 4 * 100 kBTU
    expected_load = 400 * config.KBTU_TO_GJ
    assert df["Heating_Load_GJ"].iloc[0] == pytest.approx(expected_load, rel=0.01)


def test_parallel_processing_produces_deterministic_results(monkeypatch, tmp_path):
    """Test that parallel processing produces consistent, deterministic results.

    Integration point: ProcessPoolExecutor â†’ Data aggregation consistency
    """
    from workflow import calculate_community_analysis as calc

    community_name = "TestCommunity"
    timeseries_dir = tmp_path / community_name / "timeseries"
    timeseries_dir.mkdir(parents=True)

    requirements = {"2002-2016-single": 5}

    # Create multiple files with different data
    for i in range(5):
        rows = [
            "Time,Load: Heating: Delivered,End Use: Electricity: Heating,End Use: Fuel Oil: Heating,End Use: Propane: Heating",
            "time,kBtu,kBtu,kBtu,kBtu",  # Units row
        ]
        for hour in range(24):
            rows.append(f"2024-01-01 {hour:02d}:00:00,{100 + i * 10},{10 + i},0,0")
        csv_content = "\n".join(rows)
        file_path = timeseries_dir / f"2002-2016-single_EX-{i:04d}-results_timeseries.csv"
        file_path.write_text(csv_content, encoding="utf-8")

    monkeypatch.setattr(calc, "communities_dir", lambda: tmp_path)
    monkeypatch.setattr(calc, "get_community_requirements", lambda x: requirements)
    monkeypatch.setattr(calc, "EXPECTED_ROWS", 24)

    # Run aggregation (uses parallel processing internally)
    calc.select_and_sum_timeseries(community_name)

    # Verify deterministic output
    output_csv = tmp_path / community_name / "analysis" / f"{community_name}-community_total.csv"
    df = pd.read_csv(output_csv)

    # Expected: sum of (100, 110, 120, 130, 140) = 600 kBTU per row
    expected_load_per_row = (100 + 110 + 120 + 130 + 140) * config.KBTU_TO_GJ
    assert df["Heating_Load_GJ"].iloc[0] == pytest.approx(expected_load_per_row, rel=0.01)

    # Verify total matches sum of components
    total = df["Total_Heating_Energy_GJ"].iloc[0]
    components = (
        df["Heating_Electricity_GJ"].iloc[0]
        + df["Heating_Oil_GJ"].iloc[0]
        + df["Heating_Propane_GJ"].iloc[0]
        + df["Heating_Natural_Gas_GJ"].iloc[0]
        + df["Heating_Wood_GJ"].iloc[0]
    )
    assert total == pytest.approx(components, rel=0.01)


def test_semi_requirements_do_not_match_wrong_era_double_files(monkeypatch, tmp_path, capsys):
    """Test that 'semi' requirements do NOT match 'double' files from different eras.

    Integration point: File pattern matching â†’ Era validation (negative test)
    """
    from workflow import calculate_community_analysis as calc

    community_name = "TestCommunity"
    timeseries_dir = tmp_path / community_name / "timeseries"
    timeseries_dir.mkdir(parents=True)

    # Require 2002-2016-semi but provide only pre-2002-double (wrong era)
    requirements = {"2002-2016-semi": 2}

    # Create pre-2002-double files (should NOT match 2002-2016-semi requirement)
    rows = [
        "Time,Load: Heating: Delivered,End Use: Electricity: Heating",
        "time,kBtu,kBtu",  # Units row
    ]
    for hour in range(24):
        rows.append(f"2024-01-01 {hour:02d}:00:00,100,10")
    csv_content = "\n".join(rows)

    wrong_era_file_1 = timeseries_dir / "pre-2002-double_EX-0001-results_timeseries.csv"
    wrong_era_file_1.write_text(csv_content, encoding="utf-8")
    wrong_era_file_2 = timeseries_dir / "pre-2002-double_EX-0002-results_timeseries.csv"
    wrong_era_file_2.write_text(csv_content, encoding="utf-8")

    monkeypatch.setattr(calc, "communities_dir", lambda: tmp_path)
    monkeypatch.setattr(calc, "get_community_requirements", lambda x: requirements)
    monkeypatch.setattr(calc, "EXPECTED_ROWS", 24)

    # Should fail because wrong-era files don't match
    with pytest.raises(ValueError):
        calc.select_and_sum_timeseries(community_name)

    # Verify that it printed errors about no files found
    captured = capsys.readouterr()
    assert (
        "ERROR: No available files for 2002-2016-semi" in captured.out
        or "0 files found" in captured.out
    )


def test_handles_production_size_files_with_8761_rows(monkeypatch, tmp_path):
    """Test that function correctly handles production-size files with 8761 rows.

    Integration point: Row count validation â†’ Production data handling

    Note: This is the only test using 8761 rows to verify production file handling.
    All other tests use 24 rows for speed and clarity.
    """
    from workflow import calculate_community_analysis as calc

    community_name = "TestCommunity"
    timeseries_dir = tmp_path / community_name / "timeseries"
    timeseries_dir.mkdir(parents=True)

    requirements = {"2002-2016-single": 2}

    # Create 2 production-size files (8760 rows = 365 days Ã— 24 hours)
    for i in range(2):
        rows = [
            "Time,Load: Heating: Delivered,End Use: Electricity: Heating",
            "time,kBtu,kBtu",  # Units row
        ]
        for hour in range(8760):
            rows.append(f"2024-01-01 {hour % 24:02d}:00:00,100,10")
        csv_content = "\n".join(rows)
        file_path = timeseries_dir / f"2002-2016-single_EX-{i:04d}-results_timeseries.csv"
        file_path.write_text(csv_content, encoding="utf-8")

    monkeypatch.setattr(calc, "communities_dir", lambda: tmp_path)
    monkeypatch.setattr(calc, "get_community_requirements", lambda x: requirements)
    # Don't mock EXPECTED_ROWS - use the real value (8760)

    # Run aggregation
    calc.select_and_sum_timeseries(community_name)

    # Verify output
    output_csv = tmp_path / community_name / "analysis" / f"{community_name}-community_total.csv"
    assert output_csv.exists()

    df = pd.read_csv(output_csv)

    # Verify correct row count
    assert len(df) == 8760, "Should have 8760 rows for production files"

    # Verify aggregation: 2 files Ã— 100 kBTU = 200 kBTU per row
    expected_load = 200 * config.KBTU_TO_GJ
    assert df["Heating_Load_GJ"].iloc[0] == pytest.approx(expected_load, rel=0.01)

    # Verify last row also correct
    assert df["Heating_Load_GJ"].iloc[-1] == pytest.approx(expected_load, rel=0.01)

