
# Installation Guide

Complete setup instructions for running the community workflow end-to-end.

## Detailed Setup

This repo depends on the `h2k-hpxml` converter working on your machine.

Notes: 
- This orchestrator uses `pyproject.toml`

- The converter submodule declares support for Python 3.10–3.13.

- `communities/` is generated locally by the workflow and is not committed.

### Step 1) Clone the repo (with submodules)

`src/h2k-hpxml/` is a git submodule and must be initialized.

```bash
git clone --recurse-submodules https://github.com/micael-gourde/community-energy-orchestrator.git
cd community-energy-orchestrator
```

If you already cloned without submodules:

```bash
git submodule update --init --recursive
```

### Step 2) Create and activate a Python virtual environment

Linux/macOS:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

Windows (PowerShell):

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

### Step 3) Install orchestrator dependencies

```bash
pip install -e .
```

### Step 4) (Optional) Install the converter package in editable mode

On supported Python versions, the converter is installed automatically as a
dependency from the `src/h2k-hpxml/` submodule when you run Step 3.

Only do this step if you're developing the converter itself.

Linux/macOS:

```bash
pip install -e src/h2k-hpxml
```

Windows:

```powershell
pip install -e src\h2k-hpxml
```

Verification:

```bash
h2k-hpxml --help
os-setup --help
```

If `h2k-hpxml` is “command not found”, confirm your venv is active and re-run the install. On Windows, you may need to restart your terminal.

### Step 5) Install and verify OpenStudio/EnergyPlus dependencies

These steps are required for the converter to actually run simulations:

Linux/macOS:

```bash
os-setup --auto-install
os-setup --test-installation
```

If you hit permission errors on Linux, try:

```bash
sudo os-setup --auto-install
```

If `h2k-hpxml` is “command not found”, restart your terminal and confirm your venv is active.

Windows (PowerShell):

```powershell
os-setup --auto-install
os-setup --test-installation
```

If commands are still not found on Windows, try:

```powershell
os-setup --add-to-path
```

If `os-setup` is not found, re-check Step 4 (the converter package must be installed into your active environment).

Optional deeper verification:

Linux/macOS:

```bash
os-setup --test-comprehensive
```

Optional: verify the converter end-to-end without the orchestrator:

Linux/macOS:

```bash
h2k-demo
```

### Step 6) Provide the archetype library

This workflow expects a local Hot2000 archetype library at:

- `src/source-archetypes/`

This folder is intentionally treated as a local input (it is gitignored). Place/download the archetype library there before running any communities.

### Step 7) Run a community

Choose one from [Communities](COMMUNITIES.md):

```bash
python3 src/process_community_workflow.py "Old Crow"
```

Optional: run the API instead of the CLI workflow:

```bash
python3 -m uvicorn src.main:app --reload
```

Then open:

- http://localhost:8000/docs

If a run fails during conversion/simulation, start by re-running:

```bash
os-setup --test-installation
```

Next: once you're installed, jump straight to the usage and outputs overview in the [User Guide](USER_GUIDE.md).
