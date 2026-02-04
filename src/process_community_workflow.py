#!/usr/bin/env python3
"""
Community energy modeling workflow orchestrator.
Processes housing archetypes, runs simulations, and generates community-level energy analysis.
"""

import csv
import math
import os
import random
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pandas as pd

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

def create_manifest(community_name, requirements):
    """
    Create manifest file documenting requirements and simulation status.
    
    Args:
        community_name: Name of the community
        requirements: Dict of housing types to required counts
    
    Returns:
        Path to created manifest file
    """
    manifest_path = Path(__file__).resolve().parent.parent / 'communities' / community_name / 'archetypes' / f'{community_name}-manifest.md'
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

def duplicate_missing_timeseries(timeseries_dir, building_type, required_count):
    """
    Duplicate timeseries files to reach exact required count if needed.
    
    Args:
        timeseries_dir: Path to directory containing timeseries files
        building_type: Type prefix to match (e.g., 'pre-2000-single')
        required_count: Exact number of files needed
    """
    files = sorted(f for f in os.listdir(timeseries_dir) if f.startswith(building_type) and f.endswith("-results_timeseries.csv"))
    if not files:
        print(f"No source files found for {building_type}")
        return
    count = len(files)

    seed_str = os.environ.get('ARCHETYPE_SELECTION_SEED')
    if seed_str is not None:
        # Stable per-building-type seed so results don't depend on dict iteration order.
        rng = random.Random(f"{seed_str}:{building_type}")
        source_files = [f for f in files if '_DUPLICATE_' not in f] or files
    else:
        # No seed: truly random duplication each run
        rng = random.Random()
        source_files = files
    
    if count >= required_count:
        print(f"{building_type}: Already have {count} files (required: {required_count})")
        return
    
    while count < required_count:
        src_file = rng.choice(source_files)
        src_path = os.path.join(timeseries_dir, src_file)
        new_name = f"{building_type}_DUPLICATE_{count+1}-results_timeseries.csv"
        dst_path = os.path.join(timeseries_dir, new_name)
        shutil.copy2(src_path, dst_path)
        print(f"Created {new_name}")
        files.append(new_name)
        count += 1


def get_weather_location(community_name):
    """
    Look up weather location from CSV.
    
    Args:
        community_name: Name of the community
    
    Returns:
        Weather location string, or community name with dashes replaced if not found
    """
    csv_path = Path(__file__).resolve().parent.parent / 'csv' / 'train-test communities hdd and weather locations.csv'
    
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


def get_community_requirements(community_name):
    """
    Read housing type requirements from CSV file.
    
    Args:
        community_name: Name of the community
    
    Returns:
        Dict mapping housing types (e.g., 'pre-2000-single') to required counts
    """
    comm_upper = community_name.upper()
    csv_path = Path(__file__).resolve().parent.parent / 'csv' / 'train-test communities number of housing types.csv'
    
    if not csv_path.exists():
        raise FileNotFoundError(f"Requirements CSV not found: {csv_path}")
    
    df = pd.read_csv(csv_path, header=None)
    # Find the row where the first column matches (case-insensitive)
    mask = df[0].astype(str).str.strip().str.upper() == comm_upper
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
    debug_log_path = Path(__file__).resolve().parent.parent / 'logs' / 'archetype_copy_debug.log'
    debug_log_path.parent.mkdir(parents=True, exist_ok=True)
    with open(debug_log_path, 'a') as debug_log:
        debug_log.write(f"[DEBUG] Extracted requirements for {community_name}: {requirements}\n")
    return requirements

def create_community_directories(community_name):
    """
    Create standard directory structure for a community.
    
    Args:
        community_name: Name of the community
    
    Returns:
        Path to community base directory
    """
    base_path = Path(__file__).resolve().parent.parent / 'communities' / community_name
    archetypes_path = base_path / 'archetypes'
    timeseries_path = base_path / 'timeseries'
    analysis_path = base_path / 'analysis'
    for path in [base_path, archetypes_path, timeseries_path, analysis_path]:
        path.mkdir(parents=True, exist_ok=True)
    return base_path

