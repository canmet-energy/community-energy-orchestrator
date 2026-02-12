# Community Energy Orchestrator

## Background
This repository orchestrates the workflow for processing community energy models:

- Copies Hot2000 archetype models (`.H2K`) into a per-community workspace
- Updates each copied model’s weather reference to match the target community
- Converts `.H2K` → HPXML and runs EnergyPlus simulations to produce hourly results
- Aggregates outputs into community-level summary artifacts

Changing the weather reference drives downstream model behavior because heating/cooling loads depend on climate.

## Interface
This repo supports two interfaces:

1) **CLI workflow script** (runs one community end-to-end)

Linux/macOS:

```bash
# Recommended (after uv sync)
process-community "Old Crow"

# Or directly
python3 src/workflow/process_community_workflow.py "Old Crow"
```

Windows (PowerShell):

```powershell
# Recommended (after uv sync)
process-community "Old Crow"

# Or directly
python src\workflow\process_community_workflow.py "Old Crow"
```

2) **REST API** (FastAPI) for starting runs and polling status

Linux/macOS:

```bash
python3 -m uvicorn src.app.main:app
```

Windows (PowerShell):

```powershell
python -m uvicorn src.app.main:app
```

Then open the Swagger UI at:

- http://localhost:8000/docs

> **Note:** Dev environments use `src.app.main:app`. Docker uses `app.main:app` (see [Docker Guide](docs/DOCKER.md)).

## Documentation
- [Installation Guide](docs/INSTALLATION.md) - Complete setup instructions for all platforms
- [Docker Guide](docs/DOCKER.md) - Complete Docker deployment guide
- [User Guide](docs/USER_GUIDE.md) - Complete guide to using the program
- [Communities](docs/COMMUNITIES.md) - List of all available communities to test

## Docker Quick Start (Recommended for Sharing)

If you prefer containerized deployment:

```bash
# 1) Clone the repo
git clone https://github.com/canmet-energy/community-energy-orchestrator.git
cd community-energy-orchestrator

# 2) CRITICAL: Download the archetype library BEFORE building
# Go to https://github.com/canmet-energy/housing-archetypes.git
# Navigate to data/h2k_files/existing-stock
# Download: retrofit-archetypes-for-diesel-reduction-modelling-in-remote-communities
# Rename it to 'source-archetypes' and place it in the src/ directory
# The build will FAIL if this directory is missing!

# 3) Build the Docker image
docker build -t community-energy-orchestrator .

# 4) Run the API server
docker run -p 8000:8000 community-energy-orchestrator

# OR use docker-compose for easier management:
docker-compose up
```

Then open the Swagger UI at http://localhost:8000/docs

**Note:** Docker installation automatically handles all dependencies (Python, uv, OpenStudio, EnergyPlus) inside the container. You only need Docker installed on your system.

**Important:** The build validates that `source-archetypes/` exists and contains files. If you skip step 2, the build will fail with a clear error message.

## Repository Layout
- `src/workflow/process_community_workflow.py`: end-to-end workflow driver
- `src/workflow/service.py`: public API for workflow operations
- `src/h2k-hpxml/`: converter used to generate HPXML + run simulations (git submodule)
- `src/source-archetypes/`: Hot2000 `.H2K` archetype library (local/downloaded)
- `communities/<Community Name>/`: per-run working directory and outputs (generated locally)
- `csv/`: community requirements + weather mapping inputs

## CLI Command

After installation with `uv sync`, run the workflow:

```bash
process-community "Old Crow"
```

This is equivalent to `python3 src/workflow/process_community_workflow.py "Old Crow"` but cleaner.

See [User Guide](docs/USER_GUIDE.md) for details.

## Quick Start

Choose your OS:

### Linux/macOS

```bash
# 1) Clone the repo
git clone https://github.com/canmet-energy/community-energy-orchestrator.git
cd community-energy-orchestrator

# 2) Install uv (if not already installed)
pip install uv

# 3) Sync dependencies (creates venv and installs everything)
uv sync

# 4) Activate the virtual environment
source .venv/bin/activate

# 5) Install/verify simulation dependencies (OpenStudio/EnergyPlus)
os-setup --auto-install
os-setup --test-installation

# If you hit permission errors, try:
# sudo os-setup --auto-install

# 6) Provide the archetype library
# Go to https://github.com/canmet-energy/housing-archetypes.git
# Navigate to data/h2k_files/existing-stock
# Download the folder: retrofit-archetypes-for-diesel-reduction-modelling-in-remote-communities
# Rename it to 'source-archetypes' and place it in the src/ directory

# 7) Run a community
python3 src/workflow/process_community_workflow.py "Old Crow"

# Optional: run the API instead
# python3 -m uvicorn src.app.main:app
```

### Windows (PowerShell)

```powershell
# 1) Clone the repo
git clone https://github.com/canmet-energy/community-energy-orchestrator.git
cd community-energy-orchestrator

# 2) Install uv (if not already installed)
pip install uv

# 3) Sync dependencies (creates venv and installs everything)
uv sync

# 4) Activate the virtual environment
.venv\Scripts\Activate.ps1

# 5) Install/verify simulation dependencies (OpenStudio/EnergyPlus)
os-setup --auto-install
os-setup --test-installation

# If commands are not found on Windows, try:
# os-setup --add-to-path

# 6) Provide the archetype library
# Go to https://github.com/canmet-energy/housing-archetypes.git
# Navigate to data/h2k_files/existing-stock
# Download the folder: retrofit-archetypes-for-diesel-reduction-modelling-in-remote-communities
# Rename it to 'source-archetypes' and place it in the src\ directory

# 7) Run a community
python src\workflow\process_community_workflow.py "Old Crow"

# Optional: run the API instead
# python -m uvicorn src.app.main:app
```

For first-time setup on a new machine (OpenStudio/EnergyPlus dependencies), follow: [Installation Guide](docs/INSTALLATION.md)

## Workflow Examples

### List available communities

See the full list of communities [here](docs/COMMUNITIES.md).

### Run a community

Linux/macOS:

```bash
python3 src/workflow/process_community_workflow.py "Rankin Inlet"
```

Windows (PowerShell):

```powershell
python src\workflow\process_community_workflow.py "Rankin Inlet"
```

### Where outputs go
After a run, you’ll typically see:

- `communities/<Community Name>/archetypes/`: weather-updated `.H2K` models used for simulation
- `communities/<Community Name>/timeseries/`: per-building `*-results_timeseries.csv`
- `communities/<Community Name>/analysis/`: aggregated outputs (community totals, logs, etc.)

Note: the workflow currently deletes the existing `communities/<Community Name>/` directory at the start of each run to ensure a clean rebuild.
