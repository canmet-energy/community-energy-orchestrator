#!/usr/bin/env python3
"""
Change weather location in H2K files using regex-based replacement.

This script modifies ONLY the Region/English and Location/English fields
in the H2K Weather section, which are the only fields actually used by
h2k-hpxml to determine the CWEC weather file. All other attributes
(HDD, library, location codes, French names, etc.) are left unchanged.

The h2k-hpxml library looks up weather files based solely on:
  - Region English name (e.g., "NORTHWEST TERRITORIES")
  - Location English name (e.g., "FORT SIMPSON")

These are matched against the h2k_weather_names.csv file in h2k-hpxml
to find the appropriate CWEC2020 weather file.
"""

import argparse
import os
import re
import sys
from pathlib import Path

# Enable UTF-8 mode for Windows compatibility with special characters
if sys.platform == "win32":
    # Set Python to use UTF-8 for file I/O and console output
    os.environ.setdefault("PYTHONUTF8", "1")

    # Reconfigure stdout/stderr to use UTF-8
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")

from workflow.core import csv_dir


def get_region_for_location(location):
    """Get the region code and English/French names for a location"""
    # Map locations to regions
    location_map = {
        # British Columbia (Region 1)
        "BONILLA ISLAND": ("1", "BRITISH COLUMBIA", "COLOMBIE-BRITANNIQUE"),
        "DEASE LAKE": ("1", "BRITISH COLUMBIA", "COLOMBIE-BRITANNIQUE"),
        "ESTEVAN POINT": ("1", "BRITISH COLUMBIA", "COLOMBIE-BRITANNIQUE"),
        "FORT NELSON": ("1", "BRITISH COLUMBIA", "COLOMBIE-BRITANNIQUE"),
        "PORT HARDY": ("1", "BRITISH COLUMBIA", "COLOMBIE-BRITANNIQUE"),
        "PRINCE GEORGE": ("1", "BRITISH COLUMBIA", "COLOMBIE-BRITANNIQUE"),
        "PUNTZI MOUNTAIN": ("1", "BRITISH COLUMBIA", "COLOMBIE-BRITANNIQUE"),
        "ROSE SPIT": ("1", "BRITISH COLUMBIA", "COLOMBIE-BRITANNIQUE"),
        "SALMON ARM": ("1", "BRITISH COLUMBIA", "COLOMBIE-BRITANNIQUE"),
        "SARTINE ISLAND": ("1", "BRITISH COLUMBIA", "COLOMBIE-BRITANNIQUE"),
        "SHERINGHAM POINT": ("1", "BRITISH COLUMBIA", "COLOMBIE-BRITANNIQUE"),
        # Saskatchewan (Region 3)
        "COLLINS BAY": ("3", "SASKATCHEWAN", "SASKATCHEWAN"),
        # Newfoundland and Labrador (Region 5)
        "MARY'S HARBOUR": ("5", "NEWFOUNDLAND AND LABRADOR", "TERRE-NEUVE-ET-LABRADOR"),
        "BONAVISTA": ("5", "NEWFOUNDLAND AND LABRADOR", "TERRE-NEUVE-ET-LABRADOR"),
        "BURGEO": ("5", "NEWFOUNDLAND AND LABRADOR", "TERRE-NEUVE-ET-LABRADOR"),
        "CARTWRIGHT": ("5", "NEWFOUNDLAND AND LABRADOR", "TERRE-NEUVE-ET-LABRADOR"),
        "ST-LAWRENCE": ("5", "NEWFOUNDLAND AND LABRADOR", "TERRE-NEUVE-ET-LABRADOR"),
        # Quebec (Region 6)
        "CHAMOUCHOUANE": ("6", "QUEBEC", "QUÉBEC"),
        "INUKJUAK": ("6", "QUEBEC", "QUÉBEC"),
        "KUUJJUAQ": ("6", "QUEBEC", "QUÉBEC"),
        "KUUJJUARAPIK": ("6", "QUEBEC", "QUÉBEC"),
        "NATASHQUAN": ("6", "QUEBEC", "QUÉBEC"),
        "VAL-D'OR": ("6", "QUEBEC", "QUÉBEC"),
        "ÎLES DE LA MADELEINE": ("6", "QUEBEC", "QUÉBEC"),
        # Ontario (Region 7)
        "ARMSTRONG": ("7", "ONTARIO", "ONTARIO"),
        "LANSDOWNE HOUSE": ("7", "ONTARIO", "ONTARIO"),
        "NAGAGAMI": ("7", "ONTARIO", "ONTARIO"),
        "PEAWANUCK": ("7", "ONTARIO", "ONTARIO"),
        "TIMMINS": ("7", "ONTARIO", "ONTARIO"),
        # Manitoba (Region 8)
        "GILLAM": ("8", "MANITOBA", "MANITOBA"),
        "TADOULE LAKE": ("8", "MANITOBA", "MANITOBA"),
        # Yukon (Region 11)
        "BURWASH": ("11", "YUKON", "YUKON"),
        "OLD CROW": ("11", "YUKON", "YUKON"),
        "WATSON LAKE": ("11", "YUKON", "YUKON"),
        # Northwest Territories (Region 12)
        "DÉLINE": ("12", "NORTHWEST TERRITORIES", "TERRITOIRES DU NORD-OUEST"),
        "FORT GOOD HOPE": ("12", "NORTHWEST TERRITORIES", "TERRITOIRES DU NORD-OUEST"),
        "FORT LIARD": ("12", "NORTHWEST TERRITORIES", "TERRITOIRES DU NORD-OUEST"),
        "FORT PROVIDENCE": ("12", "NORTHWEST TERRITORIES", "TERRITOIRES DU NORD-OUEST"),
        "FORT SIMPSON": ("12", "NORTHWEST TERRITORIES", "TERRITOIRES DU NORD-OUEST"),
        "FORT SMITH": ("12", "NORTHWEST TERRITORIES", "TERRITOIRES DU NORD-OUEST"),
        "HOLMAN": ("12", "NORTHWEST TERRITORIES", "TERRITOIRES DU NORD-OUEST"),
        "LAC LA MARTRE": ("12", "NORTHWEST TERRITORIES", "TERRITOIRES DU NORD-OUEST"),
        "LITTLE CHICAGO": ("12", "NORTHWEST TERRITORIES", "TERRITOIRES DU NORD-OUEST"),
        "LOWER CARP LAKE": ("12", "NORTHWEST TERRITORIES", "TERRITOIRES DU NORD-OUEST"),
        "LUTSELK'E": ("12", "NORTHWEST TERRITORIES", "TERRITOIRES DU NORD-OUEST"),
        "NORMAN WELLS": ("12", "NORTHWEST TERRITORIES", "TERRITOIRES DU NORD-OUEST"),
        "PAULATUK": ("12", "NORTHWEST TERRITORIES", "TERRITOIRES DU NORD-OUEST"),
        "SACHS HARBOUR CLIMATE": (
            "12",
            "NORTHWEST TERRITORIES",
            "TERRITOIRES DU NORD-OUEST",
        ),
        "TUKTOYAKTUK": ("12", "NORTHWEST TERRITORIES", "TERRITOIRES DU NORD-OUEST"),
        "YOHIN": ("12", "NORTHWEST TERRITORIES", "TERRITOIRES DU NORD-OUEST"),
        # Nunavut (Region 13)
        "ARCTIC BAY": ("13", "NUNAVUT", "NUNAVUT"),
        "ARVIAT CLIMATE": ("13", "NUNAVUT", "NUNAVUT"),
        "BAKER LAKE": ("13", "NUNAVUT", "NUNAVUT"),
        "CAMBRIDGE BAY": ("13", "NUNAVUT", "NUNAVUT"),
        "CAPE DORSET CLIMATE": ("13", "NUNAVUT", "NUNAVUT"),
        "CLYDE RIVER CLIMATE": ("13", "NUNAVUT", "NUNAVUT"),
        "CORAL HARBOUR": ("13", "NUNAVUT", "NUNAVUT"),
        "EUREKA": ("13", "NUNAVUT", "NUNAVUT"),
        "GJOA HAVEN CLIMATE": ("13", "NUNAVUT", "NUNAVUT"),
        "HALL BEACH": ("13", "NUNAVUT", "NUNAVUT"),
        "IQALUIT": ("13", "NUNAVUT", "NUNAVUT"),
        "KUGAARUK CLIMATE": ("13", "NUNAVUT", "NUNAVUT"),
        "KUGLUKTUK": ("13", "NUNAVUT", "NUNAVUT"),
        "PANGNIRTUNG": ("13", "NUNAVUT", "NUNAVUT"),
        "POND INLET": ("13", "NUNAVUT", "NUNAVUT"),
        "QIKIQTARJUAQ CLIMATE": ("13", "NUNAVUT", "NUNAVUT"),
        "RANKIN INLET": ("13", "NUNAVUT", "NUNAVUT"),
        "RESOLUTE BAY": ("13", "NUNAVUT", "NUNAVUT"),
        "TALOYOAK": ("13", "NUNAVUT", "NUNAVUT"),
    }
    location = location.upper()
    return location_map.get(location, (None, None, None))


