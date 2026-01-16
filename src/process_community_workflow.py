#!/usr/bin/env python3
def duplicate_missing_timeseries(timeseries_dir, building_type, required_count):
    # Guarantee at least the required count (not just N+20%)
    target_count = max(int(required_count * 1.2), required_count) if required_count > 0 else 0
    files = [f for f in os.listdir(timeseries_dir) if f.startswith(building_type) and f.endswith("-results_timeseries.csv")]
    if not files:
        print(f"No source files found for {building_type}")
        return
    count = len(files)
    # First, ensure at least the required count
    while count < required_count:
        src_file = files[count % len(files)]
        src_path = os.path.join(timeseries_dir, src_file)
        new_name = f"{building_type}_DUPLICATE_{count+1}-results_timeseries.csv"
        dst_path = os.path.join(timeseries_dir, new_name)
        shutil.copy2(src_path, dst_path)
        print(f"Created {new_name}")
        files.append(new_name)
        count += 1
    # Optionally, fill up to N+20% for simulation diversity
    while count < target_count:
        src_file = files[count % len(files)]
        src_path = os.path.join(timeseries_dir, src_file)
        new_name = f"{building_type}_DUPLICATE_{count+1}-results_timeseries.csv"
        dst_path = os.path.join(timeseries_dir, new_name)
        shutil.copy2(src_path, dst_path)
        print(f"Created {new_name}")
        files.append(new_name)
        count += 1

def process_community_energy(community_name):
    # Collect timeseries files from archetypes/output
    import shutil
    base_dir = Path(f'communities/{community_name}')
    output_dir = base_dir / 'archetypes' / 'output'
    timeseries_dir = base_dir / 'timeseries'
    timeseries_dir.mkdir(parents=True, exist_ok=True)
    collected = 0
    if output_dir.exists():
        for building_dir in output_dir.iterdir():
            if building_dir.is_dir():
                run_dir = building_dir / 'run'
                if run_dir.exists():
                    results_file = run_dir / 'results_timeseries.csv'
                    if results_file.exists():
                        target_name = f"{building_dir.name}-results_timeseries.csv"
                        target_path = timeseries_dir / target_name
                        shutil.copy2(results_file, target_path)
                        collected += 1
    print(f"Collected {collected} timeseries files for {community_name}")
    # Ensure each required type has enough files by duplicating as needed
    requirements = get_community_requirements(community_name)
    timeseries_dir_path = str(timeseries_dir)
    for building_type, required_count in requirements.items():
        duplicate_missing_timeseries(timeseries_dir_path, building_type, required_count)

    # Run community analysis with correct arguments
    analysis_dir = base_dir / 'analysis'
    analysis_dir.mkdir(parents=True, exist_ok=True)
    subprocess.run([
        sys.executable,
        'calculate_community_analysis.py',
        community_name
    ], check=True)
import os
import csv
import re
import shutil
import subprocess
import random
import pandas as pd
from pathlib import Path
ARCHETYPE_TYPE_PATTERNS = {
    'pre-2000-single': [r'pre-2000-single_.*\.H2K$'],
    '2001-2015-single': [r'2001-2015-single_.*\.H2K$'],
    'post-2016-single': [r'post-2016-single_.*\.H2K$'],
    'pre-2000-semi': [r'pre-2000-semi_.*\.H2K$', r'pre-2000-double_.*\.H2K$'],
    '2001-2015-semi': [r'2001-2015-semi_.*\.H2K$', r'2001-2015-double_.*\.H2K$'],
    'post-2016-semi': [r'post-2016-semi_.*\.H2K$', r'post-2016-double_.*\.H2K$'],
    'pre-2000-row-mid': [r'pre-2000-row-mid_.*\.H2K$', r'pre-2000-row-middle_.*\.H2K$'],
    '2001-2015-row-mid': [r'2001-2015-row-mid_.*\.H2K$', r'2001-2015-row-middle_.*\.H2K$'],
    'post-2016-row-mid': [r'post-2016-row-mid_.*\.H2K$', r'post-2016-row-middle_.*\.H2K$'],
    'pre-2000-row-end': [r'pre-2000-row-end_.*\.H2K$'],
    '2001-2015-row-end': [r'2001-2015-row-end_.*\.H2K$'],
    'post-2016-row-end': [r'post-2016-row-end_.*\.H2K$'],
}

