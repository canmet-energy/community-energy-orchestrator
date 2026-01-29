
# Installation Guide

Complete setup instructions for running the community workflow end-to-end.

## Table of Contents
- [Requirements](#requirements)
- [Quick Start](#quick-start)
- [Detailed Setup](#detailed-setup)
- [Verification](#verification)
- [Troubleshooting](#troubleshooting)

## Requirements

### Core requirements
- Python 3.10+ (recommended)
- `pip`

### Simulation requirements
This project runs simulations via the converter in `src/h2k-hpxml/` (git submodule). That converter depends on OpenStudio/EnergyPlus tooling.

If you are setting up on a new machine, expect the first-time setup to take longer.

## Quick Start

```bash
# 1) Clone
git clone https://github.com/micael-gourde/community-energy-orchestrator.git
cd community-energy-orchestrator

# 1a) Initialize submodules (required for src/h2k-hpxml)
git submodule update --init --recursive

# (Alternative) You can clone with submodules in one step:
# git clone --recurse-submodules https://github.com/micael-gourde/community-energy-orchestrator.git

# 2) Create and activate a virtual environment
python3 -m venv .venv
source .venv/bin/activate

# 3) Install orchestrator dependencies
pip install -r requirements.txt

# 4) Install converter package (includes the h2k-hpxml CLI entrypoint)
pip install -e src/h2k-hpxml

# 5) Provide the archetype library (required)
# Ensure src/source-archetypes/ exists and contains the .H2K archetypes.

# 6) Run a community
python src/process_community_workflow.py "Old Crow"
```

Note: `communities/` is generated locally by the workflow and is not committed.

## Detailed Setup

### 1) Create and activate a virtual environment

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 2) Install Python dependencies

```bash
pip install -r requirements.txt
pip install -e src/h2k-hpxml
```

### 3) Provide the archetype library

This workflow expects a local Hot2000 archetype library at:

- `src/source-archetypes/`

This folder is intentionally treated as a local input (it is gitignored). Place/download the archetype library there before running any communities.

### 4) OpenStudio/EnergyPlus setup (if needed)
If your environment does not already have the simulation dependencies configured, the converter provides helper commands.

After installing the converter package, you can try:

```bash
os-setup --help
```

For full details, see the converter’s installation guide.

## Verification

### Confirm the CLI is installed

```bash
h2k-hpxml --help
```

### Dry run with a community

Choose one from [COMMUNITIES.md](COMMUNITIES.md):

```bash
python src/process_community_workflow.py "Old Crow"
```

## Troubleshooting

### “Command not found: h2k-hpxml”
Reinstall the converter into your active venv:

```bash
pip install -e src/h2k-hpxml
```

### “OpenStudio not found” / simulation errors
Follow the converter’s setup instructions.
