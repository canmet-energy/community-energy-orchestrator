#!/usr/bin/env python3
import pandas as pd
import numpy as np
from pathlib import Path
import glob
import argparse
import sys
import os
import traceback
import random

# Conversion factor from kBtu to GJ
KBTU_TO_GJ = 0.001055056

def read_timeseries(file_path):
    """Load and process timeseries data from CSV file."""
    file_path_obj = Path(file_path)
    if not file_path_obj.exists():
        raise FileNotFoundError(f"Timeseries file not found: {file_path}")
    
    # Load timeseries data
    df = pd.read_csv(file_path)
    
    # Get heating load (what the house needs)
    df["Heating_Load_GJ"] = pd.to_numeric(df["Load: Heating: Delivered"], errors='coerce') * KBTU_TO_GJ
    
    # Get heating fuel use (what equipment uses)
    # Try to find electricity, propane, and oil columns
    elec_cols = ["End Use: Electricity: Heating", "System Use: HeatingSystem1: Electricity: Heating"]
    oil_cols = ["End Use: Fuel Oil: Heating", "System Use: HeatingSystem1: Fuel Oil: Heating"]
    propane_cols = ["End Use: Propane: Heating", "System Use: HeatingSystem1: Propane: Heating"]

    # Electricity
    for col in elec_cols:
        if col in df.columns:
            df["Heating_Electricity_GJ"] = pd.to_numeric(df[col], errors='coerce') * KBTU_TO_GJ
            print(f"Using electricity column: {col}")
            break
    else:
        df["Heating_Electricity_GJ"] = 0
        print("No electricity column found!")

    # Fuel Oil
    for col in oil_cols:
        if col in df.columns:
            df["Heating_Oil_GJ"] = pd.to_numeric(df[col], errors='coerce') * KBTU_TO_GJ
            print(f"Using oil column: {col}")
            break
    else:
        df["Heating_Oil_GJ"] = 0
        print("No oil column found!")

    # Propane
    for col in propane_cols:
        if col in df.columns:
            df["Heating_Propane_GJ"] = pd.to_numeric(df[col], errors='coerce') * KBTU_TO_GJ
            print(f"Using propane column: {col}")
            break
    else:
        df["Heating_Propane_GJ"] = 0
        print("No propane column found!")

    return df

# Default requirements file
REQUIREMENTS_FILE = Path(__file__).resolve().parent.parent / 'csv' / 'train-test communities number of housing types.csv'

def load_community_requirements(community_name):
    """
    Load the community requirements from the CSV file.
    Returns a dictionary of building types and counts.
    """
    if not REQUIREMENTS_FILE.exists():
        raise FileNotFoundError(f"Requirements file not found: {REQUIREMENTS_FILE}")
    
    try:
        # Try UTF-8 encoding first
        df = pd.read_csv(REQUIREMENTS_FILE, header=None, encoding='utf-8')
    except UnicodeDecodeError:
        # Fall back to latin1 if UTF-8 fails
        df = pd.read_csv(REQUIREMENTS_FILE, header=None, encoding='latin1')
    
    # Find the row for the specified community
    community_row = None
    for i, row in df.iterrows():
        if i > 0 and row[0] and isinstance(row[0], str) and row[0].strip().upper() == community_name.strip().upper():
            community_row = row
            break
        
    print(f"Looking for community: '{community_name}' in requirements file")
    if community_row is None:
        print("Available communities:")
        for i, row in df.iterrows():
            if i > 0 and row[0] and isinstance(row[0], str):
                print(f"  - '{row[0]}'")
        print("Community not found. Using available files instead.")
        return {}
        
    # Parse the requirements from the community row
    # Format in CSV: community, building_type1, count1, building_type2, count2, ...
    requirements = {}
    for i in range(1, len(community_row), 2):
        # Skip if we've reached the end of data
        if i+1 >= len(community_row) or pd.isna(community_row[i]) or pd.isna(community_row[i+1]):
            continue
            
        building_type = community_row[i].strip()
        count = int(community_row[i+1])
        if count > 0:  # Only include types with count > 0
            requirements[building_type] = count
    
    print(f"Found {len(requirements)} building types for {community_name}:")
    for building_type, count in requirements.items():
        print(f"  - {building_type}: {count} units")
        
    return requirements