def get_weather_location(community_name):
    """
    Look up the weather location for a community from the CSV file.
    Returns the weather location string, or the community name if not found.
    """
    csv_path = 'train-test-communities hdd and weather locaiton.csv'
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
#!/usr/bin/env python3


import os
import shutil
import sys
import pandas as pd
from pathlib import Path
import subprocess
import re
import random
from src.debug_timeseries_outputs import debug_timeseries_outputs

# Define building type patterns
BUILDING_TYPES = {
    'pre-2000-single': [r'pre-2000-single_.*\.H2K$'],
    '2001-2015-single': [r'2001-2015-single_.*\.H2K$'],
    'post-2016-single': [r'post-2016-single_.*\.H2K$'],
    'pre-2000-semi': [r'pre-2000-semi_.*\.H2K$', r'pre-2000-double_.*\.H2K$'],
    '2001-2015-semi': [r'2001-2015-semi_.*\.H2K$', r'2001-2015-double_.*\.H2K$'],
    'post-2016-semi': [r'post-2016-semi_.*\.H2K$', r'post-2016-double_.*\.H2K$'],
    'pre-2000-row-mid': [r'pre-2000-row-mid_.*\.H2K$', r'pre-2000-row-middle_.*\.H2K$'],
    '2001-2015-row-mid': [r'2001-2015-row-mid_.*\.H2K$', r'2001-2015-row-middle_.*\.H2K$'],
    'post-2016-row-mid': [r'post-2016-row-mid_.*\.H2K$', r'post-2016-row-middle_.*\.H2K$'],
    'pre-2000-row-end': [r'pre-2000-row-end_.*\.H2K$'],
    '2001-2015-row-end': [r'2001-2015-row-end_.*\.H2K$'],
    'post-2016-row-end': [r'post-2016-row-end_.*\.H2K$'],
}

def get_community_requirements(community_name):
    """
    Read community requirements from CSV file containing housing counts
    Returns dictionary of housing types and their required counts
    """

    comm_upper = community_name.upper()
    df = pd.read_csv('train-test communities number of housing types.csv', header=None)
    # Find the row where the first column matches (case-insensitive)
    mask = df[0].str.strip().str.upper() == comm_upper
    if not mask.any():
        raise ValueError(f"Community '{community_name}' not found in CSV file.")
    row = df[mask].iloc[0].tolist()
    # Skip the first column (community name)
    kv_pairs = row[1:]
    requirements = {}
    # Parse as key-value pairs
    for i in range(0, len(kv_pairs)-1, 2):
        key = kv_pairs[i]
        val = kv_pairs[i+1]
        # Only process valid keys
        if isinstance(key, str) and '-' in key:
            # Extract era and type
            parts = key.split('-')
            if len(parts) >= 3:
                era = parts[-2] + '-' + parts[-1] if parts[-2].isdigit() else parts[-2]
                btype = parts[-1] if parts[-2].isdigit() else parts[-1]
                # Actually, just use the last two segments for era and type
                era_type = '-'.join(parts[-2:]) if parts[-2] in ['pre-2000','2001-2015','post-2016'] else parts[-2] + '-' + parts[-1]
                # But for manifest, use era and type
                # For requirements dict, use <era>-<type>
                # Find era and type from key
                for era_opt in ['pre-2000','2001-2015','post-2016']:
                    if era_opt in key:
                        era = era_opt
                        break
                else:
                    era = None
                for t_opt in ['single','semi','row-mid','row-end']:
                    if t_opt in key:
                        btype = t_opt
                        break
                else:
                    btype = None
                if era and btype:
                    try:
                        count = int(val)
                    except Exception:
                        count = 0
                    requirements[f"{era}-{btype}"] = count
    # Write requirements to debug log for inspection
    with open('archetype_copy_debug.log', 'a') as debug_log:
        debug_log.write(f"[DEBUG] Extracted requirements for {community_name}: {requirements}\n")
    return requirements

