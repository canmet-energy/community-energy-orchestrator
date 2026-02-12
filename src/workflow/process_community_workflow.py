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
import stat
import sys
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

import pandas as pd

from workflow.change_weather_location_regex import change_weather_code
from workflow.config import get_max_workers, get_archetype_selection_seed, ARCHETYPE_TYPE_PATTERNS
from workflow.core import communities_dir, logs_dir, source_archetypes_dir
from workflow.requirements import get_community_requirements, get_weather_location
from workflow.calculate_community_analysis import select_and_sum_timeseries
from workflow.debug_outputs import main as debug_main

def remove_readonly(func, path, exc):
    """Error handler for shutil.rmtree to handle read-only files."""
    if not os.access(path, os.W_OK):
        os.chmod(path, stat.S_IWUSR | stat.S_IRUSR | stat.S_IXUSR)
        func(path)
    else:
        raise

def safe_rmtree(path):
    """Remove directory tree with read-only file handling, compatible with all Python versions."""
    if sys.version_info >= (3, 12):
        shutil.rmtree(path, onexc=remove_readonly)
    else:
        shutil.rmtree(path, onerror=remove_readonly)


def create_manifest(community_name, requirements):
    """
    Create manifest file documenting requirements and simulation status.
    
    Args:
        community_name: Name of the community
        requirements: Dict of housing types to required counts
    
    Returns:
        Path to created manifest file
    """
    manifest_path = communities_dir() / community_name / 'archetypes' / f'{community_name}-manifest.md'
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
    
    Returns:
        int: Final count of files for this building type
    """
    files = sorted(f for f in os.listdir(timeseries_dir) if f.startswith(building_type) and f.endswith("-results_timeseries.csv"))
    if not files:
        print(f"[ERROR] No source files found for {building_type}")
        return 0
    count = len(files)

    seed_str = get_archetype_selection_seed()
    rng = random.Random(seed_str) if seed_str is not None else random.Random()
    source_files = [f for f in files if '_DUPLICATE_' not in f] or files
    
    if count >= required_count:
        print(f"{building_type}: Already have {count} files (required: {required_count})")
        return count
    
    while count < required_count:
        src_file = rng.choice(source_files)
        src_path = os.path.join(timeseries_dir, src_file)
        new_name = f"{building_type}_DUPLICATE_{count+1}-results_timeseries.csv"
        dst_path = os.path.join(timeseries_dir, new_name)
        shutil.copy(src_path, dst_path)
        print(f"Created {new_name}")
        files.append(new_name)
        count += 1
    
    return count

def create_community_directories(community_name):
    """
    Create standard directory structure for a community.
    
    Args:
        community_name: Name of the community
    
    Returns:
        Path to community base directory
    """
    base_path = communities_dir() / community_name
    archetypes_path = base_path / 'archetypes'
    timeseries_path = base_path / 'timeseries'
    analysis_path = base_path / 'analysis'
    for path in [base_path, archetypes_path, timeseries_path, analysis_path]:
        path.mkdir(parents=True, exist_ok=True)
    return base_path

def copy_single_archetype(src_file, dst_file):
    """Copy a single archetype file with error handling."""
    try:
        shutil.copy(src_file, dst_file)
        return True
    except Exception as e:
        print(f"[ERROR] Failed to copy {src_file} to {dst_file}: {e}")
        return False

def copy_archetype_files(community_name, requirements):
    """
    Copy archetype files matching requirements (targets N+20% per type).
    
    Args:
        community_name: Name of the community
        requirements: Dict of housing types to required counts
    """

    archetypes_source = source_archetypes_dir()
    
    if not archetypes_source.exists():
        raise FileNotFoundError(f"Source archetypes directory not found: {archetypes_source}")
    
    base_path = communities_dir() / community_name / 'archetypes'
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

    debug_log_path = logs_dir() / 'archetype_copy_debug.log'
    debug_log_path.parent.mkdir(parents=True, exist_ok=True)
    seed_str = get_archetype_selection_seed()
    rng = random.Random(seed_str) if seed_str is not None else random.Random()

    copy_tasks = []

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
                copy_tasks.append((src_file, dst_file))
                debug_log.write(f"[DEBUG] Copying {src_file} -> {dst_file}\n")
    
    # Perform copying in parallel
    if not copy_tasks:
        print("[WARNING] No archetype files to copy based on requirements.")
        return
    
    max_workers = min(get_max_workers(),len(copy_tasks))
    print(f"[PARALLEL] Copying {len(copy_tasks)} archetype files with {max_workers} workers")   

    copied_count = 0
    with ProcessPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(copy_single_archetype, src_file, dst_file): (src_file, dst_file) for src_file, dst_file in copy_tasks}
        for future in as_completed(futures):
            try:
                if future.result():
                    copied_count += 1
            except Exception as e:
                src_file, dst_file = futures[future]
                print(f"[ERROR] Exception copying {src_file} to {dst_file}: {e}")
    
    print(f"Copied {copied_count} archetype files for {community_name}")

def update_single_weather_file(file_path, weather_location):
    """Update weather location in a single HOT2000 file. Module-level for pickling."""
    try:
        change_weather_code(file_path, location=weather_location, validate=False, debug=False)
        return True
    except Exception as e:
        print(f"[ERROR] Failed to update weather location in {file_path}: {e}")
        return False
    
def update_weather_location(community_name):
    """
    Update HOT2000 files to use correct weather location.
    
    Args:
        community_name: Name of the community
    """
    base_path = communities_dir() / community_name / 'archetypes'
    weather_location = get_weather_location(community_name)
    
    h2k_files = list(base_path.glob('*.H2K'))
    if not h2k_files:
        print(f"[WARNING] No H2K files found in {base_path} to update weather location.")
        return
    
    max_workers = min(get_max_workers(), len(h2k_files))
    print(f"[PARALLEL] Updating weather location in {len(h2k_files)} files with {max_workers} workers")

    updated_count = 0
    with ProcessPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(update_single_weather_file, h2k_file, weather_location): h2k_file for h2k_file in h2k_files}

        for future in as_completed(futures):
            try:
                if future.result():
                    updated_count += 1
            except Exception as e:
                h2k_file = futures[future]
                print(f"[ERROR] Exception updating weather location in {h2k_file}: {e}")
    print(f"Updated weather location in {updated_count} files for {community_name}")


def _copy_single_timeseries(building_dir, timeseries_dir):
    """Copy timeseries file for a single building. Module-level for pickling."""
    try:
        run_dir = building_dir / 'run'
        if run_dir.exists():
            results_file = run_dir / 'results_timeseries.csv'
            if results_file.exists():
                target_name = f"{building_dir.name}-results_timeseries.csv"
                target_path = timeseries_dir / target_name
                if target_path.exists():
                    print(f"[WARNING] Target file already exists: {target_path}")
                    return False
                shutil.copy(results_file, target_path)
                return True
    except Exception as e:
        print(f"[ERROR] Failed to copy {building_dir.name}: {e}")
    return False

def collect_timeseries_parallel(output_dir, timeseries_dir):
    """
    Parallel collection of timeseries files from h2k-hpxml output.
    Each worker copies files from a separate building directory.
    
    Args:
        output_dir: Path to archetypes/output directory
        timeseries_dir: Path to community timeseries directory
    
    Returns:
        int: Number of files successfully collected
    """
    building_dirs = [d for d in output_dir.iterdir() if d.is_dir()]
    
    if not building_dirs:
        print("[WARNING] No building directories found in output")
        return 0
    
    collected = 0
    max_workers = min(get_max_workers(), len(building_dirs))
    
    print(f"[PARALLEL] Collecting timeseries files with {max_workers} workers")
    
    with ProcessPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(_copy_single_timeseries, bdir, timeseries_dir): bdir for bdir in building_dirs}

        for future in as_completed(futures):
            try:
                if future.result():
                    collected += 1
            except Exception as e:
                building_dir = futures[future]
                print(f"[ERROR] Exception collecting {building_dir.name}: {e}")
    return collected

def run_hpxml_conversion(community_name, requirements):
    """
    Convert HOT2000 files to HPXML, run simulations, and collect timeseries results.
    Duplicates timeseries files as needed to meet requirements.
    
    Args:
        community_name: Name of the community
    """
    base_path = communities_dir() / community_name / 'archetypes'
    output_path = base_path / 'output'

    # Create output directory if not already created
    output_path.mkdir(parents= True, exist_ok= True)

    # Rename .H2K files to .h2k (h2k_hpxml uses case-sensitive glob("*.h2k"))
    renamed = 0
    for p in list(base_path.iterdir()):
        if p.is_file() and p.suffix.upper() == '.H2K' and p.suffix != '.h2k':
            # Use two-step rename to handle case-insensitive filesystems
            tmp = p.with_suffix('.h2k.tmp')
            p.rename(tmp)
            tmp.rename(p.with_suffix('.h2k'))
            renamed += 1
    
    if renamed:
        print(f"[HPXML] Normalized {renamed} files from .H2K to .h2k")

    print(f"[HPXML] Starting HPXML conversion for files in: {base_path}")
    print(f"[HPXML] Output will be saved to: {output_path}")

    # Run h2k-hpxml conversion using the Python library API.
    try:
        from h2k_hpxml.api import run_full_workflow, validate_dependencies
    except Exception as e:
        raise RuntimeError(
            "Failed to import h2k_hpxml. Ensure dependencies are installed (e.g., 'uv sync') "
            "and that pyproject.toml pins the git dependency correctly."
        ) from e

    deps = validate_dependencies()
    if not deps.get("valid", False):
        missing = deps.get("missing", [])
        raise RuntimeError(
            "h2k-hpxml external dependencies are missing or misconfigured. "
            f"Missing: {missing}. "
            "Run: uv run os-setup --install-quiet  (then)  uv run os-setup --check-only"
        )

    results = run_full_workflow(
        input_path=base_path,
        output_path=output_path,
        simulate=True,
        output_format="csv",
        hourly_outputs=["ALL"],
        debug=False,
    )

    print(
        "[HPXML] Workflow complete: "
        f"{results.get('successful_conversions', 0)} succeeded, "
        f"{results.get('failed_conversions', 0)} failed."
    )
    if results.get("errors"):
        print("[HPXML] Errors encountered during conversion/simulation:")
        for err in results["errors"]:
            print(f"  - {err}")

    # Collect timeseries files from archetypes/output using parallel processing
    print(f"[HPXML] Collecting timeseries files from output directories...")
    base_dir = communities_dir() / community_name
    output_dir = base_dir / 'archetypes' / 'output'
    timeseries_dir = base_dir / 'timeseries'
    timeseries_dir.mkdir(parents=True, exist_ok=True)
    
    # Use parallel collection for performance
    if output_dir.exists():
        collected = collect_timeseries_parallel(output_dir, timeseries_dir)
    else:
        collected = 0
    
    print(f"Collected {collected} timeseries files for {community_name}")

    # Ensure each required type has enough files by duplicating as needed
    timeseries_dir_path = str(timeseries_dir)
    verification_failed = False
    for building_type, required_count in requirements.items():
        actual_count = duplicate_missing_timeseries(timeseries_dir_path, building_type, required_count)
        if actual_count < required_count:
            print(f"[ERROR] Failed to reach required count for {building_type}: {actual_count}/{required_count}")
            verification_failed = True
    
    if verification_failed:
        raise RuntimeError(f"Could not meet timeseries requirements for {community_name}")

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
        if not requirements or all(count == 0 for count in requirements.values()):
            raise ValueError(f"No valid requirements found for {community_name}. All counts are zero or missing.")
        print(f"[WORKFLOW] Community validated: {community_name}")
    except ValueError as e:
        print(f"[ERROR] {e}")
        raise
    except FileNotFoundError as e:
        print(f"[ERROR] {e}")
        raise
    
    # 0. Clean existing community directory to ensure fresh run
    print(f"[WORKFLOW] Step 0: Cleaning previous run data...")
    cleanup_dir = communities_dir() / community_name
    
    # Safety check before deletion
    if cleanup_dir.exists() and cleanup_dir.is_dir():
        communities_base = communities_dir()
        try:
            cleanup_dir.resolve().relative_to(communities_base.resolve())
            safe_rmtree(cleanup_dir)
            print(f"[CLEANUP] Removed existing: {cleanup_dir}")
        except PermissionError as e:
            print(f"[ERROR] Could not remove {cleanup_dir}: {e}")
            print(f"[ERROR] Some files may be open in an editor. Close all files in this community folder and try again.")
            raise PermissionError(f"Permission denied when cleaning {community_name} directory. Close any open files and try again.") from e
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

    # 6. Aggregate and output community analysis
    print("\nAggregating community energy analysis...")
    try:
        select_and_sum_timeseries(community_name)
    except Exception as e:
        print(f"Error in community analysis: {e}")
        raise RuntimeError(f"Community analysis failed: {e}") from e

    # 7. Debug timeseries and H2K files
    print(f"[WORKFLOW] Running debug validation...")
    try:
        debug_main(community_name)
        print(f"Debug validation complete. Check: communities/{community_name}/analysis/output_debug.log")
    except Exception as e:
        print(f"Warning: Debug validation had issues: {e}")
    
    print(f"Analysis completed successfully for {community_name}")
    

    # 8. Remove archetypes/output directory after successful analysis
    print(f"[WORKFLOW] Cleaning up archetypes/output directory...")
    output_dir = communities_dir() / community_name / 'archetypes'
    
    # Safety check before removal
    if output_dir.exists() and output_dir.is_dir():
        expected_base = communities_dir() / community_name
        try:
            output_dir.resolve().relative_to(expected_base.resolve())
            safe_rmtree(output_dir)
            print(f"Removed directory: {output_dir}")
        except PermissionError as e:
            print(f"[ERROR] Could not remove {output_dir}: {e}")
            print(f"[ERROR] Some files may be open in an editor. Close them and manually delete the output directory.")
            raise PermissionError(f"Permission denied when cleaning output directory. Close any open files in {community_name}/archetypes.") from e
        except ValueError:
            print(f"[WARNING] Safety check failed for output directory removal: {output_dir}")
    
    print(f"Workflow for {community_name} completed successfully, you are free to proceed!")
    return 0

def cli():
    """CLI entry point for running the workflow."""
    if len(sys.argv) != 2:
        print("Usage: process-community <community_name>")
        sys.exit(1)
        
    community_name = sys.argv[1]
    main(community_name)

if __name__ == "__main__":
    cli()