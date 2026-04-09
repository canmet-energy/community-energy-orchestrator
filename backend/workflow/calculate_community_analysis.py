#!/usr/bin/env python3
import argparse
import glob
import json
import os
import random
import sys
import traceback
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

# Enable UTF-8 mode for Windows compatibility with special characters
if sys.platform == "win32":
    # Set Python to use UTF-8 for file I/O and console output
    os.environ.setdefault("PYTHONUTF8", "1")

    # Reconfigure stdout/stderr to use UTF-8
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")

from workflow.config import (
    ENERGY_CATEGORIES,
    EXPECTED_ROWS,
    GJ_TO_KW,
    KBTU_TO_GJ,
    KWH_TO_GJ,
    get_analysis_random_seed,
    get_max_workers,
)
from workflow.paths import communities_dir
from workflow.requirements import get_community_info, get_community_requirements


def _extract_column(df, csv_cols, unit):
    """Find matching CSV columns and return their summed values in GJ.

    *csv_cols* is a list of **fallback groups**.  Each element can be:
    - a plain string – treated as a single-element group, or
    - a list of strings – alternatives for the same measurement;
      only the **first** column found in the DataFrame is used.

    Different groups are **summed** (e.g. wood-cord + wood-pellets).
    Converts kBtu or kWh → GJ based on *unit* parameter.
    Returns a zero Series when none of the candidate columns exist.
    """
    result = pd.Series(0, index=df.index)
    for col_group in csv_cols:
        # Treat a bare string as a single-element fallback group
        if isinstance(col_group, str):
            col_group = [col_group]
        # Use only the first matching column from the fallback group
        for col in col_group:
            if col in df.columns:
                value = pd.to_numeric(df[col], errors="coerce").fillna(0)
                if unit == "kBtu":
                    value = value * KBTU_TO_GJ
                elif unit == "kWh":
                    value = value * KWH_TO_GJ
                result += value
                break
    return result


def read_timeseries(file_path):
    """Load and process timeseries data from CSV file.

    Extracts energy columns for every category defined in
    :data:`~workflow.config.ENERGY_CATEGORIES` (heating, total, etc.)
    in a single pass over the CSV.
    """
    file_path_obj = Path(file_path)
    if not file_path_obj.exists():
        raise FileNotFoundError(f"Timeseries file not found: {file_path}")

    # Load timeseries data - skip row 1 (units row) to avoid misalignment
    # Row 0: header, Row 1: units (kBtu, kWh, etc.), Row 2+: actual data
    # low_memory=False prevents DtypeWarning for mixed types
    df = pd.read_csv(file_path, skiprows=[1], low_memory=False, encoding="utf-8")

    for category in ENERGY_CATEGORIES.values():
        # Extract load column if the category defines one (e.g. heating load)
        load_cfg = category.get("load")
        if load_cfg:
            df[load_cfg["output_col"]] = _extract_column(
                df, [load_cfg["csv_col"]], load_cfg["unit"]
            )

        # Extract each fuel-source column
        for source in category["sources"].values():
            df[source["output_col"]] = _extract_column(df, source["csv_cols"], source["unit"])
            # Add any auxiliary columns (e.g. fans/pumps for heating electricity)
            # Auxiliary columns use the same unit as the main source
            for aux_col in source.get("additive_cols", []):
                if aux_col in df.columns:
                    aux_value = pd.to_numeric(df[aux_col], errors="coerce").fillna(0)
                    # Convert auxiliary column to GJ using source's unit
                    if source["unit"] == "kBtu":
                        aux_value = aux_value * KBTU_TO_GJ
                    elif source["unit"] == "kWh":
                        aux_value = aux_value * KWH_TO_GJ
                    df[source["output_col"]] += aux_value

    return df


def _get_output_columns():
    """Build the ordered list of community-total CSV columns from ENERGY_CATEGORIES."""
    cols = ["Time"]
    for cat in ENERGY_CATEGORIES.values():
        if cat.get("load"):
            cols.append(cat["load"]["output_col"])
        for source in cat["sources"].values():
            cols.append(source["output_col"])
        cols.append(cat["total_col"])
    return cols


def _get_aggregate_columns():
    """Return columns that must be summed across dwelling files (excludes totals)."""
    cols = []
    for cat in ENERGY_CATEGORIES.values():
        if cat.get("load"):
            cols.append(cat["load"]["output_col"])
        for source in cat["sources"].values():
            cols.append(source["output_col"])
    return cols


