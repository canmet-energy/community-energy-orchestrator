#!/usr/bin/env python3
"""
Change weather location in H2K files using regex-based replacement
"""
import os
import glob
import argparse
import re
from pathlib import Path

from workflow.core import csv_dir

def load_csv_data(filename):
    """Load CSV file and return dictionary."""
    file_path = Path(filename)
    if not file_path.exists():
        raise FileNotFoundError(f"CSV file not found: {filename}")
    
    data = {}
    with open(filename, 'r', encoding='utf-8-sig') as f:
        for line in f:
            line = line.strip()
            if not line:  # Skip empty lines
                continue
            parts = line.split(',')
            if len(parts) >= 2:
                key, value = parts[0], parts[1]
                data[key.upper()] = value
    return data

def get_region_for_location(location):
    """Get the region code and English/French names for a location"""
    # Map locations to regions
    location_map = {
        # British Columbia (Region 1)
        'BONILLA ISLAND': ('1', 'BRITISH COLUMBIA', 'COLOMBIE-BRITANNIQUE'),
        'DEASE LAKE': ('1', 'BRITISH COLUMBIA', 'COLOMBIE-BRITANNIQUE'),
        'ESTEVAN POINT': ('1', 'BRITISH COLUMBIA', 'COLOMBIE-BRITANNIQUE'),
        'FORT NELSON': ('1', 'BRITISH COLUMBIA', 'COLOMBIE-BRITANNIQUE'),
        'PORT HARDY': ('1', 'BRITISH COLUMBIA', 'COLOMBIE-BRITANNIQUE'),
        'PRINCE GEORGE': ('1', 'BRITISH COLUMBIA', 'COLOMBIE-BRITANNIQUE'),
        'PUNTZI MOUNTAIN': ('1', 'BRITISH COLUMBIA', 'COLOMBIE-BRITANNIQUE'),
        'ROSE SPIT': ('1', 'BRITISH COLUMBIA', 'COLOMBIE-BRITANNIQUE'),
        'SALMON ARM': ('1', 'BRITISH COLUMBIA', 'COLOMBIE-BRITANNIQUE'),
        'SARTINE ISLAND': ('1', 'BRITISH COLUMBIA', 'COLOMBIE-BRITANNIQUE'),
        'SHERINGHAM POINT': ('1', 'BRITISH COLUMBIA', 'COLOMBIE-BRITANNIQUE'),
        
        # Newfoundland and Labrador (Region 5)
        "MARY'S HARBOUR": ('5', 'NEWFOUNDLAND AND LABRADOR', 'TERRE-NEUVE-ET-LABRADOR'),
        'BONAVISTA': ('5', 'NEWFOUNDLAND AND LABRADOR', 'TERRE-NEUVE-ET-LABRADOR'),
        'BURGEO': ('5', 'NEWFOUNDLAND AND LABRADOR', 'TERRE-NEUVE-ET-LABRADOR'),
        'CARTWRIGHT': ('5', 'NEWFOUNDLAND AND LABRADOR', 'TERRE-NEUVE-ET-LABRADOR'),
        'ST-LAWRENCE': ('5', 'NEWFOUNDLAND AND LABRADOR', 'TERRE-NEUVE-ET-LABRADOR'),
        
        # Quebec (Region 6)
        'CHAMOUCHOUANE': ('6', 'QUEBEC', 'QUÉBEC'),
        'INUKJUAK': ('6', 'QUEBEC', 'QUÉBEC'),
        'KUUJJUAQ': ('6', 'QUEBEC', 'QUÉBEC'),
        'KUUJJUARAPIK': ('6', 'QUEBEC', 'QUÉBEC'),
        'NATASHQUAN': ('6', 'QUEBEC', 'QUÉBEC'),
        "VAL-D'OR": ('6', 'QUEBEC', 'QUÉBEC'),
        'ÎLES DE LA MADELEINE': ('6', 'QUEBEC', 'QUÉBEC'),
        
        # Ontario (Region 7)
        'ARMSTRONG': ('7', 'ONTARIO', 'ONTARIO'),
        'LANSDOWNE HOUSE': ('7', 'ONTARIO', 'ONTARIO'),
        'NAGAGAMI': ('7', 'ONTARIO', 'ONTARIO'),
        'PEAWANUCK': ('7', 'ONTARIO', 'ONTARIO'),
        'TIMMINS': ('7', 'ONTARIO', 'ONTARIO'),
        
        # Manitoba (Region 8)
        'COLLINS BAY': ('8', 'MANITOBA', 'MANITOBA'),
        'GILLAM': ('8', 'MANITOBA', 'MANITOBA'),
        'TADOULE LAKE': ('8', 'MANITOBA', 'MANITOBA'),
        
        # Yukon (Region 11)
        'BURWASH': ('11', 'YUKON', 'YUKON'),
        'OLD CROW': ('11', 'YUKON', 'YUKON'),
        'WATSON LAKE': ('11', 'YUKON', 'YUKON'),
        
        # Northwest Territories (Region 12)
        'DELINE': ('12', 'NORTHWEST TERRITORIES', 'TERRITOIRES DU NORD-OUEST'),
        'FORT GOOD HOPE': ('12', 'NORTHWEST TERRITORIES', 'TERRITOIRES DU NORD-OUEST'),
        'FORT LIARD': ('12', 'NORTHWEST TERRITORIES', 'TERRITOIRES DU NORD-OUEST'),
        'FORT PROVIDENCE': ('12', 'NORTHWEST TERRITORIES', 'TERRITOIRES DU NORD-OUEST'),
        'FORT SIMPSON': ('12', 'NORTHWEST TERRITORIES', 'TERRITOIRES DU NORD-OUEST'),
        'FORT SMITH': ('12', 'NORTHWEST TERRITORIES', 'TERRITOIRES DU NORD-OUEST'),
        'HOLMAN': ('12', 'NORTHWEST TERRITORIES', 'TERRITOIRES DU NORD-OUEST'),
        'LAC LA MARTRE': ('12', 'NORTHWEST TERRITORIES', 'TERRITOIRES DU NORD-OUEST'),
        'LITTLE CHICAGO': ('12', 'NORTHWEST TERRITORIES', 'TERRITOIRES DU NORD-OUEST'),
        'LOWER CARP LAKE': ('12', 'NORTHWEST TERRITORIES', 'TERRITOIRES DU NORD-OUEST'),
        "LUTSELK'E": ('12', 'NORTHWEST TERRITORIES', 'TERRITOIRES DU NORD-OUEST'),
        'NORMAN WELLS': ('12', 'NORTHWEST TERRITORIES', 'TERRITOIRES DU NORD-OUEST'),
        'PAULATUK': ('12', 'NORTHWEST TERRITORIES', 'TERRITOIRES DU NORD-OUEST'),
        'SACHS HARBOUR CLIMATE': ('12', 'NORTHWEST TERRITORIES', 'TERRITOIRES DU NORD-OUEST'),
        'TUKTOYAKTUK': ('12', 'NORTHWEST TERRITORIES', 'TERRITOIRES DU NORD-OUEST'),
        'YOHIN': ('12', 'NORTHWEST TERRITORIES', 'TERRITOIRES DU NORD-OUEST'),
        
        # Nunavut (Region 13)
        'ARCTIC BAY': ('13', 'NUNAVUT', 'NUNAVUT'),
        'ARVIAT CLIMATE': ('13', 'NUNAVUT', 'NUNAVUT'),
        'BAKER LAKE': ('13', 'NUNAVUT', 'NUNAVUT'),
        'CAMBRIDGE BAY': ('13', 'NUNAVUT', 'NUNAVUT'),
        'CAPE DORSET CLIMATE': ('13', 'NUNAVUT', 'NUNAVUT'),
        'CLYDE RIVER CLIMATE': ('13', 'NUNAVUT', 'NUNAVUT'),
        'CORAL HARBOUR': ('13', 'NUNAVUT', 'NUNAVUT'),
        'EUREKA': ('13', 'NUNAVUT', 'NUNAVUT'),
        'GJOA HAVEN CLIMATE': ('13', 'NUNAVUT', 'NUNAVUT'),
        'HALL BEACH': ('13', 'NUNAVUT', 'NUNAVUT'),
        'IQALUIT': ('13', 'NUNAVUT', 'NUNAVUT'),
        'KUGAARUK CLIMATE': ('13', 'NUNAVUT', 'NUNAVUT'),
        'KUGLUKTUK': ('13', 'NUNAVUT', 'NUNAVUT'),
        'PANGNIRTUNG': ('13', 'NUNAVUT', 'NUNAVUT'),
        'POND INLET': ('13', 'NUNAVUT', 'NUNAVUT'),
        'QIKIQTARJUAQ CLIMATE': ('13', 'NUNAVUT', 'NUNAVUT'),
        'RANKIN INLET': ('13', 'NUNAVUT', 'NUNAVUT'),
        'RESOLUTE BAY': ('13', 'NUNAVUT', 'NUNAVUT'),
        'TALOYOAK': ('13', 'NUNAVUT', 'NUNAVUT'),
    }
    
    return location_map.get(location, (None, None, None))

