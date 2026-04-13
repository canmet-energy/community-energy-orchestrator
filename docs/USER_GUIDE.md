
# User Guide

This guide covers how to **use** the Community Energy Orchestrator once it is installed. If you still need to set up the tool, see one of:

- [Installation Guide](INSTALLATION.md) — manual setup (recommended for development)
- [Docker Guide](DOCKER.md) — containerised setup

For a list of all 139 supported communities, see the [Communities Reference](COMMUNITIES.md).

---

## Table of Contents

- [Quick Start](#quick-start)
- [Using the CLI](#using-the-cli)
- [Using the API](#using-the-api)
- [Using the Web Frontend](#using-the-web-frontend)
- [Understanding Outputs](#understanding-outputs)
- [Environment Variables](#environment-variables)
- [Troubleshooting](#troubleshooting)

---

## Quick Start

The fastest way to process a community and see results:

```bash
process-community "Old Crow"
```

This runs the full workflow: archetype selection → weather update → energy simulation → aggregation. Output files appear in `output/Old Crow/` when the run finishes.

> **Windows PowerShell users:** If community names with French characters (e.g. Gamètì, Déline) cause encoding errors, see [Installation Guide — Troubleshooting](INSTALLATION.md#windows-encoding-errors).

---

## Using the CLI

The CLI is the simplest way to process a single community locally.

### Running a Workflow

```bash
process-community "<Community Name>"
```

For example:

```bash
process-community "Rankin Inlet"
```

- Community names **must be quoted** if they contain spaces or special characters.
- The name must match an entry in `data/json/communities.json` (case-insensitive). Accents must be correct (e.g. `"Gamètì"` not `"Gametì"`).
- Each run **deletes and recreates** the `output/<Community Name>/` directory, so previous results for that community are replaced.

### Help

```bash
process-community --help
```

### Running Directly with Python

If you prefer not to use the installed entry point, you can invoke the module directly:

**Linux / macOS:**

```bash
python3 backend/workflow/process_community_workflow.py "Old Crow"
```

**Windows (PowerShell):**

```powershell
python backend\workflow\process_community_workflow.py "Old Crow"
```

---

## Using the API

The REST API lets you start workflow runs over HTTP and poll for results. It is also required for the web frontend.

### Starting the API Server

**Linux / macOS:**

```bash
python3 -m uvicorn app.main:app --host 0.0.0.0
```

**Windows (PowerShell):**

```powershell
python -m uvicorn app.main:app --host 0.0.0.0
```

The server starts on port **8000** by default. Stop it with `Ctrl+C`.

> If you are using Docker, the API server starts automatically — see the [Docker Guide](DOCKER.md).

### Interactive API Docs

Once the server is running, open the auto-generated Swagger UI:

- **http://localhost:8000/docs**

You can try out every endpoint directly from the browser.

### Key Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/health` | Server health check |
| `GET` | `/communities` | List all available communities with metadata |
| `POST` | `/runs` | Start a new workflow run |
| `GET` | `/runs` | List all runs (current session) |
| `GET` | `/runs/current` | Get the currently active run |
| `GET` | `/runs/{run_id}` | Get status of a specific run |
| `GET` | `/runs/{run_id}/analysis-data` | Aggregated analysis results (JSON) |
| `GET` | `/runs/{run_id}/daily-load-data` | Daily energy load profile (JSON) |
| `GET` | `/runs/{run_id}/peak-day-hourly-data` | Hourly profile for the peak demand day (JSON) |
| `GET` | `/runs/{run_id}/download/community-total` | Download the community total CSV |
| `GET` | `/runs/{run_id}/download/dwelling-timeseries` | Download all per-dwelling timeseries as a ZIP |
| `GET` | `/runs/{run_id}/download/analysis-md` | Download the analysis summary (Markdown) |

### Starting a Run via the API

Send a POST request with the community name:

```bash
curl -X POST http://localhost:8000/runs \
  -H "Content-Type: application/json" \
  -d '{"community_name": "Old Crow"}'
```

The response includes a `run_id`. Poll `GET /runs/{run_id}` until the `status` field changes to `completed` or `failed`.

### Important Notes

- **One run at a time.** The API enforces a single active run per server process. Submitting a second run while one is in progress returns an error.
- **In-memory state.** Run history is stored in memory. Restarting the server clears all run records (output files on disk are not affected).

---

## Using the Web Frontend

The web frontend provides a visual interface for running workflows and exploring results with interactive charts.

### Starting the Frontend

If you installed with **Docker** ([Docker Guide](DOCKER.md)):

```bash
docker-compose up
```

This starts both the API (port 8000) and the frontend (port 5173) together.

If you installed **locally** ([Installation Guide](INSTALLATION.md)):

You need two terminal sessions — one for the API and one for the frontend.

Terminal 1 — start the API:

```bash
python -m uvicorn app.main:app --host 0.0.0.0
```

Terminal 2 — start the frontend (requires Node.js 18+):

```bash
cd frontend
npm install
npm run dev
```

Then open **http://localhost:5173** in your browser.

### What the Frontend Shows

1. **Community search** — Search and select from the 139 available communities. Before running a workflow, you can see the community overview: province/territory, population, heating degree-days,  total houses.
2. **Run a workflow** — Click to start a run and watch its progress in real time.
3. **Results dashboard** — Once a run completes, the frontend displays:
   - **Energy breakdown** — Pie chart of energy by fuel source (propane, oil, electricity, natural gas, wood).
   - **Daily energy profile** — Line chart showing average daily energy and peak daily power across the year.
   - **Peak day hourly profile** — Hourly load on the day with the highest demand.
   - Toggle between **Heating** and **Total** energy categories.
4. **Downloads** — Download the community total CSV, per-dwelling timeseries (ZIP), or the analysis summary (Markdown).
5. **Run history** — Access results from previous runs in the current session (up to 5).
6. **Dark mode** — Toggle between light and dark themes.

---

## Understanding Outputs

After a successful run, the output directory for the community contains:

```
output/<Community Name>/
├── timeseries/               # Per-dwelling hourly results
│   └── *-results_timeseries.csv
└── analysis/                 # Aggregated community results
    ├── <Community>-community_total.csv   # Hourly totals (8760 rows)
    ├── <Community>_analysis.json         # Summary statistics (JSON)
    ├── <Community>_analysis.md           # Human-readable summary
    └── output_debug.log                  # Validation and debug info
```

### Key Output Files

**Community total CSV** (`analysis/<Community>-community_total.csv`)

The main result file. Contains 8,760 rows (one per hour of the year) with columns for heating load, and energy consumption by fuel type (propane, oil, electricity, natural gas, wood) — all in gigajoules (GJ).

**Per-dwelling timeseries** (`timeseries/*-results_timeseries.csv`)

Individual hourly simulation results for each dwelling archetype. These are the raw EnergyPlus outputs converted from the H2K models.

### Logs

- `logs/archetype_copy_debug.log` — Records which housing requirements were read from `communities.json` and how many archetypes were matched and copied for each type.

---

## Environment Variables

These optional variables control workflow behaviour:

| Variable | Default | Description |
|----------|---------|-------------|
| `MAX_PARALLEL_WORKERS` | Auto-detected from CPU count | Number of parallel simulation workers |
| `ANALYSIS_RANDOM_SEED` | None (random) | Seed for reproducible analysis randomisation |
| `ARCHETYPE_SELECTION_SEED` | None (random) | Seed for reproducible archetype selection |

Set them before running a command:

```bash
MAX_PARALLEL_WORKERS=4 process-community "Old Crow"
```

Or in PowerShell:

```powershell
$env:MAX_PARALLEL_WORKERS = "4"
process-community "Old Crow"
```

---

## Troubleshooting

### Converter or Simulation Errors

If you see errors about `h2k-hpxml`, OpenStudio, or EnergyPlus:

1. Confirm the tools are installed: `os-setup --test-installation`
2. Confirm the archetype library exists: check that `data/source-archetypes/` is populated (see [Installation Guide — Step 6](INSTALLATION.md#step-6-download-the-archetype-library)).
3. Check the debug log at `output/<Community Name>/analysis/output_debug.log` for details.

### Community Name Not Found

- The name must match an entry in `data/json/communities.json`.
- Matching is case-insensitive, but accents must be correct (e.g. `"gamètì"` works, `"gametì"` does not).
- Use `process-community --help` or browse the [Communities Reference](COMMUNITIES.md) for exact names.

### Windows PowerShell Encoding Errors

If communities with French characters (Gamètì, Déline, François) fail with encoding errors, see [Installation Guide — Troubleshooting](INSTALLATION.md#windows-encoding-errors) for the fix.

### Still not working?

Try running the community again. Some failures are transient and resolve on a retry.
