# Community Energy Orchestrator

## Background
This repository orchestrates the workflow for processing community energy models:

- Copies Hot2000 archetype models (`.H2K`) into a per-community workspace
- Updates each copied model’s weather reference to match the target community
- Converts `.H2K` → HPXML and runs EnergyPlus simulations to produce hourly results
- Aggregates outputs into community-level summary artifacts

Changing the weather reference drives downstream model behavior because heating/cooling loads depend on climate.

## Interface
This repo supports three interfaces:

1) **CLI workflow script** (runs one community end-to-end)

Linux/macOS:

```bash
# Recommended (after uv sync)
process-community "Old Crow"

# Or directly
python3 backend/workflow/process_community_workflow.py "Old Crow"
```

Windows (PowerShell):

```powershell
# Recommended (after uv sync)
process-community "Old Crow"

# Or directly
python backend\workflow\process_community_workflow.py "Old Crow"
```

> **Windows PowerShell:** Communities with French characters (Gamètì, Déline) require UTF-8 setup. Run once:
> ```powershell
> [Console]::OutputEncoding = [System.Text.Encoding]::UTF8
> $env:PYTHONUTF8 = "1"
> ```
> Or add to PowerShell profile. See [Installation Guide](docs/INSTALLATION.md#step-4-activate-the-virtual-environment) for details. Git Bash doesn't need this.

2) **REST API** (FastAPI) for starting runs and polling status

Linux/macOS:

```bash
python3 -m uvicorn app.main:app --host 0.0.0.0
```

Windows (PowerShell):

```powershell
python -m uvicorn app.main:app --host 0.0.0.0
```

Then open the Swagger UI at:

- http://localhost:8000/docs

3) **Web Frontend** (React + Vite) for visualizing results in a browser

```bash
cd frontend
npm install
npm run dev
```

Then open http://localhost:5173 — requires the API to be running on port 8000.

## Documentation
- [Installation Guide](docs/INSTALLATION.md) - Complete setup instructions for all platforms
- [Docker Guide](docs/DOCKER.md) - Complete Docker deployment guide
- [User Guide](docs/USER_GUIDE.md) - Complete guide to using the program
- [Communities](docs/COMMUNITIES.md) - List of all available communities to test
- [Contributing](CONTRIBUTING.md) - Development setup, testing, and code style

## Docker Quick Start (Recommended for Sharing)

If you prefer containerized deployment:

```bash
# 1) Clone the repo
git clone https://github.com/canmet-energy/community-energy-orchestrator.git
cd community-energy-orchestrator

# 2) Download the archetype library (needed before running, not building)
# Go to https://github.com/canmet-energy/housing-archetypes.git
# Navigate to data/h2k_files/existing-stock
# Download: retrofit-archetypes-for-diesel-reduction-modelling-in-remote-communities
# Rename it to 'source-archetypes' and place it in the src/ directory
# Note: The archetype library is gitignored and mounted as a volume at runtime

# 3) Build the Docker image
docker build -t community-energy-orchestrator .

# 4) Run with docker-compose (recommended - starts API + frontend):
docker-compose up

# OR run the API only:
docker run -p 8000:8000 community-energy-orchestrator
```

Then open:
- Frontend: http://localhost:5173
- API Swagger UI: http://localhost:8000/docs

**Note:** Docker installation automatically handles all dependencies (Python, uv, OpenStudio, EnergyPlus) inside the container. You only need Docker installed on your system.

**Important:** The archetype library (`data/source-archetypes/`) is not baked into the Docker image — it's mounted as a volume at runtime via docker-compose. You need it before running `docker-compose up`, not before building.

## Repository Layout
- `backend/workflow/process_community_workflow.py`: end-to-end workflow driver
- `backend/workflow/service.py`: public API for workflow operations
- `data/source-archetypes/`: Hot2000 `.H2K` archetype library organized in subdirectories by type (local/downloaded, mounted into container)
- `output/<Community Name>/`: per-run working directory and outputs (generated locally)
- `data/json/`: community requirements + weather mapping configuration

## CLI Command

After installation with `uv sync`, run the workflow:

```bash
process-community "Old Crow"
```

This is equivalent to `python3 backend/workflow/process_community_workflow.py "Old Crow"` but cleaner.

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
# Rename it to 'source-archetypes' and place it in the data/ directory

# 7) Run a community
python3 backend/workflow/process_community_workflow.py "Old Crow"

# Optional: run the API instead
# python3 -m uvicorn app.main:app --host 0.0.0.0
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

# 4b) Configure UTF-8 (REQUIRED for French characters)
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$env:PYTHONUTF8 = "1"
# To make permanent: notepad $PROFILE (add the two lines above)

# 5) Install/verify simulation dependencies (OpenStudio/EnergyPlus)
os-setup --auto-install
os-setup --test-installation

# If commands are not found on Windows, try:
# os-setup --add-to-path

# 6) Provide the archetype library
# Go to https://github.com/canmet-energy/housing-archetypes.git
# Navigate to data/h2k_files/existing-stock
# Download the folder: retrofit-archetypes-for-diesel-reduction-modelling-in-remote-communities
# Rename it to 'source-archetypes' and place it in the data\ directory

# 7) Run a community
python backend\workflow\process_community_workflow.py "Old Crow"

# Optional: run the API instead
# python -m uvicorn app.main:app --host 0.0.0.0
```

For first-time setup on a new machine (OpenStudio/EnergyPlus dependencies), follow: [Installation Guide](docs/INSTALLATION.md)

## Workflow Examples

### List available communities

See the full list of communities [here](docs/COMMUNITIES.md).

### Run a community

Linux/macOS:

```bash
python3 backend/workflow/process_community_workflow.py "Rankin Inlet"
```

Windows (PowerShell):

```powershell
python backend\workflow\process_community_workflow.py "Rankin Inlet"
```

### Where outputs go
After a run, you’ll typically see:

- `output/<Community Name>/archetypes/`: weather-updated `.H2K` models used for simulation
- `output/<Community Name>/timeseries/`: per-building `*-results_timeseries.csv`
- `output/<Community Name>/analysis/`: aggregated outputs (community totals, logs, etc.)

Note: the workflow currently deletes the existing `output/<Community Name>/` directory at the start of each run to ensure a clean rebuild.

## Contributing

Contributions are welcome! See [CONTRIBUTING.md](CONTRIBUTING.md) for development setup, testing, code style, and submission guidelines.

Quick start:

```bash


pip install uv
uv sync --all-extras
make fix-all          # Format, lint, and test before pushing
```
## Licensing and Relationship to Other Software

This project is licensed under the GNU Affero General Public License
v3.0 or later (AGPL‑3.0+).

It is designed to interoperate with [btap_batch](https://github.com/canmet-energy/btap_batch), which is released under the same AGPL‑3.0+ licence. Modifications to either project are subject to the same copyleft obligations under AGPL‑3.0+.

## Citing This Work 

If you use the Community Energy Orchestrator in your research, please cite it as:

```text
Natural Resources Canada
Community Energy Orchestrator
https://github.com/canmet-energy/community-energy-orchestrator
```
