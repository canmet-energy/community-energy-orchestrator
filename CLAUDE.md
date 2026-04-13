# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with this repository.
Keep it under 150 lines — route to `docs/` for detail, don't duplicate it here.

## Project Overview

The **Community Energy Orchestrator** is a Canadian government tool (NRCan) that generates hourly energy profiles for northern and remote communities. It takes census housing stock data, assigns representative building archetypes (HOT2000/H2K files), runs EnergyPlus simulations via h2k-hpxml, and aggregates results into community-level energy breakdowns by fuel type.

- **Status**: Alpha (v0.1.0) | **Python**: 3.10–3.12 | **License**: AGPL-3.0+
- **H2K files** are HOT2000 building energy models (XML-based, Canadian housing standard)
- **Key dependency**: [h2k-hpxml](https://github.com/canmet-energy/h2k-hpxml) — converts H2K → HPXML → EnergyPlus (brings OpenStudio + EnergyPlus)
- **Source archetypes** (`data/source-archetypes/`) are H2K template files, too large for git — obtain from team or internal share. **Not needed for unit tests** (fully mocked), but required for integration tests and real runs.
- **Three interfaces**: CLI (`process-community`), REST API (`energy-orchestrator`), React frontend — all run the same workflow

## Setup

```bash
uv sync                        # Install all deps from lockfile (preferred)
uv pip install -e ".[dev]"    # Alternative: editable install with dev extras
```

Both install the project; `uv sync` uses the lockfile for reproducibility, `uv pip install -e ".[dev]"` resolves from pyproject.toml. Use one or the other. For full environment setup (OpenStudio, EnergyPlus, h2k-hpxml `os-setup`), see `docs/INSTALLATION.md`. Frontend setup: `cd frontend && npm install` (see `frontend/README.md`).

**Windows note**: `Makefile` targets use bash syntax. On Windows, run commands directly or use WSL/Git Bash. See `docs/INSTALLATION.md` for platform-specific guidance.

## Workflow Pipeline

`process_community_workflow.py` → `main()` runs these steps in order:
1. **Validate** community name against `data/json/communities.json` (139 communities)
2. **Copy archetypes** — selects H2K files from `data/source-archetypes/` (N+20% extra per housing type for simulation failure buffer, seeded random)
3. **Patch weather** — regex-updates weather location codes inside each H2K file
4. **Simulate** — calls `h2k_hpxml.api.run_full_workflow()` (H2K → HPXML → EnergyPlus, parallel)
5. **Collect timeseries** — gathers hourly CSV results; duplicates files if some simulations failed to meet required count
6. **Aggregate** — sums 8760-row timeseries into community totals by fuel type (`calculate_community_analysis.py`)
7. **Debug validate** — `debug_outputs.py` runs sanity checks on timeseries files
8. **Cleanup** — removes intermediate archetype/simulation files

`service.py` is a thin public wrapper so the API doesn't import workflow internals directly.

## Essential Commands

```bash
# Run
process-community "Old Crow"              # CLI: single community
energy-orchestrator                       # Start FastAPI server (port 8000)

# Test
uv run pytest tests/unit/ -m unit --cov=backend/ --cov-report=term-missing
uv run pytest tests/integration/ -m integration       # Needs archetypes + EnergyPlus
uv run pytest tests/unit/test_config.py -m unit -v    # Single test file

# Makefile shortcuts (Linux/macOS/WSL)
make fix-all                              # Format + static analysis + test (before push)
make dev-check                            # All checks, continues on errors (shows summary)

# Docker
docker compose up --build                 # API on :8000, frontend on :5173
```

## API Endpoints

Defined in `backend/app/main.py`. Single-run-at-a-time enforced via in-process lock (threading); keep workers=1.

`GET /health` · `GET /communities` · `POST /runs` · `GET /runs` · `GET /runs/current` · `GET /runs/{run_id}` · `GET /runs/{run_id}/analysis-md` · `GET /runs/{run_id}/analysis-data` · `GET /runs/{run_id}/daily-load-data` · `GET /runs/{run_id}/peak-day-hourly-data` · `GET /runs/{run_id}/download/community-total` · `GET /runs/{run_id}/download/dwelling-timeseries`

See `docs/USER_GUIDE.md` for request/response details and frontend usage.

## Environment Variables

| Variable | Default | Purpose |
|----------|---------|---------|
| `MAX_PARALLEL_WORKERS` | auto (80% CPUs) | Worker count for parallel sim/copy |
| `ANALYSIS_RANDOM_SEED` | None | Deterministic analysis runs |
| `ARCHETYPE_SELECTION_SEED` | None | Deterministic archetype selection |
| `APP_ROOT` | auto-detected | Override project root path |
| `ALLOWED_ORIGINS` | — | CORS origins for API |

## Architecture

```
backend/
  app/main.py                    # FastAPI REST API (endpoints + run state)
  workflow/
    process_community_workflow.py # Main workflow (see pipeline above)
    service.py                   # Public API wrapper (thin, delegates to main)
    config.py                    # Constants, ENERGY_CATEGORIES, ARCHETYPE_TYPE_PATTERNS, env vars
    calculate_community_analysis.py  # Aggregation: timeseries → community totals
    outputs.py                   # Output file generation (CSV, markdown, zip)
    debug_outputs.py             # Timeseries validation/sanity checks
    paths.py                     # Path resolution (project_root, output_dir, etc.)
    requirements.py              # Community data loading from communities.json
    change_weather_location_regex.py # H2K weather file patching
frontend/                        # React + Vite (visualizes analysis results)
data/json/communities.json       # Community definitions (province, HDD, weather, housing counts)
data/source-archetypes/          # H2K archetype library (not in git)
output/{community}/              # Generated: analysis/, timeseries/ (not in git)
logs/                            # Runtime logs (not in git)
```

## Key Patterns

- **Energy categories** are data-driven via `ENERGY_CATEGORIES` in `config.py` — dict keyed by category name (e.g. `"heating"`), each with `label`, optional `load`, `sources` (fuel breakdown with CSV column mappings and unit), and `total_col`. Adding a category only requires a new dict entry; all downstream logic adapts.
- **Units**: GJ primary. Conversions in `config.py`: `KBTU_TO_GJ`, `KWH_TO_GJ`, `GJ_TO_KW`.
- **Test markers**: `@pytest.mark.unit` (mocked, no external deps), `@pytest.mark.integration` (needs archetypes + EnergyPlus), `@pytest.mark.slow`, `@pytest.mark.stress`.
- **Archetype patterns**: 12 types (3 eras × 4 dwelling types) defined in `ARCHETYPE_TYPE_PATTERNS` in `config.py`. Folder names follow `{era}-{dwelling_type}` convention (e.g. `pre-2002-single`).

## Code Style

- **black** (line length 100) | **isort** (black profile) | **pylint** | **mypy** (relaxed: `check_untyped_defs = true`)
- Do NOT delete `__init__.py` files — required for package imports
- All tool config lives in `pyproject.toml`

## MANDATORY

- Run `make fix-all` before committing. **Also** run `uv run mypy tests/ backend/` — `fix-all` only type-checks `backend/`, not `tests/`.
- Branch strategy: `main` for PRs, feature branches for dev work.

## Documentation Index

Route to these for detail — don't duplicate their content here:

| File | Content |
|------|---------|
| `docs/BACKGROUND.md` | Research motivation, methodology, workflow explanation |
| `docs/INSTALLATION.md` | Full setup: Python, uv, OpenStudio, EnergyPlus, h2k-hpxml, Windows/Linux/macOS |
| `docs/DOCKER.md` | Docker and Docker Compose setup |
| `docs/USER_GUIDE.md` | CLI, API, frontend usage, output file formats |
| `docs/COMMUNITIES.md` | All 139 supported communities with metadata |
| `docs/DEVELOPMENT.md` | Dev environment, project structure, testing, CI/CD |
| `CONTRIBUTING.md` | How to submit changes |
| `pyproject.toml` | All tool config (pytest, mypy, black, pylint, coverage) |
| `Makefile` | All development shortcuts (`make help` for list) |