def _compute_category_stats(community_total, category):
    """Compute summary statistics for one energy category.

    Returns a dict with optional ``"load"`` and required ``"energy"`` sub-dicts,
    matching the structure used in the analysis JSON.
    """
    stats: dict[str, Any] = {}

    # Load stats (only categories with a load concept, e.g. heating)
    if category.get("load"):
        load_col = category["load"]["output_col"]
        total_gj = community_total[load_col].sum()
        max_gj_per_hour = community_total[load_col].max()
        avg_gj_per_hour = community_total[load_col].mean()
        stats["load"] = {
            "total_annual_gj": float(total_gj),
            "max_hourly_kw": float(max_gj_per_hour * GJ_TO_KW),
            "avg_hourly_gj": float(avg_gj_per_hour),
        }

    # Energy stats (total + per-source breakdown)
    total_col = category["total_col"]
    total_gj = community_total[total_col].sum()
    max_gj_per_hour = community_total[total_col].max()
    avg_gj_per_hour = community_total[total_col].mean()
    max_idx = community_total[total_col].idxmax()
    max_time = str(community_total.loc[max_idx, "Time"])

    def pct(val):
        return (val / total_gj * 100) if total_gj else 0

    by_source: dict[str, float] = {}
    for source_key, source in category["sources"].items():
        source_gj = community_total[source["output_col"]].sum()
        by_source[f"{source_key}_gj"] = float(source_gj)
        by_source[f"{source_key}_percent"] = round(pct(source_gj), 1)

    stats["energy"] = {
        "total_annual_gj": float(total_gj),
        "max_hourly_kw": float(max_gj_per_hour * GJ_TO_KW),
        "max_hourly_time": max_time,
        "avg_hourly_gj": float(avg_gj_per_hour),
        "by_source": by_source,
    }

    return stats


def _write_category_markdown(f, category, stats):
    """Write a markdown section for one energy category's statistics."""
    label = category["label"]

    # Load section (only for categories with a load concept)
    if "load" in stats:
        load = stats["load"]
        f.write(f"## Community {label} Load Statistics (what the houses need):\n")
        f.write(f"- Total Annual Load: {load['total_annual_gj']:,.1f} GJ\n")
        f.write(f"- Maximum Hourly Load: {load['max_hourly_kw']:,.1f} kW\n")
        f.write(f"- Average Hourly Load: {load['avg_hourly_gj']:,.1f} GJ\n\n")

    # Energy section
    energy = stats["energy"]
    heading = f"## Community {label} Energy Use Statistics"
    if "load" in stats:
        heading += " (what the equipment uses)"
    f.write(f"{heading}:\n")
    f.write(f"- Total Annual Energy: {energy['total_annual_gj']:,.1f} GJ\n")

    for source_key in category["sources"]:
        display_name = source_key.replace("_", " ").title()
        gj = energy["by_source"][f"{source_key}_gj"]
        pct = energy["by_source"][f"{source_key}_percent"]
        f.write(f"  - {display_name}: {gj:,.1f} GJ ({pct:,.1f}%)\n")

    f.write(f"- Maximum Hourly Power: {energy['max_hourly_kw']:,.1f} kW\n")
    f.write(f"- Average Hourly Energy: {energy['avg_hourly_gj']:,.1f} GJ\n")


def _format_community_info_lines(community_info):
    """Return formatted community metadata lines as a list of strings."""
    lines = []
    lines.append(f"Province/Territory: {community_info.get('province_territory', 'N/A')}")

    pop = community_info.get("population")
    lines.append(f"Population: {pop:,}" if pop else "Population: N/A")

    hdd = community_info.get("hdd")
    lines.append(f"Heating Degree Days (HDD): {hdd:,}" if hdd else "Heating Degree Days (HDD): N/A")

    weather = community_info.get("weather_location")
    lines.append(f"Weather Station: {weather}" if weather else "Weather Station: N/A")

    total = community_info.get("total_houses")
    lines.append(f"Total Homes: {total:,}" if total else "Total Homes: N/A")

    dist = community_info.get("housing_distribution", {})
    if dist:
        lines.append("Housing Distribution:")
        for housing_type, count in dist.items():
            if count > 0:
                lines.append(f"  - {housing_type}: {count}")

    return lines