def select_and_sum_timeseries(community_name):
    print(f"Processing community: {community_name}")
    # Get requirements from CSV file
    requirements = load_community_requirements(community_name)

    # Try multiple variations of the directory name
    community_hyphen = community_name.replace(" ", "-")
    community_upper = community_name.upper()
    community_upper_hyphen = community_upper.replace(" ", "-")

    # Extract archetype prefix from requirements keys (e.g., OLD-CROW)
    archetype_prefixes = set()
    for k in requirements.keys():
        prefix = k.split('-')[0]
        archetype_prefixes.add(prefix)
    base_path = Path(__file__).resolve().parent.parent / 'communities'
    timeseries_dirs = [
        base_path /  f'{community_hyphen}-all_timeseries',
        base_path /  f'{community_name}-all_timeseries',
        base_path /  f'{community_upper}-all_timeseries',
        base_path /  f'{community_upper_hyphen}-all_timeseries',
        base_path / community_name / 'timeseries',
        base_path / community_hyphen / 'timeseries',
        base_path / community_upper / 'timeseries',
        base_path / community_upper_hyphen / 'timeseries',
    ]
    # Add archetype prefix variants
    for prefix in archetype_prefixes:
        timeseries_dirs.append(Path(__file__).resolve().parent.parent / f'{prefix}-all_timeseries')
        timeseries_dirs.append(Path(__file__).resolve().parent.parent / 'communities' / prefix / 'timeseries')

    # Find the directory that exists
    timeseries_dir = None
    for dir_path in timeseries_dirs:
        if dir_path.exists():
            timeseries_dir = dir_path
            break

    if timeseries_dir is None:
        # If still not found, try to find by partial match
        all_dirs = [d for d in Path(__file__).resolve().parent.parent.iterdir() if d.is_dir()]
        for d in all_dirs:
            if 'all_timeseries' in d.name and any(variant in d.name.upper() for variant in 
                                              [community_name.upper(), community_hyphen.upper()]):
                timeseries_dir = d
                break

    if timeseries_dir is None:
        raise ValueError(f"Directory not found for {community_name}. Tried various naming formats including hyphen, space, and communities/<community>/timeseries.")

    print(f"Using timeseries directory: {timeseries_dir}")

    # Archetype source directory for fallback
    archetype_source_dir = Path(__file__).resolve().parent / 'source-archetypes'
        
    # If no requirements, use all available files
    if not requirements:
        print("\nNo specific requirements found. Using all available files.")
        # Scan directory for available files and build requirements
        building_types = {}
        
        # Define mapping between requirement keys and file patterns
        type_patterns = {
            "OLD-CROW-pre-2000-single": ["pre-2000-single"],
            "OLD-CROW-2001-2015-single": ["2001-2015-single"],
            "OLD-CROW-pre-2000-semi": ["pre-2000-double"],
            "OLD-CROW-2001-2015-semi": ["2001-2015-double", "post-2016-double"],
            "OLD-CROW-pre-2000-row-mid": ["pre-2000-row-end"],  # Using row-end files for mid
            "OLD-CROW-2001-2015-row-mid": ["post-2016-row-middle"],
            "OLD-CROW-pre-2000-row-end": ["pre-2000-row-end"],
            "OLD-CROW-2001-2015-row-end": ["post-2016-row-end"]
        }
        
        for file_path in glob.glob(str(timeseries_dir / '*-results_timeseries.csv')):
            filename = Path(file_path).name
            print(f"Found file: {filename}")
            for req_type, patterns in type_patterns.items():
                for pattern in patterns:
                    if pattern in filename:
                        if req_type not in building_types:
                            building_types[req_type] = 0
                        building_types[req_type] += 1
                        break  # Once a match is found, stop checking other patterns
        
        requirements = building_types
    
    print("\nFinding available files...")
    files_by_type = {k: [] for k in requirements.keys()}

    # Helper to find files for a type in a directory
    def find_files_for_type(directory, req_key):
        # Use the full req_key for matching filenames
        building_type = req_key
        found_files = []
        for file_path in glob.glob(str(directory / '*-results_timeseries.csv')):
            filename = Path(file_path).name
            # For 'semi' requirements, also include 'double' files for the same era
            if building_type.endswith('semi'):
                era = '-'.join(building_type.split('-')[:2]) if '-' in building_type else building_type
                semi_prefix = f"{era}-semi_"
                double_prefix = f"{era}-double_"
                if (filename.startswith(semi_prefix) or filename.startswith(double_prefix)) and filename.endswith("-results_timeseries.csv"):
                    found_files.append(file_path)
            else:
                if filename.startswith(f"{building_type}_") and filename.endswith("-results_timeseries.csv"):
                    found_files.append(file_path)
        return found_files

    # First, find files in the main timeseries directory
    for req_key in requirements.keys():
        files_by_type[req_key] = find_files_for_type(timeseries_dir, req_key)

    # For any type with a shortage, look in archetype source directory
    for req_key, required_count in requirements.items():
        if len(files_by_type[req_key]) < required_count:
            print(f"Shortage for {req_key}: found {len(files_by_type[req_key])}, required {required_count}. Searching archetype source directory...")
            extra_files = find_files_for_type(archetype_source_dir, req_key)
            # Only add files not already present
            new_files = [f for f in extra_files if f not in files_by_type[req_key]]
            files_by_type[req_key].extend(new_files)
            print(f"Added {len(new_files)} files from archetype source directory for {req_key}.")

    print("\nSummary by housing type (files found):")
    for building_type, files in files_by_type.items():
        print(f"  {building_type}: {len(files)} files found (required: {requirements[building_type]})")
        if len(files) < requirements[building_type]:
            print(f"WARNING: Not enough files found for {building_type}. Found {len(files)}, required {requirements[building_type]}. Will duplicate or skip as needed.")

    # Only process the exact number required for each type
    selected_files = []
    for building_type, required_count in requirements.items():
        available_files = files_by_type[building_type]
        if len(available_files) < required_count:
            print(f"WARNING: Not enough files for {building_type}. Found {len(available_files)}, required {required_count}. Duplicating as needed.")
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
    
    # Aggregation logic with robust error handling
    print("\nProcessing selected files...")
    community_total = None
    first_file = True
    error_files = []
    successful_files_used = 0
    expected_rows = 8761
    expected_columns = ["Time", "Heating_Load_GJ", "Heating_Propane_GJ", "Heating_Oil_GJ", "Heating_Electricity_GJ", "Total_Heating_Energy_GJ"]

    for file_path in selected_files:
        try:
            df = read_timeseries(file_path)
            # Check for expected row count
            if len(df) != expected_rows:
                print(f"[WARNING] File {file_path} has {len(df)} rows, expected {expected_rows}.")
            # Check for missing columns
            missing_cols = [col for col in ["Time", "Heating_Load_GJ", "Heating_Propane_GJ", "Heating_Oil_GJ", "Heating_Electricity_GJ"] if col not in df.columns]
            if missing_cols:
                print(f"[WARNING] File {file_path} is missing columns: {missing_cols}")
            # Only process if Time and Heating_Load_GJ exist
            if "Time" not in df.columns or "Heating_Load_GJ" not in df.columns:
                print(f"[ERROR] File {file_path} missing required columns. Skipping.")
                error_files.append(file_path)
                continue
            # Fill missing columns with zeros
            for col in ["Heating_Propane_GJ", "Heating_Oil_GJ", "Heating_Electricity_GJ"]:
                if col not in df.columns:
                    df[col] = 0
            if first_file:
                community_total = pd.DataFrame({'Time': df['Time']})
                community_total['Heating_Load_GJ'] = df['Heating_Load_GJ']
                community_total['Heating_Propane_GJ'] = df['Heating_Propane_GJ']
                community_total['Heating_Oil_GJ'] = df['Heating_Oil_GJ']
                community_total['Heating_Electricity_GJ'] = df['Heating_Electricity_GJ']
                first_file = False
            else:
                # Align on Time column to avoid concatenation errors
                if not community_total['Time'].equals(df['Time']):
                    print(f"[WARNING] Time columns do not match for {file_path}. Attempting to align by index.")
                community_total['Heating_Load_GJ'] = community_total['Heating_Load_GJ'].add(df['Heating_Load_GJ'], fill_value=0)
                community_total['Heating_Propane_GJ'] = community_total['Heating_Propane_GJ'].add(df['Heating_Propane_GJ'], fill_value=0)
                community_total['Heating_Oil_GJ'] = community_total['Heating_Oil_GJ'].add(df['Heating_Oil_GJ'], fill_value=0)
                community_total['Heating_Electricity_GJ'] = community_total['Heating_Electricity_GJ'].add(df['Heating_Electricity_GJ'], fill_value=0)
            print(f"Processed: {Path(file_path).stem}")
            successful_files_used += 1
        except Exception as e:
            print(f"[ERROR] Exception processing {file_path}: {e}")
            error_files.append(file_path)
            continue

    if community_total is not None:
        # Always ensure correct columns and row count
        community_total['Total_Heating_Energy_GJ'] = community_total['Heating_Propane_GJ'] + community_total['Heating_Oil_GJ'] + community_total['Heating_Electricity_GJ']
        # Truncate or pad to expected rows
        if len(community_total) > expected_rows:
            print(f"[WARNING] Output has {len(community_total)} rows, truncating to {expected_rows}.")
            community_total = community_total.iloc[:expected_rows]
        elif len(community_total) < expected_rows:
            print(f"[WARNING] Output has {len(community_total)} rows, padding with zeros to {expected_rows}.")
            pad_rows = expected_rows - len(community_total)
            pad_df = pd.DataFrame(0, index=range(pad_rows), columns=community_total.columns)
            pad_df['Time'] = [f"PAD_{i}" for i in range(pad_rows)]
            community_total = pd.concat([community_total, pad_df], ignore_index=True)
        # Ensure columns order
        for col in expected_columns:
            if col not in community_total.columns:
                community_total[col] = 0
        community_total = community_total[expected_columns]

        # Save the results
        base_communities_path = Path(__file__).resolve().parent.parent / 'communities'
        community_folder = base_communities_path / community_name.replace('-', '_')
        
        # Safety check for path
        try:
            community_folder.resolve().relative_to(base_communities_path.resolve())
        except ValueError:
            raise ValueError(f"Safety check failed: community folder path is outside communities directory")
        
        community_folder.mkdir(parents=True, exist_ok=True)
        (community_folder / 'analysis').mkdir(parents=True, exist_ok=True)
        output_file = community_folder / 'analysis' / f'{community_name}-community_total.csv'
        community_total.to_csv(output_file, index=False)
        print(f"\nCommunity total energy use saved to:")
        print(f"  - {output_file} (community folder)")

        # Calculate statistics in GJ
        total_annual_load = community_total['Heating_Load_GJ'].sum()
        max_hourly_load = community_total['Heating_Load_GJ'].max()
        avg_hourly_load = community_total['Heating_Load_GJ'].mean()

        total_annual_propane = community_total['Heating_Propane_GJ'].sum()
        total_annual_oil = community_total['Heating_Oil_GJ'].sum()
        total_annual_electricity = community_total['Heating_Electricity_GJ'].sum()
        total_annual_energy = total_annual_propane + total_annual_oil + total_annual_electricity
        max_hourly_energy = community_total['Total_Heating_Energy_GJ'].max()
        avg_hourly_energy = community_total['Total_Heating_Energy_GJ'].mean()

        # Save the analysis results
        analysis_file = community_folder / 'analysis' / f'{community_name}_analysis.md'
        with open(analysis_file, 'w') as f:
            f.write(f"# {community_name} Community Analysis\n\n")
            f.write("## Community Heating Load Statistics (what the houses need):\n")
            f.write(f"- Total Annual Load: {total_annual_load:,.1f} GJ\n")
            f.write(f"- Maximum Hourly Load: {max_hourly_load:,.3f} GJ\n")
            f.write(f"- Average Hourly Load: {avg_hourly_load:,.3f} GJ\n\n")
            f.write("## Community Heating Energy Use Statistics (what the equipment uses):\n")
            f.write(f"- Total Annual Energy: {total_annual_energy:,.1f} GJ\n")
            f.write(f"  - Propane: {total_annual_propane:,.1f} GJ ({(total_annual_propane/total_annual_energy*100) if total_annual_energy else 0:,.1f}%)\n")
            f.write(f"  - Oil: {total_annual_oil:,.1f} GJ ({(total_annual_oil/total_annual_energy*100) if total_annual_energy else 0:,.1f}%)\n")
            f.write(f"  - Electricity: {total_annual_electricity:,.1f} GJ ({(total_annual_electricity/total_annual_energy*100) if total_annual_energy else 0:,.1f}%)\n")
            f.write(f"- Maximum Hourly Energy: {max_hourly_energy:,.3f} GJ\n")
            f.write(f"- Average Hourly Energy: {avg_hourly_energy:,.3f} GJ\n")
            if error_files:
                f.write(f"\n## Warnings and Errors Encountered:\n")
                for ef in error_files:
                    f.write(f"- Issue with file: {ef}\n")

            f.write(f"\nThe number of files that were successfully used in the analysis: {successful_files_used}/{len(selected_files)}\n")

        print(f"\nAnalysis results saved to:")
        print(f"  - {analysis_file} (community folder)")

        print("\nCommunity Heating Load Statistics (what the houses need):")
        print(f"Total Annual Load: {total_annual_load:,.1f} GJ")
        print(f"Maximum Hourly Load: {max_hourly_load:,.3f} GJ")
        print(f"Average Hourly Load: {avg_hourly_load:,.3f} GJ")

        print("\nCommunity Heating Energy Use Statistics (what the equipment uses):")
        print(f"Total Annual Energy: {total_annual_energy:,.1f} GJ")
        print(f"- Propane: {total_annual_propane:,.1f} GJ ({(total_annual_propane/total_annual_energy*100) if total_annual_energy else 0:,.1f}%)")
        print(f"- Oil: {total_annual_oil:,.1f} GJ ({(total_annual_oil/total_annual_energy*100) if total_annual_energy else 0:,.1f}%)")
        print(f"- Electricity: {total_annual_electricity:,.1f} GJ ({(total_annual_electricity/total_annual_energy*100) if total_annual_energy else 0:,.1f}%)")
        print(f"Maximum Hourly Energy: {max_hourly_energy:,.3f} GJ")
        print(f"Average Hourly Energy: {avg_hourly_energy:,.3f} GJ")
        if error_files:
            print("\n[ALERT] Some input files had issues and were skipped or partially processed. See analysis markdown for details.")
        print(f"\nAnalysis saved to: {analysis_file}")
    else:
        print("No files were successfully processed. [ALERT] No valid input files for aggregation.")
        
if __name__ == '__main__':
    try:
        custom_rq_file_path = Path(__file__).resolve().parent.parent / 'csv' / 'train-test communities number of housing types.csv'
        parser = argparse.ArgumentParser(description='Calculate community total energy use.')
        parser.add_argument('community_name', type=str, help='Name of the community (e.g., BONILLA-ISLAND)')
        parser.add_argument('--requirements', type=str, help='Path to custom requirements file', default=str(custom_rq_file_path))
        
        args = parser.parse_args()
        print(f"Starting analysis for {args.community_name}...")
        
        # Convert requirements path to Path object
        requirements_path = Path(args.requirements)
        
        # Check if requirements file exists
        if not requirements_path.exists():
            raise FileNotFoundError(f"Requirements file '{requirements_path}' not found")
            
        # Update the requirements file path
        REQUIREMENTS_FILE = requirements_path
            
        select_and_sum_timeseries(args.community_name)
        print("Script finished.")
    except FileNotFoundError as e:
        print(f"Error: {e}")
    except ValueError as e:
        print(f"Error: {e}")
    except Exception as e:
        print(f"Unexpected error: {e}")
        traceback.print_exc()