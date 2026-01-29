#!/usr/bin/env python3
"""
Debug and validation module for community energy analysis.
Validates timeseries outputs and weather location codes in H2K files.
"""

import os
from pathlib import Path
from change_weather_location_regex import load_csv_data
import xml.etree.ElementTree as ET
from process_community_workflow import get_community_requirements
import sys

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
            f.write(f"\n{community_name}: TODO - # of files actually used in analysis")
    
    return debug_log_path

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

    # Keep track of validation issues found
    validation_issues = 0
    
    # Open log file in append mode to add weather validation after timeseries results
    with open(debug_log_path, 'a') as log_file:
        log_file.write(f"\n\nWeather Location Code Validation\n\n")
        
        # Iterate through all H2K files (recursively searches subdirectories)
        for f in archetype_base.glob('**/*.H2K'):
            try:
                # Read the H2K file contents (H2K files use latin-1 encoding)
                with open(f, 'r', encoding='latin-1') as file:
                    contents = file.read()

                # Verify it's a valid XML file (H2K files are XML-based)
                # Must start with either <?xml or <HouseFile tag
                if not contents.strip().startswith('<?xml') and not contents.strip().startswith('<HouseFile'):
                    log_file.write(f"H2K File: {f}\n")
                    log_file.write(f"  Not an XML H2K file.\n")
                    validation_issues += 1
                    continue
                
                # Extract the location code from the XML structure
                location_code = get_location_code_from_h2k(f)

                if location_code is None:
                    log_file.write(f"H2K File: {f}\n")
                    log_file.write(f"  Could not find location code in H2K file.\n")
                    validation_issues += 1
                    continue

                # Check if the location code matches the expected code for this community
                is_valid = validate_location_code(community_name, location_code)

                # Only log failures (keeps log concise for large numbers of files)
                if not is_valid:
                    log_file.write(f"H2K File: {f}\n")
                    log_file.write(f"  Location Code: {location_code}\n")
                    log_file.write(f"  Validation: FAILED (does not match expected code for {community_name})\n")
                    validation_issues += 1
                    continue
                    
            except Exception as e:
                # Log any unexpected errors during processing
                log_file.write(f"H2K File: {f}\n")
                log_file.write(f"  Error processing file: {e}\n")
                validation_issues += 1
                continue
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
    Validate that location code matches expected code for community.
    
    Args:
        community_name (str): Name of the community
        location_code (str): Location code from H2K file
    
    Returns:
        bool: True if code matches, False otherwise
    """
    # Load the location codes CSV file (format: {community_name: code, ...})
    location_codes_path = Path(__file__).resolve().parent.parent / 'csv' / 'location_code.csv'
    location_codes = load_csv_data(location_codes_path)

    if location_code is None:
        return False
    
    # Look up expected code for this community (case-insensitive lookup)
    expected_code = location_codes.get(community_name.upper())
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