def create_community_directories(community_name):
    """
    Create the standard directory structure for a community
    Only create the base path and archetypes folder at the start
    """
    base_path = Path(f'communities/{community_name}')
    archetypes_path = base_path / 'archetypes'
    timeseries_path = base_path / 'timeseries'
    analysis_path = base_path / 'analysis'
    for path in [base_path, archetypes_path, timeseries_path, analysis_path]:
        path.mkdir(parents=True, exist_ok=True)
    return base_path

def copy_archetype_files(community_name, requirements):
    """
    Copy required archetype files with 20% additional
    If not enough files, implement duplication process
    """
    # FIXME: Adjust source path as needed
    archetypes_source = Path('src/housing-archetypes')
    base_path = Path(f'communities/{community_name}/archetypes')
    if not base_path.exists():
        base_path.mkdir(parents=True, exist_ok=True)
    # Find all H2K files in the source directory
    all_files = os.listdir(archetypes_source)
    h2k_files = [f for f in all_files if f.endswith('.H2K')]

    debug_log_path = Path('archetype_copy_debug.log')
    with open(debug_log_path, 'a') as debug_log:
        for req_type, count in requirements.items():
            if count == 0:
                continue
            # Enforce N+20% rule (always round up for safety)
            num_to_copy = int(count * 1.2 + 0.9999) if count > 0 else 0
            patterns = ARCHETYPE_TYPE_PATTERNS.get(req_type, [fr'{req_type}_.*\.H2K$'])
            matched_files = []
            for pat in patterns:
                regex = re.compile(pat)
                matches = [f for f in h2k_files if regex.match(f)]
                matched_files.extend(matches)
            # For 'semi', always include all matching 'double' archetypes
            if 'semi' in req_type:
                double_pat = req_type.replace('semi', 'double') + r'_.*\.H2K$'
                regex_double = re.compile(double_pat)
                double_matches = [f for f in h2k_files if regex_double.match(f)]
                matched_files.extend(double_matches)
            matched_files = list(set(matched_files))
            debug_log.write(f"[DEBUG] Looking for files matching: '{req_type}' (need {count}, copying {num_to_copy})\n")
            debug_log.write(f"[DEBUG] Found {len(matched_files)} files for '{req_type}': {matched_files}\n")
            files_to_copy = list(matched_files)
            # Fallback: fill shortfall from other time periods of same base type
            if len(files_to_copy) < num_to_copy:
                base_type = req_type.split('-')[-1]
                fallback_types = [t for t in ARCHETYPE_TYPE_PATTERNS.keys() if t != req_type and t.endswith(base_type)]
                for fallback_type in fallback_types:
                    fallback_patterns = ARCHETYPE_TYPE_PATTERNS.get(fallback_type, [fr'{fallback_type}_.*\.H2K$'])
                    for pat in fallback_patterns:
                        regex = re.compile(pat)
                        fallback_matches = [f for f in h2k_files if regex.match(f) and f not in files_to_copy]
                        files_to_copy.extend(fallback_matches)
                        if len(files_to_copy) >= num_to_copy:
                            break
                    if len(files_to_copy) >= num_to_copy:
                        break
            # If still not enough, duplicate from selected (guarantee enough unique-named files)
            if len(files_to_copy) < num_to_copy and files_to_copy:
                needed = num_to_copy - len(files_to_copy)
                debug_log.write(f"[DEBUG] Duplicating {needed} archetypes for '{req_type}' to fill shortfall\n")
                # For each needed duplicate, create a unique name
                for i in range(needed):
                    src_file = random.choice(files_to_copy)
                    name_parts = src_file.rsplit('.', 1)
                    new_name = f"{name_parts[0]}_DUPLICATE_{i+1}.{name_parts[1]}"
                    files_to_copy.append(new_name)
                    # Actually copy the file with the new name
                    shutil.copy2(archetypes_source / src_file, base_path / new_name)
            # Always trim to exactly num_to_copy
            files_to_copy = files_to_copy[:num_to_copy]
            debug_log.write(f"[DEBUG] Copying {len(files_to_copy)} files for '{req_type}' to {base_path}\n")
            # Track how many times each file is used
            file_usage = {}
            for idx, file_name in enumerate(files_to_copy):
                # If this is a duplicate (ends with _DUPLICATE_x), it was already copied above
                if '_DUPLICATE_' in file_name:
                    continue
                src_file = archetypes_source / file_name
                # If this file has already been used, append _DUPLICATE_x
                if file_name not in file_usage:
                    file_usage[file_name] = 1
                    dst_file_main = base_path / file_name
                else:
                    file_usage[file_name] += 1
                    name_parts = file_name.rsplit('.', 1)
                    new_name = f"{name_parts[0]}_DUPLICATE_{file_usage[file_name]}.{name_parts[1]}"
                    dst_file_main = base_path / new_name
                debug_log.write(f"[DEBUG] Copying {src_file} -> {dst_file_main}\n")
                shutil.copy2(src_file, dst_file_main)