def _write_community_info_markdown(f, community_info):
    """Write a markdown section summarizing community metadata."""
    f.write("## Community Overview\n")
    for line in _format_community_info_lines(community_info):
        f.write(f"- {line}\n")


def _print_community_info(community_info):
    """Print community metadata summary to console."""
    print("\nCommunity Overview:")
    for line in _format_community_info_lines(community_info):
        print(line)


def _print_category_stats(category, stats):
    """Print summary statistics for one energy category to console."""
    label = category["label"]

    if "load" in stats:
        load = stats["load"]
        print(f"\nCommunity {label} Load Statistics (what the houses need):")
        print(f"Total Annual Load: {load['total_annual_gj']:,.1f} GJ")
        print(f"Maximum Hourly Load: {load['max_hourly_kw']:,.1f} kW")
        print(f"Average Hourly Load: {load['avg_hourly_gj']:,.1f} GJ")

    energy = stats["energy"]
    section_title = f"\nCommunity {label} Energy Use Statistics"
    if "load" in stats:
        section_title += " (what the equipment uses)"
    print(f"{section_title}:")
    print(f"Total Annual Energy: {energy['total_annual_gj']:,.1f} GJ")

    for source_key in category["sources"]:
        display_name = source_key.replace("_", " ").title()
        gj = energy["by_source"][f"{source_key}_gj"]
        pct = energy["by_source"][f"{source_key}_percent"]
        print(f"- {display_name}: {gj:,.1f} GJ ({pct:,.1f}%)")

    print(f"Maximum Hourly Power: {energy['max_hourly_kw']:,.1f} kW")
    print(f"Average Hourly Energy: {energy['avg_hourly_gj']:,.1f} GJ")


