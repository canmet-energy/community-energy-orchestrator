"""Output file management for community workflow results."""

import io
import zipfile
from pathlib import Path

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
