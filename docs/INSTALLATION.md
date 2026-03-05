
# Installation Guide

Complete setup instructions for running the community workflow end-to-end.

## Installation Methods

Choose one of the following installation methods:

1. **Docker (Recommended for sharing)** - Containerized setup with all dependencies → [Docker Guide](DOCKER.md)
2. **Manual Setup** - Direct installation on your system with uv

---

## Option 1: Docker Installation

If you have Docker installed, this is the fastest way to get started.

### Step 1) Install Docker

If you don't have Docker, install it from https://docs.docker.com/get-docker/

### Step 2) Clone the repo

```bash
git clone https://github.com/canmet-energy/community-energy-orchestrator.git
cd community-energy-orchestrator
```

### Step 3) Download the archetype library

**⚠️ REQUIRED:** This directory is needed to process communities.

1. Go to https://github.com/canmet-energy/housing-archetypes.git
2. Navigate to `data/h2k_files/existing-stock`
3. Download the folder `retrofit-archetypes-for-diesel-reduction-modelling-in-remote-communities`
4. Rename the downloaded folder to `source-archetypes`
5. Place it in the `src/` directory of this repository

The final path should be: `src/source-archetypes/` containing `.H2K` files.

**Verification:** Check that `src/source-archetypes/2001-2015-single_EX-0001.H2K` exists.

### Step 4) Build the Docker image

```bash
docker build -t community-energy-orchestrator .
```

This will:
- Install Python 3.10 and uv package manager
- Install all dependencies (matching your uv.lock)
- Install OpenStudio/EnergyPlus automatically
- Set up the complete environment

### Step 5) Run the container

```bash
# Run the FastAPI server
docker run -p 8000:8000 community-energy-orchestrator
```

Then open http://localhost:8000/docs to access the API.

**Docker vs Dev Container:** The Dockerfile creates a production-ready container for running the API. If you're developing in VS Code with the dev container (`.devcontainer/`), that's for development purposes and includes additional dev tools.

---

## Option 2: Manual Setup

## Detailed Setup

This repo depends on the `h2k-hpxml` converter working on your machine.

Notes: 
- This orchestrator uses `pyproject.toml` and `uv` for dependency management

- The converter library supports Python 3.10–3.12.

- `communities/` is generated locally by the workflow and is not committed.

### Step 1) Clone the repo

```bash
git clone https://github.com/canmet-energy/community-energy-orchestrator.git
cd community-energy-orchestrator
```

### Step 2) Install uv (if not already installed)

```bash
pip install uv
```

Note: `uv` can also be installed via other methods (pipx, curl, etc.). See https://github.com/astral-sh/uv for alternatives.

### Step 3) Sync dependencies

This will create a virtual environment automatically and install all dependencies:

```bash
uv sync
```

**For contributors:** Use `uv sync --all-extras` to include testing and linting tools.

### Step 4) Activate the virtual environment

Linux/macOS:

```bash
source .venv/bin/activate
```

Windows (PowerShell):

```powershell
 .venv\Scripts\Activate.ps1
```

**Important for Windows PowerShell Users:**

If you'll be processing communities with French characters (Gamètì, Déline, François, etc.), you **must** configure UTF-8 encoding in PowerShell. Without this, you'll get encoding errors when the workflow tries to create directories and files.

```powershell
# Option 1 (Recommended): Add permanently to your PowerShell profile
notepad $PROFILE
# Add these two lines to the file:
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$env:PYTHONUTF8 = "1"
# Save, close, and restart PowerShell

# Option 2: Set temporarily for current session only
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$env:PYTHONUTF8 = "1"
```

If `$PROFILE` doesn't exist, create it first:
```powershell
New-Item -Path $PROFILE -Type File -Force
```

**Note:** Git Bash on Windows doesn't need this setup (it uses UTF-8 by default).

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

```bash
os-setup --test-comprehensive
```

Optional: verify the converter end-to-end without the orchestrator:

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

Linux/macOS:

```bash
# Using CLI command (recommended after uv sync)
process-community "Old Crow"

# Or using Python directly
python3 src/workflow/process_community_workflow.py "Old Crow"
```

Windows (PowerShell):

```powershell
# Using CLI command (recommended after uv sync)
process-community "Old Crow"

# Or using Python directly
python src\workflow\process_community_workflow.py "Old Crow"
```

Optional: run the API instead of the CLI workflow:

Linux/macOS:

```bash
python3 -m uvicorn src.app.main:app
```

Windows (PowerShell):

```powershell
python -m uvicorn src.app.main:app
```

Then open:

- http://localhost:8000/docs

> **Note:** This uses `src.app.main:app` because of the editable install. Docker environments use `app.main:app` instead.

If a run fails during conversion/simulation, start by re-running:

```bash
os-setup --test-installation
```

### Step 8) Run tests (optional)

To verify your installation is working correctly:

```bash
# Install test dependencies if you haven't already
uv sync --all-extras
source .venv/bin/activate  # or .venv\Scripts\Activate.ps1 on Windows

# Run all tests
pytest tests/

# Run with coverage (like CI does)
pytest tests/unit/ -m unit --cov=src/ --cov-report=term-missing
```

Next: once you're installed, jump straight to the usage and outputs overview in the [User Guide](USER_GUIDE.md).
