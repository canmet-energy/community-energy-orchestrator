#!/usr/bin/env python3
"""
Debug and validation module for community energy analysis.
Validates timeseries outputs from h2k-hpxml conversion.
"""

import os
import sys

from workflow.core import communities_dir
from workflow.requirements import get_community_requirements

# Enable UTF-8 mode for Windows compatibility with special characters
if sys.platform == "win32":
    # Set Python to use UTF-8 for file I/O and console output
    os.environ.setdefault("PYTHONUTF8", "1")

    # Reconfigure stdout/stderr to use UTF-8
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")


def debug_timeseries_outputs(community_name):
    """
    Validate that h2k-hpxml conversion generated required timeseries files.

    Args:
        community_name (str): Name of the community

    Returns:
        Path: Path to the debug log file

    Writes to:
        communities/<community>/analysis/output_debug.log (overwrites)
    """
    # Define paths for output directory and debug log
    output_base = communities_dir() / community_name / "archetypes" / "output"
    debug_log_path = communities_dir() / community_name / "analysis" / "output_debug.log"

    # Load housing requirements from CSV (e.g., {"pre-2000-single": 5, "2001-2015-semi": 3, ...})
    requirements = get_community_requirements(community_name)

    # Create parent directory if needed
    debug_log_path.parent.mkdir(parents=True, exist_ok=True)

    # Initialize counters for each housing type
    found_counts = {k: 0 for k in requirements}  # Start all counts at 0
    missing = {}  # Will store types that have fewer files than required

    # Only count files if output directory exists
    if output_base.exists():
        # Count how many output files were actually generated for each type
        for era_type in requirements:
            # Look for directories like: pre-2000-single_1/run/results_timeseries.csv
            # The glob pattern matches any directory starting with era_type followed by underscore
            matches = [p for p in output_base.glob(f"{era_type}_*/run/results_timeseries.csv")]
            found_counts[era_type] = len(matches)
            required = requirements[era_type]

            # Track which types have missing files
            if len(matches) < required:
                missing[era_type] = required - len(matches)
    else:
        # No output directory means all files are missing
        for era_type in requirements:
            required = requirements[era_type]
            missing[era_type] = required

    # Write results to log file (mode 'w' overwrites any existing file)
    with open(debug_log_path, "w", encoding="utf-8") as f:
        f.write(f"Timeseries output debug for {community_name}\n")

        # Write summary for all housing types
        for era_type in requirements:
            f.write(
                f"{era_type}: required={requirements[era_type]}, found={found_counts[era_type]}\n"
            )

        # Write detailed list of missing files if any
        if missing:
            f.write("\nMissing timeseries outputs by type:\n")
            for k, v in missing.items():
                f.write(f"{k}: {v} missing\n")
        else:
            f.write("\nAll required timeseries outputs found.\n")

    return debug_log_path


def main(community_name):
    """
    Run all debug checks and write to output_debug.log.

    Args:
        community_name (str): Name of the community

    Returns:
        Path: Path to the debug log file
    """
    # Run timeseries debug (mode 'w' creates/overwrites file)
    debug_log_path = debug_timeseries_outputs(community_name)

    return debug_log_path


def cli():
    """CLI entry point for validating workflow outputs."""
    if len(sys.argv) < 2:
        print("Usage: validate-outputs <community_name>")
        sys.exit(1)

    community_name = sys.argv[1]
    log_path = main(community_name)
    print(f"Debug log written to: {log_path}")


if __name__ == "__main__":
    cli()
