
# Installation Guide

Setup instructions for installing the Community Energy Orchestrator directly on your machine.

> **Prefer Docker?** If you'd rather run everything in a container without installing dependencies locally, see the [Docker Guide](DOCKER.md) instead.

## Prerequisites

- **Git** — to clone the repository
- **uv** — a fast Python package manager that also installs Python for you. No admin rights needed. You do **not** need to install Python separately.

## Step 1: Clone the Repository

```bash
git clone https://github.com/canmet-energy/community-energy-orchestrator.git
cd community-energy-orchestrator
```

## Step 2: Install uv

Linux/macOS:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Windows (PowerShell):

```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

After installing, restart your terminal so `uv` is on your PATH.

## Step 3: Install Dependencies

This will automatically download the correct Python version (3.10–3.12) and install all dependencies:

```bash
uv sync
```

> **For contributors:** Use `uv sync --all-extras` to include development and testing tools. See the [Development Guide](DEVELOPMENT.md) for details.

## Step 4: Activate the Virtual Environment

Linux/macOS:

```bash
source .venv/bin/activate
```

Windows (PowerShell):

```powershell
.venv\Scripts\Activate.ps1
```

## Step 5: Install OpenStudio and EnergyPlus

The simulation engine requires OpenStudio and EnergyPlus. The `os-setup` command (provided by the h2k-hpxml dependency) handles installation automatically.

```bash
os-setup --auto-install
os-setup --test-installation
```

If you get permission errors on Linux:

```bash
sudo os-setup --auto-install
```

If `os-setup` is not found on Windows, try:

```powershell
os-setup --add-to-path
```

## Step 6: Download the Archetype Library

The workflow requires a local library of Hot2000 archetype files. This library is maintained separately and must be downloaded manually.

1. Go to the [housing-archetypes](https://github.com/canmet-energy/housing-archetypes) repository
2. Navigate to `data/h2k_files/existing-stock`
3. Download the folder: `retrofit-archetypes-for-diesel-reduction-modelling-in-remote-communities`
4. Rename the downloaded folder to `source-archetypes`
5. Place it in the `data/` directory of this repository

Your directory structure should look like:

```
data/
  source-archetypes/
    pre-2002-single/
      pre-2002-single_EX-0001.H2K
      ...
    2002-2016-single/
    post-2016-single/
    ...
```

**Verification:** Confirm that `data/source-archetypes/2002-2016-single/2002-2016-single_EX-0001.H2K` exists.

## Step 7: Verify the Installation

Run a small community to confirm everything works:

```bash
process-community "Norman's Bay"
```

If the workflow completes, your installation is working. See the [User Guide](USER_GUIDE.md) to learn about all the ways to use the tool (CLI, API, frontend) and understand the outputs.

## Troubleshooting

### "command not found: process-community" or "command not found: os-setup"

Make sure your virtual environment is active. On Windows, you may need to restart your terminal after activating the venv.

### Simulation failures

If a run fails during conversion or simulation:

```bash
os-setup --test-installation
```

This will verify that OpenStudio and EnergyPlus are correctly installed and accessible.

### Windows encoding errors

If communities with special characters (Gamètì, Déline, François) fail with encoding errors, configure UTF-8 encoding in PowerShell:

**Permanent fix (recommended):**

```powershell
# Open your PowerShell profile (create it if it doesn't exist)
if (!(Test-Path -Path $PROFILE)) { New-Item -Path $PROFILE -Type File -Force }
notepad $PROFILE
```

Add these two lines to the file, save, and restart PowerShell:

```powershell
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$env:PYTHONUTF8 = "1"
```

**Temporary fix (current session only):**

```powershell
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$env:PYTHONUTF8 = "1"
```

> **Alternative:** Git Bash on Windows uses UTF-8 by default and does not need this setup.

## Next Steps

- [User Guide](USER_GUIDE.md) — Learn how to use the CLI, API, and frontend
- [Docker Guide](DOCKER.md) — Run everything in a container instead
- [Background](BACKGROUND.md) — Understand what the tool does and how it works