def select_and_sum_timeseries(community_name):
    # Set random seed for reproducible file duplication (only if specified)
    seed = get_analysis_random_seed()
    use_deterministic_order = False
    if seed is not None:
        random.seed(seed)
        use_deterministic_order = True

    print(f"Processing community: {community_name}")
    # Get requirements from JSON file
    print(f"Looking for community: '{community_name}' in requirements file")
    requirements = get_community_requirements(community_name)

    if requirements:
        print(f"Found {len(requirements)} building types for {community_name}:")
        if all(count == 0 for count in requirements.values()):
            print(f"\n{'='*60}")
            print(f"Community '{community_name}' exists in database but has 0 houses.")
            print(f"No analysis can be performed.")
            print(f"{'='*60}\n")
            return
    else:
        print(f"Community '{community_name}' not found in database. Using available files instead.")

    # Try multiple variations of the directory name
    community_hyphen = community_name.replace(" ", "-")
    community_upper = community_name.upper()
    community_upper_hyphen = community_upper.replace(" ", "-")

    base_path = communities_dir()
    timeseries_dirs = [
        base_path / community_name / "timeseries",
        base_path / community_hyphen / "timeseries",
        base_path / community_upper / "timeseries",
        base_path / community_upper_hyphen / "timeseries",
    ]

    # Find the directory that exists
    timeseries_dir = None
    for dir_path in timeseries_dirs:
        if dir_path.exists():
            timeseries_dir = dir_path
            break

    if timeseries_dir is None:
        raise ValueError(
            f"Directory not found for {community_name}. Tried various naming formats including hyphen, space, and communities/<community>/timeseries."
        )

    print(f"Using timeseries directory: {timeseries_dir}")

    # If no requirements, use all available files
    if not requirements:
        print("\nNo specific requirements found. Using all available files.")
        # Scan directory for available files and build requirements dynamically
        building_types = {}

        for file_path in glob.glob(str(timeseries_dir / "*-results_timeseries.csv")):
            filename = Path(file_path).name
            # Extract building type from filename (e.g., "2002-2016-single" from "2002-2016-single_EX-0001-results_timeseries.csv")
            if "_" in filename:
                building_type = filename.split("_")[0]
                if building_type not in building_types:
                    building_types[building_type] = 0
                building_types[building_type] += 1

        requirements = building_types

        if not requirements:
            raise ValueError(
                f"No timeseries files found in {timeseries_dir}. Cannot proceed with analysis."
            )

    print("\nFinding available files...")
    files_by_type: dict[str, list[Path]] = {k: [] for k in requirements.keys()}

    # Helper to find files for a type in a directory
    def find_files_for_type(directory, req_key):
        # Use the full req_key for matching filenames
        building_type = req_key
        found_files = []
        for file_path_str in glob.glob(str(directory / "*-results_timeseries.csv")):
            file_path = Path(file_path_str)
            filename = file_path.name
            # For 'semi' requirements, also include 'double' files for the same era
            if building_type.endswith("semi"):
                era = (
                    "-".join(building_type.split("-")[:2])
                    if "-" in building_type
                    else building_type
                )
                semi_prefix = f"{era}-semi_"
                double_prefix = f"{era}-double_"
                if (
                    filename.startswith(semi_prefix) or filename.startswith(double_prefix)
                ) and filename.endswith("-results_timeseries.csv"):
                    found_files.append(file_path)
            else:
                if filename.startswith(f"{building_type}_") and filename.endswith(
                    "-results_timeseries.csv"
                ):
                    found_files.append(file_path)
        return found_files

    # First, find files in the main timeseries directory
    for req_key in requirements.keys():
        files_by_type[req_key] = find_files_for_type(timeseries_dir, req_key)

    print("\nSummary by housing type (files found):")
    for building_type, files in files_by_type.items():
        print(
            f"  {building_type}: {len(files)} files found (required: {requirements[building_type]})"
        )
        if len(files) < requirements[building_type]:
            print(
                f"WARNING: Not enough files found for {building_type}. Found {len(files)}, required {requirements[building_type]}. Will duplicate or skip as needed."
            )

    # Only process the exact number required for each type
    selected_files = []
    for building_type, required_count in requirements.items():
        available_files = files_by_type[building_type]
        if use_deterministic_order:
            available_files = sorted(available_files)
        if len(available_files) < required_count:
            print(
                f"WARNING: Not enough files for {building_type}. Found {len(available_files)}, required {required_count}. Duplicating as needed."
            )
            # Duplicate files with replacement to meet required count
            if available_files:
                selected = available_files.copy()
                needed = required_count - len(available_files)
                selected += random.choices(available_files, k=needed)
            else:
                print(f"ERROR: No available files for {building_type}. Skipping.")
                continue
        else:
            selected = available_files[:required_count]
        selected_files.extend(selected)

    # Check if any files were selected before processing
    if not selected_files:
        print("\n[ERROR] No files were selected for processing. Cannot proceed with analysis.")
        raise ValueError(
            "No timeseries files could be selected. Check that files exist and match the required building types."
        )

    # Aggregation logic with robust error handling
    print("\nProcessing selected files...")
    processed_dfs = []
    error_files = []

    # Build column lists from configuration
    output_columns = _get_output_columns()
    aggregate_columns = _get_aggregate_columns()

    max_workers = min(get_max_workers(), len(selected_files))
    with ProcessPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(read_timeseries, file_path): file_path for file_path in selected_files
        }
        for future in as_completed(futures):
            current_file = futures[future]
            try:
                df = future.result()
                # Check for expected row count
                if len(df) != EXPECTED_ROWS:
                    print(
                        f"[WARNING] File {current_file} has {len(df)} rows, expected {EXPECTED_ROWS}."
                    )
                if "Time" not in df.columns:
                    print(f"[ERROR] File {current_file} missing required Time column. Skipping.")
                    error_files.append(current_file)
                    continue
                # Safety net: fill any missing aggregate columns with zeros
                for col in aggregate_columns:
                    if col not in df.columns:
                        df[col] = 0

                processed_dfs.append(df)
                print(f"Processed: {Path(current_file).stem}")
            except Exception as e:
                print(f"[ERROR] Exception processing {current_file}: {e}")
                error_files.append(current_file)
                continue

    # Aggregate results after parallel processing
    if processed_dfs:
        n_rows = len(processed_dfs[0])

        # Sum each aggregate column across all dwelling DataFrames
        accumulators = {col: np.zeros(n_rows) for col in aggregate_columns}
        for df in processed_dfs:
            for col in aggregate_columns:
                accumulators[col] += df[col].values

        # Build community total DataFrame
        data = {"Time": processed_dfs[0]["Time"].values}
        data.update(accumulators)
        community_total = pd.DataFrame(data)

        # Compute total-energy column for each category (sum of sources)
        for cat in ENERGY_CATEGORIES.values():
            source_cols = [s["output_col"] for s in cat["sources"].values()]
            community_total[cat["total_col"]] = sum(community_total[c] for c in source_cols)

        successful_files_used = len(processed_dfs)
    else:
        community_total = None
        successful_files_used = 0

    if community_total is not None:
        # Truncate to expected rows if needed
        if len(community_total) > EXPECTED_ROWS:
            print(
                f"[WARNING] Output has {len(community_total)} rows, truncating to {EXPECTED_ROWS}."
            )
            community_total = community_total.iloc[:EXPECTED_ROWS]
        community_total = community_total[output_columns]

        # Save the aggregated CSV
        base_communities_path = communities_dir()
        community_folder = base_communities_path / community_name
        community_folder.mkdir(parents=True, exist_ok=True)
        (community_folder / "analysis").mkdir(parents=True, exist_ok=True)
        output_file = community_folder / "analysis" / f"{community_name}-community_total.csv"
        community_total.to_csv(output_file, index=False)
        print(f"\nCommunity total energy use saved to:")
        print(f"  - {output_file} (community folder)")

        # Compute statistics for every category
        all_stats = {}
        for cat_key, cat in ENERGY_CATEGORIES.items():
            all_stats[cat_key] = _compute_category_stats(community_total, cat)

        # Build analysis JSON from computed stats
        analysis_data = {"community_name": community_name}
        for cat_key, cat in ENERGY_CATEGORIES.items():
            stats = all_stats[cat_key]
            if "load" in stats:
                analysis_data[f"{cat_key}_load"] = stats["load"]
            analysis_data[f"{cat_key}_energy"] = stats["energy"]

        # Fetch community metadata for the report
        community_info = get_community_info(community_name)

        # Save analysis markdown
        analysis_file = community_folder / "analysis" / f"{community_name}_analysis.md"
        with open(analysis_file, "w", encoding="utf-8") as f:
            f.write(f"# {community_name} Community Analysis\n\n")

            if community_info:
                _write_community_info_markdown(f, community_info)
                f.write("\n")

            for cat_key, cat in ENERGY_CATEGORIES.items():
                _write_category_markdown(f, cat, all_stats[cat_key])
                f.write("\n")

            if error_files:
                f.write(f"## Warnings and Errors Encountered:\n")
                for ef in error_files:
                    f.write(f"- Issue with file: {ef}\n")

            f.write(
                f"\nThe number of files that were successfully used in the analysis: {successful_files_used}/{len(selected_files)}\n"
            )

        print(f"\nAnalysis results saved to:")
        print(f"  - {analysis_file} (community folder)")

        # Include community metadata in JSON output
        if community_info:
            analysis_data["community_info"] = {
                k: community_info[k]
                for k in (
                    "province_territory",
                    "population",
                    "hdd",
                    "weather_location",
                    "total_houses",
                )
            }
            analysis_data["community_info"]["housing_distribution"] = {
                k: v for k, v in community_info.get("housing_distribution", {}).items() if v > 0
            }

        # Save analysis JSON for frontend visualizations
        analysis_json_file = community_folder / "analysis" / f"{community_name}_analysis.json"
        with open(analysis_json_file, "w", encoding="utf-8") as f:
            json.dump(analysis_data, f, indent=2)
        print(f"  - {analysis_json_file} (community folder - JSON)")

        # Print summary to console
        if community_info:
            _print_community_info(community_info)

        for cat_key, cat in ENERGY_CATEGORIES.items():
            _print_category_stats(cat, all_stats[cat_key])

        if error_files:
            print(
                "\n[ALERT] Some input files had issues and were skipped or partially processed. See analysis markdown for details."
            )
        print(f"\nAnalysis saved to: {analysis_file}")
    else:
        print("\n[ERROR] No files were successfully processed. Analysis cannot proceed.")
        raise ValueError("All input files failed processing. Check error messages above.")


def cli():
    """CLI entry point for calculating community analysis."""
    try:
        parser = argparse.ArgumentParser(description="Calculate community total energy use.")
        parser.add_argument(
            "community_name", type=str, help="Name of the community (e.g., BONILLA-ISLAND)"
        )

        args = parser.parse_args()

        select_and_sum_timeseries(args.community_name)
        print("Script finished.")
    except FileNotFoundError as e:
        print(f"Error: {e}")
    except ValueError as e:
        print(f"Error: {e}")
    except Exception as e:
        print(f"Unexpected error: {e}")
        traceback.print_exc()


if __name__ == "__main__":
    cli()
