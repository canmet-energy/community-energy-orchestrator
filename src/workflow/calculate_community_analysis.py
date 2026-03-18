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

from workflow.config import EXPECTED_ROWS, KBTU_TO_GJ, get_analysis_random_seed, get_max_workers
from workflow.core import communities_dir, csv_dir
from workflow.requirements import get_community_requirements


def read_timeseries(file_path):
    """Load and process timeseries data from CSV file."""
    file_path_obj = Path(file_path)
    if not file_path_obj.exists():
        raise FileNotFoundError(f"Timeseries file not found: {file_path}")

    # Load timeseries data - skip row 1 (units row) to avoid misalignment
    # Row 0: header, Row 1: units (kBtu, kWh, etc.), Row 2+: actual data
    # low_memory=False prevents DtypeWarning for mixed types
    df = pd.read_csv(file_path, skiprows=[1], low_memory=False, encoding="utf-8")

    # Get heating load (what the house needs)
    df["Heating_Load_GJ"] = (
        pd.to_numeric(df["Load: Heating: Delivered"], errors="coerce") * KBTU_TO_GJ
    )

    # Get heating fuel use (what equipment uses)
    # Each fuel type uses End Use columns with System Use as fallback.
    # Electricity includes main heating, fans/pumps, and heat pump backup.
    fuel_col_map = {
        "Heating_Electricity_GJ": [
            "End Use: Electricity: Heating",
            "System Use: HeatingSystem1: Electricity: Heating",
        ],
        "Heating_Oil_GJ": [
            "End Use: Fuel Oil: Heating",
            "System Use: HeatingSystem1: Fuel Oil: Heating",
        ],
        "Heating_Propane_GJ": [
            "End Use: Propane: Heating",
            "System Use: HeatingSystem1: Propane: Heating",
        ],
        "Heating_Natural_Gas_GJ": [
            "End Use: Natural Gas: Heating",
            "System Use: HeatingSystem1: Natural Gas: Heating",
        ],
        "Heating_Wood_GJ": [
            "End Use: Wood Cord: Heating",
            "System Use: SupplHeatingSystem1: Wood Cord: Heating",
        ],
    }

    for output_col, source_cols in fuel_col_map.items():
        for col in source_cols:
            if col in df.columns:
                df[output_col] = pd.to_numeric(df[col], errors="coerce") * KBTU_TO_GJ
                break
        else:
            df[output_col] = 0

    # Add auxiliary electricity columns (fans/pumps and heat pump backup)
    # into the electricity total — these are separate End Use entries from
    # the simulation that represent additional electrical energy for heating.
    aux_elec_cols = [
        "End Use: Electricity: Heating Fans/Pumps",
        "End Use: Electricity: Heating Heat Pump Backup",
    ]
    for col in aux_elec_cols:
        if col in df.columns:
            df["Heating_Electricity_GJ"] += (
                pd.to_numeric(df[col], errors="coerce").fillna(0) * KBTU_TO_GJ
            )

    return df


