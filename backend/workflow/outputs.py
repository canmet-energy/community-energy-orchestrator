"""Output file management for community workflow results."""

import io
import zipfile
from pathlib import Path

import pandas as pd
from workflow.config import ENERGY_CATEGORIES
from workflow.paths import output_dir


def _community_file(community_name: str, *subpath: str) -> Path:
    """
    Build and validate a path under a community's directory.

    Args:
        community_name: Name of the community
        *subpath: Path segments under the community directory

    Returns:
        Validated Path to the file or directory

    Raises:
        FileNotFoundError: If the resolved path doesn't exist
    """
    path = output_dir() / community_name / Path(*subpath)

    if not path.exists():
        raise FileNotFoundError(f"Not found: {path}")

    return path


def get_community_total_path(community_name: str) -> Path:
    """Get the path to the community total CSV file."""
    return _community_file(community_name, "analysis", f"{community_name}-community_total.csv")


def get_analysis_markdown_path(community_name: str) -> Path:
    """Get the path to the analysis markdown file."""
    return _community_file(community_name, "analysis", f"{community_name}_analysis.md")


def get_analysis_json_path(community_name: str) -> Path:
    """Get the path to the analysis JSON file."""
    return _community_file(community_name, "analysis", f"{community_name}_analysis.json")


def get_timeseries_files(community_name: str) -> list[Path]:
    """
    Get all timeseries CSV files for a community.

    Returns:
        List of paths to timeseries CSV files

    Raises:
        FileNotFoundError: If directory doesn't exist or has no matching files
    """
    timeseries_dir = _community_file(community_name, "timeseries")

    csv_files = list(timeseries_dir.glob("*-results_timeseries.csv"))

    if not csv_files:
        raise FileNotFoundError(f"No timeseries CSV files found in {timeseries_dir}.")

    return csv_files


def create_timeseries_zip(community_name: str) -> io.BytesIO:
    """
    Create an in-memory ZIP archive of all timeseries CSV files for a community.

    Returns:
        BytesIO buffer containing the ZIP archive

    Raises:
        FileNotFoundError: If no timeseries files are found
    """
    csv_files = get_timeseries_files(community_name)

    zip_buffer = io.BytesIO()

    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_STORED) as zip_file:
        for csv_file in csv_files:
            zip_file.write(csv_file, arcname=csv_file.name)

    zip_buffer.seek(0)
    return zip_buffer


def get_daily_load_data(community_name: str, category: str = "heating") -> list[dict]:
    """
    Process community total CSV to calculate daily average and peak energy.

    Reads the hourly community-total CSV (8760 rows) and computes:
    - Daily average energy (mean of 24 hours)
    - Daily peak energy (max of 24 hours)

    Args:
        community_name: Name of the community
        category: Energy category key from ENERGY_CATEGORIES (default: "heating")

    Returns:
        List of dicts with daily data (365 days) containing:
        - day: Day number (1-365)
        - avg_energy: Average energy for the day (GJ)
        - peak_energy: Peak energy for the day (GJ)

    Raises:
        FileNotFoundError: If community total CSV doesn't exist
        ValueError: If CSV structure is invalid or category is unknown
    """
    if category not in ENERGY_CATEGORIES:
        raise ValueError(f"Unknown energy category: {category}")

    total_col = ENERGY_CATEGORIES[category]["total_col"]
    csv_path = get_community_total_path(community_name)

    try:
        df = pd.read_csv(csv_path, encoding="utf-8")
    except Exception as e:
        raise ValueError(f"Failed to read CSV file: {e}") from e

    if total_col not in df.columns:
        raise ValueError(f"CSV file missing required column: {total_col}")

    daily_data = []
    hours_per_day = 24
    num_days = len(df) // hours_per_day

    for day in range(num_days):
        start_idx = day * hours_per_day
        end_idx = start_idx + hours_per_day

        day_data = df[total_col].iloc[start_idx:end_idx]

        daily_data.append(
            {
                "day": day + 1,
                "avg_energy": float(day_data.mean()),
                "peak_energy": float(day_data.max()),
            }
        )

    return daily_data


def get_peak_day_hourly_data(community_name: str, category: str = "heating") -> dict:
    """
    Get hourly energy data for the day with the highest peak hour.

    Reads the hourly community-total CSV and finds the day containing
    the single highest hourly energy value across the entire year.
    Returns the 24-hour profile for that day.

    Args:
        community_name: Name of the community
        category: Energy category key from ENERGY_CATEGORIES (default: "heating")

    Returns:
        Dict with:
        - peak_day: Day number (1-365) when peak occurred
        - peak_hour: Hour (0-23) when peak occurred (0=midnight, 7=7AM)
        - peak_value_gj: The peak hourly energy value (GJ)
        - hourly_data: Array of 24 hourly values for that day
            - hour: Hour number (0-23)
            - energy_gj: Energy for that hour (GJ)

    Raises:
        FileNotFoundError: If community total CSV doesn't exist
        ValueError: If CSV structure is invalid or category is unknown
    """
    if category not in ENERGY_CATEGORIES:
        raise ValueError(f"Unknown energy category: {category}")

    total_col = ENERGY_CATEGORIES[category]["total_col"]
    csv_path = get_community_total_path(community_name)

    try:
        df = pd.read_csv(csv_path, encoding="utf-8")
    except Exception as e:
        raise ValueError(f"Failed to read CSV file: {e}") from e

    if total_col not in df.columns:
        raise ValueError(f"CSV file missing required column: {total_col}")

    df = df.dropna(subset=[total_col]).reset_index(drop=True)

    max_idx = df[total_col].idxmax()
    max_value = df[total_col].iloc[max_idx]

    hours_per_day = 24
    peak_day = (max_idx // hours_per_day) + 1
    peak_hour_in_day = max_idx % hours_per_day

    day_start_idx = (peak_day - 1) * hours_per_day
    day_end_idx = day_start_idx + hours_per_day

    hourly_data = []
    for hour in range(hours_per_day):
        idx = day_start_idx + hour
        if idx < len(df):
            hourly_data.append(
                {
                    "hour": hour,
                    "energy_gj": float(df[total_col].iloc[idx]),
                }
            )

    # Add hour 0 of the next day for visualization continuity
    next_day_start_idx = day_end_idx
    if next_day_start_idx < len(df):
        hourly_data.append(
            {
                "hour": 24,
                "energy_gj": float(df[total_col].iloc[next_day_start_idx]),
            }
        )

    return {
        "peak_day": int(peak_day),
        "peak_hour": int(peak_hour_in_day),
        "peak_value_gj": float(max_value),
        "hourly_data": hourly_data,
    }
