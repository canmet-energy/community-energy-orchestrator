# Community Energy Orchestrator

## Background
This repository orchestrates the workflow for processing community energy models:

- Copies Hot2000 archetype models (`.H2K`) into a per-community workspace
- Updates each copied model’s weather reference to match the target community
- Converts `.H2K` → HPXML and runs EnergyPlus simulations to produce hourly results
- Aggregates outputs into community-level summary artifacts

Changing the weather reference drives downstream model behavior because heating/cooling loads depend on climate.

## Interface
The primary interface is a Python workflow script:

```bash
python src/process_community_workflow.py "Old Crow"
```

## Documentation
- [Installation Guide](docs/INSTALLATION.md) - Complete setup instructions for all platforms
- [User Guide](docs/USER_GUIDE.md) - Complete guide to using the program
- [Communities](docs/COMMUNITIES.md) - List of all available communities to test
## Repository Layout
- `src/process_community_workflow.py`: end-to-end workflow driver
- `src/h2k-hpxml/`: converter used to generate HPXML + run simulations (git submodule)
- `src/source-archetypes/`: Hot2000 `.H2K` archetype library (local/downloaded)
- `communities/<Community Name>/`: per-run working directory and outputs (generated locally)
- `csv/`: community requirements + weather mapping inputs

## Quick Start

Choose your OS:

### Linux/macOS

```bash
# 1) Clone (includes submodules)
git clone --recurse-submodules https://github.com/micael-gourde/community-energy-orchestrator.git
cd community-energy-orchestrator

# 2) Create + activate venv
python3 -m venv .venv
source .venv/bin/activate

# 3) Install orchestrator dependencies
pip install -r requirements.txt

# 4) Install the converter package (provides h2k-hpxml + os-setup)
pip install -e src/h2k-hpxml

# 5) Install/verify simulation dependencies (OpenStudio/EnergyPlus)
os-setup --auto-install
os-setup --test-installation

# If you hit permission errors, try:
# sudo os-setup --auto-install

# 6) Provide the archetype library
# Ensure src/source-archetypes/ exists and contains .H2K files.

# 7) Run a community
python src/process_community_workflow.py "Old Crow"
```

### Windows (PowerShell)

```powershell
# 1) Clone (includes submodules)
git clone --recurse-submodules https://github.com/micael-gourde/community-energy-orchestrator.git
cd community-energy-orchestrator

# 2) Create + activate venv
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# 3) Install orchestrator dependencies
pip install -r requirements.txt

# 4) Install the converter package (provides h2k-hpxml + os-setup)
pip install -e src\h2k-hpxml

# 5) Install/verify simulation dependencies (OpenStudio/EnergyPlus)
os-setup --auto-install
os-setup --test-installation

# If 'h2k-hpxml' or 'os-setup' are not found, restart your terminal and confirm the venv is active.

# If commands are still not found on Windows, try:
# os-setup --add-to-path

# 6) Provide the archetype library
# Ensure src\source-archetypes\ exists and contains .H2K files.

# 7) Run a community
python src\process_community_workflow.py "Old Crow"
```

For first-time setup on a new machine (OpenStudio/EnergyPlus dependencies), follow: [Installation Guide](docs/INSTALLATION.md)

## Workflow Examples

### List available communities

See the full list of communities [here](docs/COMMUNITIES.md).

### Run a community

```bash
python src/process_community_workflow.py "Rankin Inlet"
```

### Where outputs go
After a run, you’ll typically see:

- `communities/<Community Name>/archetypes/`: weather-updated `.H2K` models used for simulation
- `communities/<Community Name>/timeseries/`: per-building `*-results_timeseries.csv`
- `communities/<Community Name>/analysis/`: aggregated outputs (community totals, logs, etc.)

Note: the workflow currently deletes the existing `communities/<Community Name>/` directory at the start of each run to ensure a clean rebuild.
