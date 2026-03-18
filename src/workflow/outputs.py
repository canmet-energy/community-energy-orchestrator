"""Output file management for community workflow results."""

import io
import json
import zipfile
from pathlib import Path

import pandas as pd

from workflow.core import communities_dir


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
    path = communities_dir() / community_name / Path(*subpath)

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


def get_daily_load_data(community_name: str) -> str:
    """
    Process community total CSV to calculate daily average and peak heating energy.

    Reads the hourly community-total CSV (8760 rows) and computes:
    - Daily average heating energy (mean of 24 hours)
    - Daily peak heating energy (max of 24 hours)

    Returns:
        JSON string with daily data (365 days) containing:
        - day: Day number (1-365)
        - avg_energy: Average heating energy for the day (GJ)
        - peak_energy: Peak heating energy for the day (GJ)

    Raises:
        FileNotFoundError: If community total CSV doesn't exist
        ValueError: If CSV structure is invalid
    """
    csv_path = get_community_total_path(community_name)

    # Read the CSV file
    try:
        df = pd.read_csv(csv_path, encoding="utf-8")
    except Exception as e:
        raise ValueError(f"Failed to read CSV file: {e}") from e

    # Validate required columns
    if "Total_Heating_Energy_GJ" not in df.columns:
        raise ValueError("CSV file missing required column: Total_Heating_Energy_GJ")

    # Calculate daily statistics
    # Group by day (every 24 hours)
    daily_data = []

    hours_per_day = 24
    total_hours = len(df)
    num_days = total_hours // hours_per_day

    for day in range(num_days):
        start_idx = day * hours_per_day
        end_idx = start_idx + hours_per_day

        day_data = df["Total_Heating_Energy_GJ"].iloc[start_idx:end_idx]

        daily_data.append(
            {
                "day": day + 1,  # 1-indexed day number
                "avg_energy": float(day_data.mean()),
                "peak_energy": float(day_data.max()),
            }
        )

    return json.dumps(daily_data)


def get_peak_day_hourly_data(community_name: str) -> str:
    """
    Get hourly energy data for the day with the highest peak hour.

    Reads the hourly community-total CSV and finds the day containing
    the single highest hourly energy value across the entire year.
    Returns the 24-hour profile for that day.

    Returns:
        JSON string with:
        - peak_day: Day number (1-365) when peak occurred
        - peak_hour: Hour (0-23) when peak occurred (0=midnight, 7=7AM)
        - peak_value_gj: The peak hourly energy value (GJ)
        - hourly_data: Array of 24 hourly values for that day
            - hour: Hour number (0-23)
            - energy_gj: Heating energy for that hour (GJ)

    Raises:
        FileNotFoundError: If community total CSV doesn't exist
        ValueError: If CSV structure is invalid
    """
    csv_path = get_community_total_path(community_name)

    # Read the CSV file
    try:
        df = pd.read_csv(csv_path, encoding="utf-8")
    except Exception as e:
        raise ValueError(f"Failed to read CSV file: {e}") from e

    # Validate required columns
    if "Total_Heating_Energy_GJ" not in df.columns:
        raise ValueError("CSV file missing required column: Total_Heating_Energy_GJ")

    # Drop any empty/NaN rows (CSV may have a blank row after the header)
    df = df.dropna(subset=["Total_Heating_Energy_GJ"]).reset_index(drop=True)

    # Find the hour with maximum energy in the entire year
    max_idx = df["Total_Heating_Energy_GJ"].idxmax()
    max_value = float(df["Total_Heating_Energy_GJ"].iloc[max_idx])

    # Calculate which day and hour this belongs to
    # Hours are 0-based (0=midnight, 7=7AM) matching the CSV timestamp convention
    hours_per_day = 24
    peak_day = (max_idx // hours_per_day) + 1  # 1-indexed day number
    peak_hour_in_day = max_idx % hours_per_day  # 0-indexed hour (0-23)

    # Get the 24-hour data for this day
    day_start_idx = (peak_day - 1) * hours_per_day
    day_end_idx = day_start_idx + hours_per_day

    hourly_data = []
    for hour in range(hours_per_day):
        idx = day_start_idx + hour
        if idx < len(df):
            hourly_data.append(
                {
                    "hour": hour,  # 0-indexed hour (0-23)
                    "energy_gj": float(df["Total_Heating_Energy_GJ"].iloc[idx]),
                }
            )

    # Add hour 0 of the next day to show the wrap-around for visualization continuity
    next_day_start_idx = day_end_idx
    if next_day_start_idx < len(df):
        hourly_data.append(
            {
                "hour": 24,  # Represents midnight of next day for plotting
                "energy_gj": float(df["Total_Heating_Energy_GJ"].iloc[next_day_start_idx]),
            }
        )

    result = {
        "peak_day": int(peak_day),
        "peak_hour": int(peak_hour_in_day),
        "peak_value_gj": float(max_value),
        "hourly_data": hourly_data,
    }

    return json.dumps(result)
