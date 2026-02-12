
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

- [Installation Guide](INSTALLATION.md)

## Command Reference

### CLI Commands (Recommended)

After installing the package with `uv sync`, use the main entry point:

```bash
process-community "Old Crow"
```

Alternatively, run the Python module directly:
```bash
python3 src/workflow/process_community_workflow.py "Old Crow"
```

### Docker Commands

If you're using Docker:

```bash
# Build the image (first time only - requires source-archetypes to be downloaded first!)
docker build -t community-energy-orchestrator .

# Run the API server
docker run -p 8000:8000 community-energy-orchestrator

# OR use docker-compose (recommended)
docker-compose up

# Stop and clean up
docker-compose down
```

With volume mounts to persist outputs on your host machine:

Linux/macOS:

```bash
docker run -p 8000:8000 \
  -v $(pwd)/communities:/app/communities \
  -v $(pwd)/output:/app/output \
  -v $(pwd)/logs:/app/logs \
  community-energy-orchestrator
```

Windows (PowerShell):

```powershell
docker run -p 8000:8000 `
  -v ${PWD}/communities:/app/communities `
  -v ${PWD}/output:/app/output `
  -v ${PWD}/logs:/app/logs `
  community-energy-orchestrator
```

Access the API at http://localhost:8000/docs

**Note:** The Docker container runs the FastAPI server by default. To run the CLI script (`process_community_workflow.py`), you can:

Linux/macOS:

```bash
# Run CLI workflow in Docker (interactive mode)
docker run -it community-energy-orchestrator \
  process-community "Old Crow"

# With volume mounts to save outputs
docker run -it \
  -v $(pwd)/communities:/app/communities \
  -v $(pwd)/logs:/app/logs \
  community-energy-orchestrator \
  process-community "Old Crow"
```

Windows (PowerShell):

```powershell
# Run CLI workflow in Docker (interactive mode)
docker run -it community-energy-orchestrator `
  process-community "Old Crow"

# With volume mounts to save outputs
docker run -it `
  -v ${PWD}/communities:/app/communities `
  -v ${PWD}/logs:/app/logs `
  community-energy-orchestrator `
  process-community "Old Crow"
```

### `process_community_workflow.py` (main entrypoint)
Runs the full workflow for a single community.

Linux/macOS:

```bash
# Recommended (after uv sync)
process-community "Old Crow"

# Or use Python directly
python3 src/workflow/process_community_workflow.py "Old Crow"
```

Windows (PowerShell):

```powershell
# Recommended (after uv sync)
process-community "Old Crow"

# Or use Python directly
python src\workflow\process_community_workflow.py "Old Crow"
```

Notes:
- Community names with spaces must be quoted.
- The workflow deletes `communities/<Community Name>/` at the start of each run.

### API (`src/app/main.py`)
Runs the FastAPI server so you can start a workflow run via HTTP and poll for status.


Start the server:

Linux/macOS:

```bash
python3 -m uvicorn src.app.main:app
```

Windows (PowerShell):

```powershell
python -m uvicorn src.app.main:app
```

Open the interactive docs:

- http://localhost:8000/docs

Notes:
- The API server keeps running until you stop it with `Ctrl+C`.
- Run state is stored in memory (restarting the server clears run history).
- The API enforces a single active run per server process.
- **Import path:** Use `src.app.main:app` in dev environments. Docker uses `app.main:app` (see [Docker Guide](DOCKER.md)).

### Supporting scripts

These modules are called internally by the workflow but can also be run directly for debugging:

- `src/workflow/calculate_community_analysis.py`: aggregates timeseries into community outputs
- `src/workflow/change_weather_location_regex.py`: updates weather reference in `.H2K` files
- `src/workflow/debug_outputs.py`: validates outputs and writes debug logs

**Note:** Most users should just use `process-community` which runs the complete workflow.

## Common Workflows

### 1) List available communities

See [Communities](COMMUNITIES.md) for the full list:

Note: `communities/` is generated locally by the workflow (and may not exist until you run a community).

### 2) Run a community

Linux/macOS:

```bash
# Using CLI command
process-community "Rankin Inlet"

# Or using Python directly
python3 src/workflow/process_community_workflow.py "Rankin Inlet"
```

Windows (PowerShell):

```powershell
# Using CLI command
process-community "Rankin Inlet"

# Or using Python directly
python src\workflow\process_community_workflow.py "Rankin Inlet"
```

### 3) Re-run a community
The workflow is designed to be re-runnable; it clears the specified community directory on each run.

Linux/macOS:

```bash
python3 src/workflow/process_community_workflow.py "Old Crow"
```

Windows (PowerShell):

```powershell
python src\workflow\process_community_workflow.py "Old Crow"
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

### Converter installation issues
If you see errors about `h2k-hpxml` or OpenStudio, try:

```bash
h2k-hpxml --help
os-setup --help
```

Reminder:
- `src/source-archetypes/` is a local input folder you have to download.
