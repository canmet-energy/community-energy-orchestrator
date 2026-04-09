
# User Guide

Complete guide for running community workflows and understanding outputs.

## Table of Contents
- [Installation](#installation)
- [Command Reference](#command-reference)
- [Frontend](#frontend)
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
python3 backend/workflow/process_community_workflow.py "Old Crow"
```

**Windows PowerShell Users:** If processing communities with French characters, ensure UTF-8 is configured (see [Installation Guide](INSTALLATION.md#step-4-activate-the-virtual-environment)).

### Docker Commands

If you're using Docker:

```bash
# Build the image (first time only)
docker build -t community-energy-orchestrator .

# Run the API server
docker run -p 8000:8000 community-energy-orchestrator

# OR use docker-compose (recommended - starts API + frontend)
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

With docker-compose, the frontend is also available at http://localhost:5173

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
python3 backend/workflow/process_community_workflow.py "Old Crow"
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

### API (`backend/app/main.py`)
Runs the FastAPI server so you can start a workflow run via HTTP and poll for status.


Start the server:

Linux/macOS:

```bash
python3 -m uvicorn app.main:app --host 0.0.0.0
```

Windows (PowerShell):

```powershell
python -m uvicorn app.main:app --host 0.0.0.0
```

Open the interactive docs:

- http://localhost:8000/docs

Notes:
- The API server keeps running until you stop it with `Ctrl+C`.
- Run state is stored in memory (restarting the server clears run history).
- The API enforces a single active run per server process.

## Frontend

The web frontend provides a visual interface for selecting communities, running workflows, and viewing energy analysis results with interactive charts.

### Running with Docker Compose (easiest)

```bash
docker-compose up
```

The frontend is available at http://localhost:5173 (API starts automatically on port 8000).

### Running locally

Requires Node.js 18+ and the API running on port 8000.

```bash
# Start the API first (in one terminal)
python -m uvicorn app.main:app --host 0.0.0.0

# Start the frontend (in another terminal)
cd frontend
npm install
npm run dev
```

Then open http://localhost:5173

### Supporting scripts

These modules are called internally by the workflow but can also be run directly for debugging:

- `backend/workflow/calculate_community_analysis.py`: aggregates timeseries into community outputs
- `backend/workflow/change_weather_location_regex.py`: updates weather reference in `.H2K` files
- `backend/workflow/debug_outputs.py`: validates outputs and writes debug logs

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
python3 backend/workflow/process_community_workflow.py "Rankin Inlet"
```

Windows (PowerShell):

```powershell
# Using CLI command
process-community "Rankin Inlet"

# Or using Python directly
python backend\workflow\process_community_workflow.py "Rankin Inlet"
```

### 3) Re-run a community
The workflow is designed to be re-runnable; it clears the specified community directory on each run.

Linux/macOS:

```bash
python3 backend/workflow/process_community_workflow.py "Old Crow"
```

Windows (PowerShell):

```powershell
python backend\workflow\process_community_workflow.py "Old Crow"
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
- `data/source-archetypes/` is a local input folder you have to download.

### Windows PowerShell encoding errors

If communities with special characters (Gamètì, Déline, François) fail with encoding errors:

**Cause:** PowerShell defaults to Windows-1252 encoding instead of UTF-8, which prevents Python from correctly processing community names with French accents.

**Solution:** Configure PowerShell to use UTF-8 (this is a one-time setup):

```powershell
# Add to your PowerShell profile for permanent fix
notepad $PROFILE
# Add these lines:
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$env:PYTHONUTF8 = "1"
# Save and restart PowerShell
```

Or set temporarily for current session:
```powershell
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$env:PYTHONUTF8 = "1"
```

**Alternative:** Use Git Bash instead of PowerShell (Git Bash uses UTF-8 by default).