def copy_archetype_files(community_name, requirements):
    """
    Copy archetype files matching requirements (targets N+20% per type).
    
    Args:
        community_name: Name of the community
        requirements: Dict of housing types to required counts
    """

    archetypes_source = Path(__file__).resolve().parent / 'source-archetypes'
    
    if not archetypes_source.exists():
        raise FileNotFoundError(f"Source archetypes directory not found: {archetypes_source}")
    
    base_path = Path(__file__).resolve().parent.parent / 'communities' / community_name / 'archetypes'
    if not base_path.exists():
        base_path.mkdir(parents=True, exist_ok=True)
    # Find all H2K files in the source directory
    all_files = os.listdir(archetypes_source)
    h2k_files = [f for f in all_files if f.endswith('.H2K')]

    # Compile regex patterns once to avoid repeated compilation work.
    compiled_patterns_by_type = {
        req_type: [re.compile(pat) for pat in patterns]
        for req_type, patterns in ARCHETYPE_TYPE_PATTERNS.items()
    }

    debug_log_path = Path(__file__).resolve().parent.parent / 'logs' / 'archetype_copy_debug.log'
    debug_log_path.parent.mkdir(parents=True, exist_ok=True)
    seed_str = os.environ.get('ARCHETYPE_SELECTION_SEED')
    rng = random.Random(seed_str) if seed_str is not None else random.Random()
    with open(debug_log_path, 'a') as debug_log:
        for req_type, count in requirements.items():
            if count == 0:
                continue
            # Enforce N+20% rule (always round up for safety)
            num_to_copy = math.ceil(count * 1.2) if count > 0 else 0
            if req_type not in ARCHETYPE_TYPE_PATTERNS:
                print(f"[WARNING] Requirement type '{req_type}' not found in ARCHETYPE_TYPE_PATTERNS. ")
            patterns = compiled_patterns_by_type.get(req_type)
            if patterns is None:
                patterns = [re.compile(fr'{req_type}_.*\.H2K$')]

            matched_files = [
                f for f in h2k_files
                if any(regex.match(f) for regex in patterns)
            ]
            matched_files = sorted(set(matched_files))  # Canonical order for reproducible shuffling
            rng.shuffle(matched_files)
            # Copy up to num_to_copy files (or fewer if we run out of matches).
            files_to_copy = matched_files[:num_to_copy]

            # Copy whatever is available (no duplication). If nothing matches, warn and move on.
            if not files_to_copy:
                msg = f"[WARNING] No archetype files found for '{req_type}'. Skipping copy for this type."
                print(msg)
                debug_log.write(msg + "\n")
                continue

            debug_log.write(
                f"[DEBUG] Copying {len(files_to_copy)} of {len(matched_files)} files for '{req_type}' to {base_path}\n"
            )
            for file_name in files_to_copy:
                src_file = archetypes_source / file_name
                dst_file = base_path / file_name
                shutil.copy2(src_file, dst_file)
                debug_log.write(f"[DEBUG] Copying {src_file} -> {dst_file}\n")

def update_weather_location(community_name):
    """
    Update HOT2000 files to use correct weather location.
    
    Args:
        community_name: Name of the community
    """
    base_path = Path(__file__).resolve().parent.parent / 'communities' / community_name / 'archetypes'
    weather_location = get_weather_location(community_name)
    script_path = Path(__file__).resolve().parent / 'change_weather_location_regex.py'
    subprocess.run([
        sys.executable,
        str(script_path),
        str(base_path),
        '--location',
        weather_location
    ], check=True)

def run_hpxml_conversion(community_name, requirements):
    """
    Convert HOT2000 files to HPXML, run simulations, and collect timeseries results.
    Duplicates timeseries files as needed to meet requirements.
    
    Args:
        community_name: Name of the community
    """
    base_path = Path(__file__).resolve().parent.parent / 'communities' / community_name / 'archetypes'
    output_path = base_path / 'output'

    # Create output directory if not already created
    output_path.mkdir(parents= True, exist_ok= True)

    print(f"[HPXML] Starting HPXML conversion for files in: {base_path}")
    print(f"[HPXML] Output will be saved to: {output_path}")
    
    # Run h2k-hpxml conversion with hourly data
    if shutil.which('h2k-hpxml'):
        # Using CLI (recommended)
        print(f"[HPXML] Running h2k-hpxml CLI with hourly output...")
        subprocess.run([
            'h2k-hpxml', 
            str(base_path),
            '--output',
            str(output_path),
            '--hourly', 
            'ALL'
            ], check=True)
    else:
        # Fallback to direct script if CLI not installed
        print(f"[HPXML] Running convert.py directly with hourly output...")
        convert_path = Path(__file__).resolve().parent / 'h2k-hpxml' / 'src' / 'h2k_hpxml' / 'cli' / 'convert.py'
        h2k_hpxml_src = Path(__file__).resolve().parent / 'h2k-hpxml' / 'src'
        env = os.environ.copy()
        env["PYTHONPATH"] = f"{h2k_hpxml_src}{os.pathsep}{env.get('PYTHONPATH','')}"
        subprocess.run([
            sys.executable,
            str(convert_path),
            str(base_path),
            '--output',
            str(output_path),
            '--hourly',
            'ALL'
        ], check=True, env=env)
    
    print(f"[HPXML] Conversion complete.")

    # Collect timeseries files from archetypes/output
    print(f"[HPXML] Collecting timeseries files from output directories...")
    base_dir = Path(__file__).resolve().parent.parent / 'communities' / community_name
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
    timeseries_dir_path = str(timeseries_dir)
    for building_type, required_count in requirements.items():
        duplicate_missing_timeseries(timeseries_dir_path, building_type, required_count)

