
# Installation Guide

Complete setup instructions for running the community workflow end-to-end.

## Detailed Setup

This repo depends on the `h2k-hpxml` converter working on your machine.

Notes: 
- This orchestrator uses `pyproject.toml` and `uv` for dependency management

- The converter library supports Python 3.10–3.13.

- `communities/` is generated locally by the workflow and is not committed.

### Step 1) Clone the repo

```bash
git clone https://github.com/canmet-energy/community-energy-orchestrator.git
cd community-energy-orchestrator
```

### Step 2) Install uv (if not already installed)

Linux/macOS:

```bash
pip install uv
```

Windows (PowerShell):

```powershell
pip install uv
```

Note: `uv` can also be installed via other methods (pipx, curl, etc.). See https://github.com/astral-sh/uv for alternatives.

### Step 3) Sync dependencies

This will create a virtual environment automatically and install all dependencies:

```bash
uv sync
```

### Step 4) Activate the virtual environment

Linux/macOS:

```bash
source .venv/bin/activate
```

Windows (PowerShell):

```powershell
 .venv\Scripts\Activate.ps1
```

Verification:

```bash
h2k-hpxml --help
os-setup --help
```

If commands are "command not found", confirm your venv is active. On Windows, you may need to restart your terminal.

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


Windows (PowerShell):

```powershell
os-setup --auto-install
os-setup --test-installation
```

If commands are still not found on Windows, try:

```powershell
os-setup --add-to-path
```

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

This folder is intentionally treated as a local input.

#### Downloading the archetype library:

1. Go to https://github.com/canmet-energy/housing-archetypes.git
2. Navigate to `data/h2k_files/existing-stock`
3. Download the folder `retrofit-archetypes-for-diesel-reduction-modelling-in-remote-communities`
4. Rename the downloaded folder to `source-archetypes`
5. Place it in the `src/` directory of this repository

The final path should be: `src/source-archetypes/` containing `.H2K` files.

### Step 7) Run a community

Choose one from [Communities](COMMUNITIES.md):

```bash
python3 src/process_community_workflow.py "Old Crow"
```

Optional: run the API instead of the CLI workflow:

```bash
python3 -m uvicorn src.main:app
```

Then open:

- http://localhost:8000/docs

If a run fails during conversion/simulation, start by re-running:

```bash
os-setup --test-installation
```

Next: once you're installed, jump straight to the usage and outputs overview in the [User Guide](USER_GUIDE.md).