def create_manifest(community_name, requirements):
    """
    Create a manifest file documenting the community requirements and simulation status
    """
    manifest_path = Path(f'communities/{community_name}/archetypes/{community_name}-manifest.md')
    # Ensure parent directory exists
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    # Use weather location from CSV
    weather_location = get_weather_location(community_name)
    # Helper to get count or 0
    def get_count(era, btype):
        return requirements.get(f"{era}-{btype}", 0)
    content = f"""# {community_name} Community Analysis Manifest

## Weather Location
Using weather data from: {weather_location}

## Housing Requirements

### Pre-2000
- Single Detached: {get_count('pre-2000','single')}
- Semi-Detached: {get_count('pre-2000','semi')}
- Row House Middle: {get_count('pre-2000','row-mid')}
- Row House End: {get_count('pre-2000','row-end')}

### 2001-2015
- Single Detached: {get_count('2001-2015','single')}
- Semi-Detached: {get_count('2001-2015','semi')}
- Row House Middle: {get_count('2001-2015','row-mid')}
- Row House End: {get_count('2001-2015','row-end')}

### Post-2016
- Single Detached: {get_count('post-2016','single')}
- Semi-Detached: {get_count('post-2016','semi')}
- Row House Middle: {get_count('post-2016','row-mid')}
- Row House End: {get_count('post-2016','row-end')}

## Simulation Status
- [ ] Weather files updated
- [ ] HPXML conversion completed
- [ ] Simulations completed
- [ ] Community analysis generated

## Notes
- Created on: {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')}
- Additional files added: 20% extra for each housing type
"""
    with open(manifest_path, 'w') as f:
        f.write(content)
    return manifest_path

def update_weather_location(community_name):
    """
    Update HOT2000 files to use the correct weather location
    """
    base_path = Path(f'communities/{community_name}/archetypes')
    weather_location = get_weather_location(community_name)
    subprocess.run([
        'python',
        'change_weather_location_regex.py',
        str(base_path),
        '--location',
        weather_location
    ], check=True)