def select_and_sum_timeseries(community_name):
    # Set random seed for reproducible file duplication (only if specified)
    seed = get_analysis_random_seed()
    use_deterministic_order = False
    if seed is not None:
        random.seed(seed)
        use_deterministic_order = True

    print(f"Processing community: {community_name}")
    # Get requirements from CSV file
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
            # Extract building type from filename (e.g., "2001-2015-single" from "2001-2015-single_EX-0001-results_timeseries.csv")
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
    expected_columns = [
        "Time",
        "Heating_Load_GJ",
        "Heating_Propane_GJ",
        "Heating_Oil_GJ",
        "Heating_Electricity_GJ",
        "Heating_Natural_Gas_GJ",
        "Heating_Wood_GJ",
        "Total_Heating_Energy_GJ",
    ]

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
                # Only process if Time and Heating_Load_GJ exist
                if "Time" not in df.columns or "Heating_Load_GJ" not in df.columns:
                    print(
                        f"[ERROR] File {current_file} missing required columns (Time, Heating_Load_GJ). Skipping."
                    )
                    error_files.append(current_file)
                    continue
                # Fill missing columns with zeros
                for col in [
                    "Heating_Propane_GJ",
                    "Heating_Oil_GJ",
                    "Heating_Electricity_GJ",
                    "Heating_Natural_Gas_GJ",
                    "Heating_Wood_GJ",
                ]:
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
        heating_load = np.zeros(n_rows)
        heating_propane = np.zeros(n_rows)
        heating_oil = np.zeros(n_rows)
        heating_electricity = np.zeros(n_rows)
        heating_natural_gas = np.zeros(n_rows)
        heating_wood = np.zeros(n_rows)

        for df in processed_dfs:
            heating_load += df["Heating_Load_GJ"].values
            heating_propane += df["Heating_Propane_GJ"].values
            heating_oil += df["Heating_Oil_GJ"].values
            heating_electricity += df["Heating_Electricity_GJ"].values
            heating_natural_gas += df["Heating_Natural_Gas_GJ"].values
            heating_wood += df["Heating_Wood_GJ"].values

        community_total = pd.DataFrame(
            {
                "Time": processed_dfs[0]["Time"].values,
                "Heating_Load_GJ": heating_load,
                "Heating_Propane_GJ": heating_propane,
                "Heating_Oil_GJ": heating_oil,
                "Heating_Electricity_GJ": heating_electricity,
                "Heating_Natural_Gas_GJ": heating_natural_gas,
                "Heating_Wood_GJ": heating_wood,
            }
        )
        successful_files_used = len(processed_dfs)
    else:
        community_total = None
        successful_files_used = 0

    if community_total is not None:
        # Always ensure correct columns and row count
        community_total["Total_Heating_Energy_GJ"] = (
            community_total["Heating_Propane_GJ"]
            + community_total["Heating_Oil_GJ"]
            + community_total["Heating_Electricity_GJ"]
            + community_total["Heating_Natural_Gas_GJ"]
            + community_total["Heating_Wood_GJ"]
        )
        # Truncate or pad to expected rows
        if len(community_total) > EXPECTED_ROWS:
            print(
                f"[WARNING] Output has {len(community_total)} rows, truncating to {EXPECTED_ROWS}."
            )
            community_total = community_total.iloc[:EXPECTED_ROWS]
        community_total = community_total[expected_columns]

        # Save the results
        base_communities_path = communities_dir()
        community_folder = base_communities_path / community_name
        community_folder.mkdir(parents=True, exist_ok=True)
        (community_folder / "analysis").mkdir(parents=True, exist_ok=True)
        output_file = community_folder / "analysis" / f"{community_name}-community_total.csv"
        community_total.to_csv(output_file, index=False)
        print(f"\nCommunity total energy use saved to:")
        print(f"  - {output_file} (community folder)")

        # Calculate statistics in GJ
        total_annual_load = community_total["Heating_Load_GJ"].sum()
        max_hourly_load = community_total["Heating_Load_GJ"].max()
        avg_hourly_load = community_total["Heating_Load_GJ"].mean()

        total_annual_propane = community_total["Heating_Propane_GJ"].sum()
        total_annual_oil = community_total["Heating_Oil_GJ"].sum()
        total_annual_electricity = community_total["Heating_Electricity_GJ"].sum()
        total_annual_natural_gas = community_total["Heating_Natural_Gas_GJ"].sum()
        total_annual_wood = community_total["Heating_Wood_GJ"].sum()
        total_annual_energy = (
            total_annual_propane
            + total_annual_oil
            + total_annual_electricity
            + total_annual_natural_gas
            + total_annual_wood
        )
        max_hourly_energy = community_total["Total_Heating_Energy_GJ"].max()
        avg_hourly_energy = community_total["Total_Heating_Energy_GJ"].mean()

        # Find the timestamp when max hourly energy occurs
        max_energy_idx = community_total["Total_Heating_Energy_GJ"].idxmax()
        max_energy_time = community_total.loc[max_energy_idx, "Time"]

        # Save the analysis results
        analysis_file = community_folder / "analysis" / f"{community_name}_analysis.md"
        with open(analysis_file, "w", encoding="utf-8") as f:
            f.write(f"# {community_name} Community Analysis\n\n")
            f.write("## Community Heating Load Statistics (what the houses need):\n")
            f.write(f"- Total Annual Load: {total_annual_load:,.1f} GJ\n")
            f.write(f"- Maximum Hourly Load: {max_hourly_load:,.3f} GJ\n")
            f.write(f"- Average Hourly Load: {avg_hourly_load:,.3f} GJ\n\n")
            f.write("## Community Heating Energy Use Statistics (what the equipment uses):\n")
            f.write(f"- Total Annual Energy: {total_annual_energy:,.1f} GJ\n")
            pct = lambda val: (val / total_annual_energy * 100) if total_annual_energy else 0
            f.write(
                f"  - Propane: {total_annual_propane:,.1f} GJ ({pct(total_annual_propane):,.1f}%)\n"
            )
            f.write(f"  - Oil: {total_annual_oil:,.1f} GJ ({pct(total_annual_oil):,.1f}%)\n")
            f.write(
                f"  - Electricity: {total_annual_electricity:,.1f} GJ ({pct(total_annual_electricity):,.1f}%)\n"
            )
            f.write(
                f"  - Natural Gas: {total_annual_natural_gas:,.1f} GJ ({pct(total_annual_natural_gas):,.1f}%)\n"
            )
            f.write(f"  - Wood: {total_annual_wood:,.1f} GJ ({pct(total_annual_wood):,.1f}%)\n")
            f.write(f"- Maximum Hourly Energy: {max_hourly_energy:,.3f} GJ\n")
            f.write(f"- Average Hourly Energy: {avg_hourly_energy:,.3f} GJ\n")
            if error_files:
                f.write(f"\n## Warnings and Errors Encountered:\n")
                for ef in error_files:
                    f.write(f"- Issue with file: {ef}\n")

            f.write(
                f"\nThe number of files that were successfully used in the analysis: {successful_files_used}/{len(selected_files)}\n"
            )

        print(f"\nAnalysis results saved to:")
        print(f"  - {analysis_file} (community folder)")

        # Save analysis data as JSON for frontend visualizations
        analysis_json_file = community_folder / "analysis" / f"{community_name}_analysis.json"
        analysis_data = {
            "community_name": community_name,
            "heating_load": {
                "total_annual_gj": float(total_annual_load),
                "max_hourly_gj": float(max_hourly_load),
                "avg_hourly_gj": float(avg_hourly_load),
            },
            "heating_energy": {
                "total_annual_gj": float(total_annual_energy),
                "max_hourly_gj": float(max_hourly_energy),
                "max_hourly_time": str(max_energy_time),
                "avg_hourly_gj": float(avg_hourly_energy),
                "by_source": {
                    "propane_gj": float(total_annual_propane),
                    "oil_gj": float(total_annual_oil),
                    "electricity_gj": float(total_annual_electricity),
                    "natural_gas_gj": float(total_annual_natural_gas),
                    "wood_gj": float(total_annual_wood),
                    "propane_percent": float(pct(total_annual_propane)),
                    "oil_percent": float(pct(total_annual_oil)),
                    "electricity_percent": float(pct(total_annual_electricity)),
                    "natural_gas_percent": float(pct(total_annual_natural_gas)),
                    "wood_percent": float(pct(total_annual_wood)),
                },
            },
        }
        with open(analysis_json_file, "w", encoding="utf-8") as f:
            json.dump(analysis_data, f, indent=2)
        print(f"  - {analysis_json_file} (community folder - JSON)")

        print("\nCommunity Heating Load Statistics (what the houses need):")
        print(f"Total Annual Load: {total_annual_load:,.1f} GJ")
        print(f"Maximum Hourly Load: {max_hourly_load:,.3f} GJ")
        print(f"Average Hourly Load: {avg_hourly_load:,.3f} GJ")

        print("\nCommunity Heating Energy Use Statistics (what the equipment uses):")
        print(f"Total Annual Energy: {total_annual_energy:,.1f} GJ")
        print(f"- Propane: {total_annual_propane:,.1f} GJ ({pct(total_annual_propane):,.1f}%)")
        print(f"- Oil: {total_annual_oil:,.1f} GJ ({pct(total_annual_oil):,.1f}%)")
        print(
            f"- Electricity: {total_annual_electricity:,.1f} GJ ({pct(total_annual_electricity):,.1f}%)"
        )
        print(
            f"- Natural Gas: {total_annual_natural_gas:,.1f} GJ ({pct(total_annual_natural_gas):,.1f}%)"
        )
        print(f"- Wood: {total_annual_wood:,.1f} GJ ({pct(total_annual_wood):,.1f}%)")
        print(f"Maximum Hourly Energy: {max_hourly_energy:,.3f} GJ")
        print(f"Average Hourly Energy: {avg_hourly_energy:,.3f} GJ")
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
        custom_rq_file_path = csv_dir() / "communities-number-of-houses.csv"
        parser = argparse.ArgumentParser(description="Calculate community total energy use.")
        parser.add_argument(
            "community_name", type=str, help="Name of the community (e.g., BONILLA-ISLAND)"
        )
        parser.add_argument(
            "--requirements",
            type=str,
            help="Path to custom requirements file",
            default=str(custom_rq_file_path),
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
