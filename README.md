# Community Energy Orchestrator

The Community Energy Orchestrator generates hourly energy profiles for northern and remote communities across Canada. It takes housing stock data from the census, assigns representative building archetypes, updates their weather files, runs EnergyPlus simulations, and aggregates the results into community-level energy breakdowns by fuel type.

For more on the research motivation and methodology, see the [Background](docs/BACKGROUND.md).

---

## Quick Start

```bash
process-community "Old Crow"
```

This runs the full workflow for a single community. Output files appear in `output/Old Crow/` when the run finishes.

> **First time?** You need to install dependencies before running. Pick a path below.

---

## Documentation

| Guide | Description |
|-------|-------------|
| [Background](docs/BACKGROUND.md) | What the tool does, why it exists, and how the workflow works |
| [Installation](docs/INSTALLATION.md) | Manual setup on Windows, Linux, or macOS |
| [Docker](docs/DOCKER.md) | Containerised setup with Docker or Docker Compose |
| [User Guide](docs/USER_GUIDE.md) | CLI, API, and frontend usage — plus output file reference |
| [Communities](docs/COMMUNITIES.md) | All 139 supported communities with metadata |
| [Development](docs/DEVELOPMENT.md) | Dev environment, project structure, testing, CI/CD |
| [Contributing](CONTRIBUTING.md) | How to submit changes |

### Choose Your Path

- **I want to install and run it locally** → [Installation Guide](docs/INSTALLATION.md)
- **I want to use Docker** → [Docker Guide](docs/DOCKER.md)
- **I already have it installed** → [User Guide](docs/USER_GUIDE.md)
- **I want to contribute code** → [Development Guide](docs/DEVELOPMENT.md) then [Contributing](CONTRIBUTING.md)

---

## Repository Layout

```
backend/
  app/main.py                            # FastAPI REST API
  workflow/
    process_community_workflow.py        # Main CLI workflow
    service.py                           # Public API wrapper for workflow
    config.py                            # Constants and environment variables
    ...                                  # Supporting modules
data/
  json/communities.json                  # Community definitions (139 entries)
  source-archetypes/                     # H2K archetype library (not in git)
frontend/                                # React + Vite web interface
tests/                                   # Unit and integration tests
docs/                                    # All documentation
output/                                  # Generated per-run (not in git)
```

---

## License

This project is licensed under the [GNU Affero General Public License v3.0 or later](LICENSE.txt) (AGPL-3.0+).

It is designed to interoperate with [btap_batch](https://github.com/canmet-energy/btap_batch), which is released under the same AGPL-3.0+ licence.

## Citation

If you use the Community Energy Orchestrator in your research, please cite:

```text
Natural Resources Canada
Community Energy Orchestrator
https://github.com/canmet-energy/community-energy-orchestrator
```