def main(community_name):
    """
    Execute complete community energy analysis workflow.
    
    Args:
        community_name: Name of the community
    
    Returns:
        0 on success, 1 on failure
    """

    print(f"\n[WORKFLOW] Starting workflow for community: {community_name}")
    
    # Validate community name exists in requirements CSV before any operations
    print(f"[WORKFLOW] Validating community name...")
    try:
        requirements = get_community_requirements(community_name)
        print(f"[WORKFLOW] Community validated: {community_name}")
    except ValueError as e:
        print(f"[ERROR] {e}")
        return 1
    except FileNotFoundError as e:
        print(f"[ERROR] {e}")
        return 1
    
    # 0. Clean existing community directory to ensure fresh run
    print(f"[WORKFLOW] Step 0: Cleaning previous run data...")
    cleanup_dir = Path(__file__).resolve().parent.parent / 'communities' / community_name
    
    # Safety check before deletion
    if cleanup_dir.exists() and cleanup_dir.is_dir():
        communities_base = Path(__file__).resolve().parent.parent / 'communities'
        try:
            cleanup_dir.resolve().relative_to(communities_base.resolve())
            shutil.rmtree(cleanup_dir)
            print(f"[CLEANUP] Removed existing: {cleanup_dir}")
        except ValueError:
            raise ValueError(f"Safety check failed: {cleanup_dir} is not within communities directory")
    
    # 1. Ensure all necessary directories exist
    print(f"[WORKFLOW] Step 1: Creating directories...")
    create_community_directories(community_name)

    # 2. Create manifest with already-validated requirements
    print(f"[WORKFLOW] Step 2: Creating manifest...")
    create_manifest(community_name, requirements)
    print(f"[WORKFLOW] Requirements: {requirements}")

    # 3. Copy archetype files before any simulation or analysis
    print(f"[WORKFLOW] Step 3: Copying archetype files...")
    copy_archetype_files(community_name, requirements)
    print(f"[WORKFLOW] Step 3 complete.")

    # 4. Update weather location in archetypes
    print(f"[WORKFLOW] Step 4: Updating weather location...")
    update_weather_location(community_name)
    print(f"[WORKFLOW] Step 4 complete.")

    # 5. Run HPXML conversion and simulation for each archetype
    print(f"[WORKFLOW] Step 5: Running HPXML conversion and simulations...")
    run_hpxml_conversion(community_name, requirements)
    print(f"[WORKFLOW] Step 5 complete.")

    # 6. Delegate aggregation and output to calculate_community_analysis.py
    print("\nDelegating aggregation and output to calculate_community_analysis.py...")
    script_path = Path(__file__).resolve().parent / 'calculate_community_analysis.py'
    result = subprocess.run([
        sys.executable,
        str(script_path),
        community_name
    ], capture_output=True, text=True)
    if result.returncode == 0:
        print(result.stdout)
    else:
        print(f"Error running calculate_community_analysis.py: {result.stderr}")
        return 1

    # 7. Debug timeseries and H2K files
    print(f"[WORKFLOW] Running debug validation...")
    debug_script = Path(__file__).resolve().parent / 'debug_outputs.py'
    result = subprocess.run([
        sys.executable,
        str(debug_script),
        community_name
    ], capture_output=True, text=True)
    
    if result.returncode == 0:
        print(f"Debug validation complete. Check: communities/{community_name}/analysis/output_debug.log")
        if result.stdout:
            print(result.stdout)
    else:
        print(f"Warning: Debug validation had issues: {result.stderr}")
    
    print(f"Analysis completed successfully for {community_name}")

    # 8. Remove archetypes/output directory after successful analysis
    output_dir = Path(__file__).resolve().parent.parent / 'communities' / community_name / 'archetypes' / 'output'
    
    # Safety check before removal
    if output_dir.exists() and output_dir.is_dir():
        expected_base = Path(__file__).resolve().parent.parent / 'communities' / community_name
        try:
            output_dir.resolve().relative_to(expected_base.resolve())
            shutil.rmtree(output_dir)
            print(f"Removed directory: {output_dir}")
        except ValueError:
            print(f"[WARNING] Safety check failed for output directory removal: {output_dir}")
    
    print(f"All done!")
    return 0

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python process_community_workflow.py <community_name>")
        sys.exit(1)
        
    community_name = sys.argv[1]
    main(community_name)