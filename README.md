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
- Installation: [INSTALLATION.md](docs/INSTALLATION.md)
- User guide: [USER_GUIDE.md](docs/USER_GUIDE.md)
- Communities list: [COMMUNITIES.md](docs/COMMUNITIES.md)
## Repository Layout
- `src/process_community_workflow.py`: end-to-end workflow driver
- `src/h2k-hpxml/`: converter used to generate HPXML + run simulations (git submodule)
- `src/source-archetypes/`: Hot2000 `.H2K` archetype library (local/downloaded; not committed)
- `communities/<Community Name>/`: per-run working directory and outputs (generated locally; not committed)
- `csv/`: community requirements + weather mapping inputs

## Quick Start

```bash
# 1) Clone
git clone <YOUR_REPO_URL>
cd community-energy-orchestrator

# 1a) Initialize submodules (required for src/h2k-hpxml)
git submodule update --init --recursive

# (Alternative) clone with submodules:
# git clone --recurse-submodules <YOUR_REPO_URL>

# 2) Create + activate venv
python3 -m venv .venv
source .venv/bin/activate

# 3) Install orchestrator dependencies
pip install -r requirements.txt

# 4) Install converter package (required for HPXML/EnergyPlus runs)
pip install -e src/h2k-hpxml

# 4a) Provide the archetype library
# Ensure src/source-archetypes/ exists and contains .H2K files.

# 5) Run a community
python src/process_community_workflow.py "Old Crow"
```

For first-time setup on a new machine (OpenStudio/EnergyPlus dependencies), follow: [INSTALLATION.md](docs/INSTALLATION.md)

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

## Known Issues
- First-time converter setup (OpenStudio/EnergyPlus dependencies) can take a while depending on platform.
