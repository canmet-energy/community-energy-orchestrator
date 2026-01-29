
# User Guide

Complete guide for running community workflows and understanding outputs.

## Table of Contents
- [Installation](#installation)
- [Command Reference](#command-reference)
- [Common Workflows](#common-workflows)
- [Outputs](#outputs)
- [Troubleshooting](#troubleshooting)

## Installation
See the installation guide for full setup instructions:

- [docs/INSTALLATION.md](INSTALLATION.md)

## Command Reference

### `process_community_workflow.py` (main entrypoint)
Runs the full workflow for a single community.

```bash
python src/process_community_workflow.py "Old Crow"
```

Notes:
- Community names with spaces must be quoted.
- The workflow deletes `communities/<Community Name>/` at the start of each run.

### Supporting scripts

These are invoked by the workflow internally:

- `src/change_weather_location_regex.py`: updates weather reference in copied `.H2K` files
- `src/calculate_community_analysis.py`: aggregates timeseries into community outputs
- `src/debug_outputs.py`: validates outputs and writes debug logs

## Common Workflows

### 1) List available communities

See [COMMUNITIES.md](COMMUNITIES.md) for the full list:

Note: `communities/` is generated locally by the workflow (and may not exist until you run a community).

### 2) Run a community

Choose from [COMMUNITIES.md](COMMUNITIES.md):

```bash
python src/process_community_workflow.py "Rankin Inlet"
```

### 3) Re-run a community
The workflow is designed to be re-runnable; it clears the community directory on each run.

```bash
python src/process_community_workflow.py "Old Crow"
```

## Outputs

After a successful run, outputs live under:

- `communities/<Community Name>/archetypes/`: weather-updated `.H2K` files used for simulation
- `communities/<Community Name>/archetypes/output/`: converter outputs (may be deleted at end of workflow)
- `communities/<Community Name>/timeseries/`: per-building `*-results_timeseries.csv`
- `communities/<Community Name>/analysis/`: aggregated outputs and logs

Useful logs:
- `logs/archetype_copy_debug.log`: what requirements were read + how many archetypes matched/copied

## Troubleshooting

### Slow runs
If runs suddenly become much slower, common causes are:

- Too many archetypes were copied into `communities/<Community Name>/archetypes/`, which increases the number of simulations.
- OpenStudio/EnergyPlus setup is missing or misconfigured (leading to retries or failures).

Check `logs/archetype_copy_debug.log` to confirm how many archetypes were copied for each requirement.

### “Weather in source archetypes changed”
The source archetype library under `src/source-archetypes/` is intended to be treated as read-only.

If you suspect the source is being modified, verify the community archetype directory is not a symlink to the source:

```bash
COMMUNITY="Old Crow"
readlink -f "communities/$COMMUNITY/archetypes"
readlink -f "src/source-archetypes"
```

If both resolve to the same path, updates to the “community copy” will also edit the source.

### Converter installation issues
If you see errors about `h2k-hpxml` or OpenStudio, start with:

```bash
h2k-hpxml --help
os-setup --help
```

Then follow the converter’s docs:

- `src/h2k-hpxml/docs/INSTALLATION.md`

Reminder:
- `src/h2k-hpxml/` is a git submodule and must be initialized.
- `src/source-archetypes/` is a local input folder (not committed).