def change_weather_code(file_path, location="FORT SIMPSON", validate=True, debug=False):
    """
    Changes the weather information in an H2K file using regex.
    
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
        
        # Always use latin-1 (iso-8859-1) encoding for H2K files
        with open(file_path, 'r', encoding='latin-1') as file:
            content = file.read()

        # First check if this is a properly formatted XML file
        if not content.strip().startswith('<?xml') and not content.strip().startswith('<HouseFile'):
            if debug:
                print(f"File {file_path} does not appear to be valid XML")
            return False

        # Load location codes and weather details
        location_codes_path = csv_dir() / 'location_code.csv'
        if not location_codes_path.exists():
            raise FileNotFoundError(f"Location codes CSV not found: {location_codes_path}")
        
        location_codes = load_csv_data(location_codes_path)
        
        weather_details = {}
        weather_details_path = csv_dir() / 'weather_details.csv'
        if not weather_details_path.exists():
            raise FileNotFoundError(f"Weather details CSV not found: {weather_details_path}")
        
        with open(weather_details_path, 'r', encoding='utf-8-sig') as csvfile:
            next(csvfile)  # Skip header
            for line in csvfile:
                line = line.strip()
                if not line:  # Skip empty lines
                    continue
                parts = line.split(',')
                if len(parts) >= 3:
                    loc, hdd, lib = parts[0], parts[1], parts[2]
                    weather_details[loc.upper()] = {'hdd': hdd, 'library': lib}

        # Validate location exists
        if location not in weather_details:
            print(f"Error: Location '{location}' not found in weather_details.csv")
            return False
            
        if location not in location_codes:
            print(f"Error: Location '{location}' not found in location_code.csv")
            return False

        # Get region information
        region_code, region_en, region_fr = get_region_for_location(location)
        if not region_code:
            print(f"Error: Could not determine region for location '{location}'")
            return False

        if debug:
            print(f"Found location {location}")
            print(f"Region: {region_en} (code: {region_code})")
            print(f"HDD: {weather_details[location]['hdd']}")
            print(f"Location code: {location_codes[location]}")

        # Pattern to match the exact Weather section structure
        pattern = (
            r'<Weather\s+depthOfFrost="[^"]*"\s+heatingDegreeDay="[^"]*"\s+'
            r'library="[^"]*">\s*<Region\s+code="[^"]*">\s*<English>[^<]*</English>\s*'
            r'<French>[^<]*</French>\s*</Region>\s*<Location\s+code="[^"]*">\s*'
            r'<English>[^<]*</English>\s*<French>[^<]*</French>\s*</Location>\s*</Weather>'
        )
        
        # Create replacement with exact XML structure and indentation
        replacement = (
            f'<Weather depthOfFrost="1.2192" heatingDegreeDay="{weather_details[location]["hdd"]}" '
            f'library="{weather_details[location]["library"]}">\n'
            f'            <Region code="{region_code}">\n'
            f'                <English>{region_en}</English>\n'
            f'                <French>{region_fr}</French>\n'
            f'            </Region>\n'
            f'            <Location code="{location_codes[location]}">\n'
            f'                <English>{location}</English>\n'
            f'                <French>{location}</French>\n'
            f'            </Location>\n'
            f'        </Weather>'
        )

        # Make the replacement
        new_content = re.sub(pattern, replacement, content)
        
        if new_content == content:
            if debug:
                print(f"No changes were needed in {file_path}")
            return False

        # Write the modified content back to the file
        with open(file_path, 'w', encoding='latin-1') as file:
            file.write(new_content)
            
        if debug:
            print(f"Successfully updated {file_path}")
        return True

    except Exception as e:
        print(f"Error processing {file_path}: {str(e)}")
        return False

def main():
    parser = argparse.ArgumentParser(description='Change weather location in H2K files')
    parser.add_argument('path', help='Path to H2K file or directory')
    parser.add_argument('--location', default="FORT SIMPSON", help='Weather location to change to')
    parser.add_argument('--debug', action='store_true', help='Print debug information')
    args = parser.parse_args()
    
    path_obj = Path(args.path)
    if not path_obj.exists():
        print(f"Error: Path does not exist: {args.path}")
        return 1

    if os.path.isfile(args.path):
        change_weather_code(args.path, args.location, debug=args.debug)
    else:
        root = Path(args.path)
        for file_path in sorted(p for p in root.rglob('*') if p.is_file() and p.suffix.lower() == '.h2k'):
            change_weather_code(file_path, args.location, debug=args.debug)
    
    return 0

def cli():
    """CLI entry point for updating weather locations."""
    main()

if __name__ == "__main__":
    cli()