def change_weather_code(file_path, location="FORT SIMPSON", validate=True, debug=False):
    """
    Changes the weather location in an H2K file using regex.

    Only modifies Region/English and Location/English fields, which are the
    only weather fields actually read by h2k-hpxml. All other attributes
    (HDD, library, codes, French names, etc.) are left unchanged.

    Args:
        file_path: Path to the .H2K file to modify
        location: The name of the location to change to (e.g., "FORT SIMPSON")
        validate: Whether to validate the XML after modification
        debug: Whether to print debug information

    Returns:
        bool: True if changes were made, False otherwise
    """
    file_path_obj = Path(file_path)
    if not file_path_obj.exists():
        raise FileNotFoundError(f"H2K file not found: {file_path}")

    try:
        location = location.upper()

        # Use UTF-8 encoding to match the XML declaration in H2K files
        with open(file_path, "r", encoding="utf-8") as file:
            content = file.read()

        # First check if this is a properly formatted XML file
        if not content.strip().startswith("<?xml") and not content.strip().startswith("<HouseFile"):
            if debug:
                print(f"File {file_path} does not appear to be valid XML")
            return False

        # Get region information for the location
        region_code, region_en, region_fr = get_region_for_location(location)
        if not region_code:
            print(f"Error: Could not determine region for location '{location}'")
            return False

        if debug:
            print(f"Changing weather to: {location}")
            print(f"Region: {region_en}")

        # Pattern to match Region/English element
        region_pattern = r'(<Region\s+code="[^"]*">\s*<English>)[^<]*(</English>)'
        region_replacement = rf"\1{region_en}\2"

        # Pattern to match Location/English element
        location_pattern = r'(<Location\s+code="[^"]*">\s*<English>)[^<]*(</English>)'
        location_replacement = rf"\1{location}\2"

        # Make the replacements
        new_content = re.sub(region_pattern, region_replacement, content)
        new_content = re.sub(location_pattern, location_replacement, new_content)

        if new_content == content:
            if debug:
                print(f"No changes were needed in {file_path}")
            return False

        # Write the modified content back to the file with UTF-8 encoding
        with open(file_path, "w", encoding="utf-8") as file:
            file.write(new_content)

        if debug:
            print(f"Successfully updated {file_path}")
        return True

    except Exception as e:
        print(f"Error processing {file_path}: {str(e)}")
        return False


def main():
    parser = argparse.ArgumentParser(description="Change weather location in H2K files")
    parser.add_argument("path", help="Path to H2K file or directory")
    parser.add_argument("--location", default="FORT SIMPSON", help="Weather location to change to")
    parser.add_argument("--debug", action="store_true", help="Print debug information")
    args = parser.parse_args()

    path_obj = Path(args.path)
    if not path_obj.exists():
        print(f"Error: Path does not exist: {args.path}")
        return 1

    if os.path.isfile(args.path):
        change_weather_code(args.path, args.location, debug=args.debug)
    else:
        root = Path(args.path)
        for file_path in sorted(
            p for p in root.rglob("*") if p.is_file() and p.suffix.lower() == ".h2k"
        ):
            change_weather_code(file_path, args.location, debug=args.debug)

    return 0


def cli():
    """CLI entry point for updating weather locations."""
    main()


if __name__ == "__main__":
    cli()
