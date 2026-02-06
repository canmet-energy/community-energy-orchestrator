#!/usr/bin/env python3
"""
Debug and validation module for community energy analysis.
Validates timeseries outputs and weather location codes in H2K files.
"""

from pathlib import Path
from change_weather_location_regex import load_csv_data
import xml.etree.ElementTree as ET
from process_community_workflow import get_community_requirements, get_max_workers
import sys
import csv
from concurrent.futures import ProcessPoolExecutor, as_completed

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
    output_base = Path(__file__).resolve().parent.parent / f'communities/{community_name}/archetypes/output'
    debug_log_path = Path(__file__).resolve().parent.parent / f'communities/{community_name}/analysis/output_debug.log'
    
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
            matches = [p for p in output_base.glob(f'{era_type}_*/run/results_timeseries.csv')]
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
    with open(debug_log_path, 'w') as f:
        f.write(f"Timeseries output debug for {community_name}\n")
        
        # Write summary for all housing types
        for era_type in requirements:
            f.write(f"{era_type}: required={requirements[era_type]}, found={found_counts[era_type]}\n")
        
        # Write detailed list of missing files if any
        if missing:
            f.write("\nMissing timeseries outputs by type:\n")
            for k, v in missing.items():
                f.write(f"{k}: {v} missing\n")
        else:
            f.write("\nAll required timeseries outputs found.\n")
    
    return debug_log_path

def _validate_single_h2k(h2k_file, community_name):
    """Validate weather location code for a single H2K file. Module-level for pickling."""
    try:
        with open(h2k_file, 'r', encoding='latin-1') as file:
            contents = file.read()

        if not contents.strip().startswith('<?xml') and not contents.strip().startswith('<HouseFile'):
            return (h2k_file, "Not an XML H2K file.", None)
        
        location_code = get_location_code_from_h2k(h2k_file)

        if location_code is None:
            return (h2k_file, "Could not find location code in H2K file.", None)

        is_valid = validate_location_code(community_name, location_code)

        if not is_valid:
            return (h2k_file, f"Location Code: {location_code}\n  Validation: FAILED (does not match expected code for {community_name})", location_code)
        
        return (h2k_file, None, location_code)  # None means validation passed
                    
    except Exception as e:
        return (h2k_file, f"Error processing file: {e}", None)


def debug_weather_h2k(community_name):
    """
    Validate weather location codes in H2K archetype files.
    
    Args:
        community_name (str): Name of the community
    
    Returns:
        Path: Path to the debug log file
        
    Writes to:
        communities/<community>/analysis/output_debug.log (appends)
    """
    # Define paths for archetype directory and debug log
    archetype_base = Path(__file__).resolve().parent.parent / 'communities' / community_name / 'archetypes'
    debug_log_path = Path(__file__).resolve().parent.parent / 'communities' / community_name / 'analysis' / 'output_debug.log'

    # Create parent directory if needed
    debug_log_path.parent.mkdir(parents=True, exist_ok=True)

    # Find all H2K files
    h2k_files = list(archetype_base.glob('**/*.H2K'))
    
    if not h2k_files:
        with open(debug_log_path, 'a') as log_file:
            log_file.write(f"\n\nWeather Location Code Validation\n\n")
            log_file.write("No H2K files found.\n")
        return debug_log_path
    
    # Process files in parallel
    max_workers = min(get_max_workers(), len(h2k_files))
    print(f"[PARALLEL] Validating weather location in {len(h2k_files)} H2K files with {max_workers} workers")
    
    validation_results = []
    with ProcessPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(_validate_single_h2k, h2k_file, community_name): h2k_file for h2k_file in h2k_files}
        
        for future in as_completed(futures):
            try:
                result = future.result()
                validation_results.append(result)
            except Exception as e:
                h2k_file = futures[future]
                validation_results.append((h2k_file, f"Exception during validation: {e}", None))
    
    # Write all results to log file after parallel processing completes
    validation_issues = 0
    with open(debug_log_path, 'a') as log_file:
        log_file.write(f"\n\nWeather Location Code Validation\n\n")
        
        for h2k_file, error_msg, location_code in validation_results:
            if error_msg is not None:
                log_file.write(f"H2K File: {h2k_file}\n")
                log_file.write(f"  {error_msg}\n")
                validation_issues += 1
        
        if validation_issues == 0:
            log_file.write("All H2K files passed location code validation.\n")
    
    return debug_log_path



def get_location_code_from_h2k(file_path):
    """
    Extract weather location code from H2K XML file.
    
    Args:
        file_path (Path or str): Path to the H2K XML file
    
    Returns:
        str: Location code (e.g., "400"), or None if not found
    """
    try:
        # Parse the XML file into an element tree
        tree = ET.parse(file_path)
        root = tree.getroot()

        # Navigate to Weather -> Location using XPath
        # .// means "search anywhere in the tree"
        weather = root.find('.//Weather')
        if weather is not None:
            location = weather.find('Location')
            if location is not None:
                # Get the 'code' attribute from the Location element
                code = location.get('code')
                return code
        return None

    except ET.ParseError as e:
        print(f'Error parsing XML: {e}')
        return None
    

def validate_location_code(community_name, location_code):
    """
    Validate that location code matches expected code for community's weather location.
    
    Communities use weather data from nearby weather stations, not necessarily their own location.
    This function looks up which weather location the community uses, then validates against that.
    
    Args:
        community_name (str): Name of the community
        location_code (str): Location code from H2K file
    
    Returns:
        bool: True if code matches the weather location code for this community, False otherwise
    """
    if location_code is None:
        return False
    
    # First, get the weather location for this community
    weather_locations_path = Path(__file__).resolve().parent.parent / 'csv' / 'train-test communities hdd and weather locations.csv'
    
    if not weather_locations_path.exists():
        return False
    
    # Find the weather location for this community
    weather_location = None
    comm_upper = community_name.upper()
    
    with open(weather_locations_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row['Community'].strip().upper() == comm_upper:
                weather_location = row['WEATHER'].strip()
                break
    
    if weather_location is None:
        return False
    
    # Now load the location codes CSV to get the code for that weather location
    location_codes_path = Path(__file__).resolve().parent.parent / 'csv' / 'location_code.csv'
    
    if not location_codes_path.exists():
        return False
    
    location_codes = load_csv_data(location_codes_path)
    
    # Look up expected code for the weather location (case-insensitive lookup)
    expected_code = location_codes.get(weather_location.upper())
    if expected_code is None:
        return False

    # Compare as strings to handle different data types
    return str(location_code) == str(expected_code)


def main(community_name):
    """
    Run all debug checks and write to output_debug.log.
    
    Args:
        community_name (str): Name of the community
        
    Returns:
        Path: Path to the debug log file
    """
    # Run timeseries debug first (mode 'w' creates/overwrites file)
    debug_log_path = debug_timeseries_outputs(community_name)
    
    # Run weather debug second (mode 'a' appends to existing file)
    debug_weather_h2k(community_name)
    
    return debug_log_path


if __name__ == "__main__":
    # Allow running this script standalone for debugging
    # Usage: python debug_outputs.py "Old Crow"
    if len(sys.argv) < 2:
        print("Usage: python debug_outputs.py <community_name>")
        sys.exit(1)
        
    community_name = sys.argv[1]
    log_path = main(community_name)
    print(f"Debug log written to: {log_path}")