def run_hpxml_conversion(community_name):
    """
    Convert HOT2000 files to HPXML and run simulations
    """
    base_path = Path(f'communities/{community_name}/archetypes')
    print(f"[HPXML] Starting HPXML conversion for files in: {base_path}")
    # Run h2k2hpxml conversion with hourly data
    print(f"[HPXML] Running h2k2hpxml.py with hourly output...")
    subprocess.run([
        'python',
        'converter/bin/h2k2hpxml.py',
        'run',
        '-i',
        str(base_path),
        '--hourly',
        'ALL'
    ], check=True)
    print(f"[HPXML] Conversion complete.")

    # Collect timeseries files from archetypes/output
    print(f"[HPXML] Collecting timeseries files from output directories...")
    import shutil
    base_dir = Path(f'communities/{community_name}')
    output_dir = base_dir / 'archetypes' / 'output'
    timeseries_dir = base_dir / 'timeseries'
    timeseries_dir.mkdir(parents=True, exist_ok=True)
    collected = 0
    if output_dir.exists():
        for building_dir in output_dir.iterdir():
            if building_dir.is_dir():
                run_dir = building_dir / 'run'
                if run_dir.exists():
                    results_file = run_dir / 'results_timeseries.csv'
                    if results_file.exists():
                        target_name = f"{building_dir.name}-results_timeseries.csv"
                        target_path = timeseries_dir / target_name
                        shutil.copy2(results_file, target_path)
                        collected += 1
    print(f"Collected {collected} timeseries files for {community_name}")

    # Ensure each required type has enough files by duplicating as needed
    requirements = get_community_requirements(community_name)
    timeseries_dir_path = str(timeseries_dir)
    for building_type, required_count in requirements.items():
        duplicate_missing_timeseries(timeseries_dir_path, building_type, required_count)

    # Run community analysis with correct arguments
    analysis_dir = base_dir / 'analysis'
    analysis_dir.mkdir(parents=True, exist_ok=True)
    subprocess.run([
        sys.executable,
        'calculate_community_analysis.py',
        community_name
    ], check=True)

def main(community_name):
    """
    Main workflow function
    """

    print(f"\n[WORKFLOW] Starting workflow for community: {community_name}")
    
    # Ensure all necessary directories exist
    print(f"[WORKFLOW] Step 1: Creating directories...")
    create_community_directories(community_name)

    # Get requirements for debug log
    print(f"[WORKFLOW] Step 2: Reading requirements from CSV...")
    requirements = get_community_requirements(community_name)
    print(f"[WORKFLOW] Requirements: {requirements}")

    # Copy archetype files before any simulation or analysis
    print(f"[WORKFLOW] Step 3: Copying archetype files...")
    copy_archetype_files(community_name, requirements)
    print(f"[WORKFLOW] Step 3 complete.")

    # Update weather location in archetypes
    print(f"[WORKFLOW] Step 4: Updating weather location...")
    update_weather_location(community_name)
    print(f"[WORKFLOW] Step 4 complete.")

    # Run HPXML conversion and simulation for each archetype
    print(f"[WORKFLOW] Step 5: Running HPXML conversion and simulations...")
    run_hpxml_conversion(community_name)
    print(f"[WORKFLOW] Step 5 complete.")

    # Print contents of the timeseries directory for debugging
    timeseries_dir = Path(f'communities/{community_name}/timeseries')
    print(f"\nContents of {timeseries_dir} just before analysis:")
    for f in sorted(timeseries_dir.glob('*')):
        print(f"  - {f.name}")

    # Delegate aggregation and output to calculate_community_analysis.py
    import subprocess
    print("\nDelegating aggregation and output to calculate_community_analysis.py...")
    result = subprocess.run([
        sys.executable,
        "calculate_community_analysis.py",
        community_name
    ], capture_output=True, text=True)
    print(result.stdout)
    if result.returncode != 0:
        print(f"Error running calculate_community_analysis.py: {result.stderr}")
        return 1

    # 9. Debug timeseries outputs
    debug_log_path = debug_timeseries_outputs(community_name, requirements)
    print(f"Analysis completed successfully for {community_name}")
    print(f"Timeseries output debug log: {debug_log_path}")

    # 10. Remove archetypes/output directory after successful analysis
    output_dir = Path(f"communities/{community_name}/archetypes/output")
    if output_dir.exists() and output_dir.is_dir():
        import shutil
        shutil.rmtree(output_dir)
        print(f"Removed directory: {output_dir}")
    return 0

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python process_community_workflow.py <community_name>")
        sys.exit(1)
        
    community_name = sys.argv[1]
    main(community_name)