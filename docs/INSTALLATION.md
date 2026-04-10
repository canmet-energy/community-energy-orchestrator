
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
5. Place it in the `data/` directory of this repository

The final path should be: `data/source-archetypes/` containing subdirectories organized by archetype type (e.g., `pre-2002-single/`, `2002-2016-single/`), each with `.H2K` files.

**Verification:** Check that `data/source-archetypes/2002-2016-single/2002-2016-single_EX-0001.H2K` exists.

### Step 4) Build the Docker image

```bash
docker build -t community-energy-orchestrator .
```

This will:
- Install Python 3.10 and uv
- Install all dependencies (matching your uv.lock)
- Install OpenStudio/EnergyPlus automatically
- Set up the complete environment

### Step 5) Run the container

```bash
# Recommended: Start both API and frontend
docker compose up

# OR run the API only
docker run -p 8000:8000 community-energy-orchestrator
```

Then open:
- Frontend: http://localhost:5173
- API Swagger UI: http://localhost:8000/docs

**Docker vs Dev Container:** The Dockerfile creates a production-ready container for running the API. If you're developing in VS Code with the dev container (`.devcontainer/`), that's for development purposes and includes additional dev tools.

---

## Option 2: Manual Setup

## Detailed Setup

This repo depends on the `h2k-hpxml` converter working on your machine.

Notes: 
- This orchestrator uses `uv` for Python installation and dependency management — you do **not** need to install Python separately
- `uv` requires no admin rights and works on Windows, macOS, and Linux

- The converter library supports Python 3.10–3.12.

- `output/` is generated locally by the workflow and is not committed.

### Step 1) Clone the repo

```bash
git clone https://github.com/canmet-energy/community-energy-orchestrator.git
cd community-energy-orchestrator
```

### Step 2) Install uv

`uv` is a fast Python package manager that also installs Python for you — no admin rights needed.

Linux/macOS:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Windows (PowerShell):

```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

After installing, restart your terminal so `uv` is on your PATH.

### Step 3) Sync dependencies

This will automatically download the correct Python version (3.10–3.12) and install all dependencies in one step:

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

- `data/source-archetypes/`

This folder is intentionally treated as a local input.

#### Downloading the archetype library:

1. Go to https://github.com/canmet-energy/housing-archetypes.git
2. Navigate to `data/h2k_files/existing-stock`
3. Download the folder `retrofit-archetypes-for-diesel-reduction-modelling-in-remote-communities`
4. Rename the downloaded folder to `source-archetypes`
5. Place it in the `data/` directory of this repository

The final path should be: `data/source-archetypes/` containing subdirectories organized by archetype type (e.g., `pre-2002-single/`, `2002-2016-single/`), each with `.H2K` files.

### Step 7) Run a community

Choose one from [Communities](COMMUNITIES.md):

Linux/macOS:

```bash
# Using CLI command (recommended after uv sync)
process-community "Old Crow"

# Or using Python directly
python3 backend/workflow/process_community_workflow.py "Old Crow"
```

Windows (PowerShell):

```powershell
# Using CLI command (recommended after uv sync)
process-community "Old Crow"

# Or using Python directly
python backend\workflow\process_community_workflow.py "Old Crow"
```

Optional: run the API instead of the CLI workflow:

Linux/macOS:

```bash
python3 -m uvicorn app.main:app --host 0.0.0.0
```

Windows (PowerShell):

```powershell
python -m uvicorn app.main:app --host 0.0.0.0
```

Then open:

- http://localhost:8000/docs

### Step 7b) Run the frontend (optional)

The web frontend provides a visual interface for running communities and viewing results. It requires the API to be running (Step 7).

```bash
cd frontend
npm install
npm run dev
```

Then open http://localhost:5173

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
