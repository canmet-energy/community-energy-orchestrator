import os
from pathlib import Path

def debug_timeseries_outputs(community_name, requirements):
    """
    Check which archetype types are missing timeseries outputs for the community.
    Writes a debug report to communities/<community>/archetypes/timeseries_debug.log
    """
    output_base = Path(f'communities/{community_name}/archetypes/output')
    debug_log_path = Path(f'communities/{community_name}/archetypes/timeseries_debug.log')
    found_counts = {k: 0 for k in requirements}
    missing = {}
    for era_type in requirements:
        # Find all output subdirs for this era_type
        pattern = f'{era_type}_'
        matches = [p for p in output_base.glob(f'{era_type}_*/run/results_timeseries.csv')]
        found_counts[era_type] = len(matches)
        required = requirements[era_type]
        if len(matches) < required:
            missing[era_type] = required - len(matches)
    with open(debug_log_path, 'w') as f:
        f.write(f"Timeseries output debug for {community_name}\n")
        for era_type in requirements:
            f.write(f"{era_type}: required={requirements[era_type]}, found={found_counts[era_type]}\n")
        if missing:
            f.write("\nMissing timeseries outputs by type:\n")
            for k, v in missing.items():
                f.write(f"{k}: {v} missing\n")
        else:
            f.write("\nAll required timeseries outputs found.\n")
    return debug_log_path
