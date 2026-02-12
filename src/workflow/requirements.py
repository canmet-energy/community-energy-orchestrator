import csv
from pathlib import Path
import pandas as pd

from workflow.core import csv_dir, logs_dir


def get_community_requirements(community_name):
    """
    Read housing type requirements from CSV file.
    
    Args:
        community_name: Name of the community
    
    Returns:
        Dict mapping housing types (e.g., 'pre-2000-single') to required counts.
        Returns {} if community not found (graceful fallback).
    """
    comm_upper = community_name.upper()
    csv_path = csv_dir() / 'communities-number-of-houses.csv'
    
    if not csv_path.exists():
        raise FileNotFoundError(f"Requirements CSV not found: {csv_path}")
    
    df = pd.read_csv(csv_path, header=None)
    # Find the row where the first column matches (case-insensitive)
    mask = df[0].astype(str).str.strip().str.upper() == comm_upper
    if not mask.any():
        print(f"[INFO] Community '{community_name}' not found in requirements CSV. Using graceful fallback.")
        return {}
    row = df[mask].iloc[0].tolist()
    # Skip the first column (community name)
    kv_pairs = row[1:]
    requirements = {}
    
    # Validate we have pairs
    if len(kv_pairs) % 2 != 0:
        print(f"[WARNING] Odd number of values in CSV row for {community_name}")
    
    # Parse as key-value pairs
    for i in range(0, len(kv_pairs)-1, 2):
        key = kv_pairs[i]
        val = kv_pairs[i+1]
        
        # Only process valid string keys with hyphens
        if not isinstance(key, str) or '-' not in key:
            continue
        
        # Extract era and type using known patterns
        era = None
        btype = None
        
        for era_opt in ['pre-2000', '2001-2015', 'post-2016']:
            if era_opt in key:
                era = era_opt
                break
        
        for type_opt in ['single', 'semi', 'row-mid', 'row-end']:
            if type_opt in key:
                btype = type_opt
                break
        
        # Only add if we successfully identified both era and type
        if era and btype:
            try:
                count = int(val)
                requirements[f"{era}-{btype}"] = count
            except (ValueError, TypeError):
                print(f"[WARNING] Invalid count for {key}: {val}")
    # Write requirements to debug log for inspection
    debug_log_path = logs_dir() / 'archetype_copy_debug.log'
    debug_log_path.parent.mkdir(parents=True, exist_ok=True)
    with open(debug_log_path, 'a') as debug_log:
        debug_log.write(f"[DEBUG] Extracted requirements for {community_name}: {requirements}\n")
    return requirements

def get_weather_location(community_name):
    """
    Look up weather location from CSV.
    
    Args:
        community_name: Name of the community
    
    Returns:
        Weather location string, or community name with dashes replaced if not found
    """
    csv_path = csv_dir() / 'train-test communities hdd and weather locations.csv'
    
    if not csv_path.exists():
        raise FileNotFoundError(f"Weather locations CSV not found: {csv_path}")
    
    comm_upper = community_name.upper()
    try:
        with open(csv_path, newline='', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                if row['Community'].strip().upper() == comm_upper:
                    return row['WEATHER'].strip()
    except UnicodeDecodeError:
        with open(csv_path, newline='', encoding='latin1') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                if row['Community'].strip().upper() == comm_upper:
                    return row['WEATHER'].strip()
    return community_name.replace('-', ' ')