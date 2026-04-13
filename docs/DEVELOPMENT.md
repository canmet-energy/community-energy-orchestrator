# Development Guide

This guide covers how to set up a development environment, run tests, and use the project tooling. For submitting changes, see [Contributing](../CONTRIBUTING.md).

---

## Table of Contents

- [Prerequisites](#prerequisites)
- [Dev Environment Setup](#dev-environment-setup)
- [Dev Container (VS Code)](#dev-container-vs-code)
- [Frontend Development](#frontend-development)
- [Project Structure](#project-structure)
- [Code Style](#code-style)
- [Testing](#testing)
- [Make Commands](#make-commands)
- [CI/CD Pipeline](#cicd-pipeline)

---

## Prerequisites

- Python 3.10–3.12
- [uv](https://github.com/astral-sh/uv) package manager
- Node.js 18+ (for frontend work)
- Git

> To actually **run** community workflows (not just develop and test), you also need OpenStudio, EnergyPlus, and the archetype library. See the [Installation Guide](INSTALLATION.md) for those steps.

---

## Dev Environment Setup

```bash
# 1. Fork and clone the repo
git clone https://github.com/YOUR_USERNAME/community-energy-orchestrator.git
cd community-energy-orchestrator

# 2. Install uv (if not already installed)
pip install uv

# 3. Install all dependencies including dev and test tools
uv sync --all-extras

# 4. Activate the virtual environment
source .venv/bin/activate        # Linux/macOS
# .venv\Scripts\Activate.ps1    # Windows PowerShell
```

This installs the project in editable mode with all dev dependencies (black, isort, pylint, mypy, pytest, safety, bandit).

---

## Dev Container (VS Code)

The repo includes a `.devcontainer/` configuration for VS Code. Opening the project in a dev container gives you a fully configured environment with:

- Python 3.10 with all dependencies pre-installed
- OpenStudio and EnergyPlus installed via `os-setup`
- Node.js 22 with frontend dependencies
- Virtual environment auto-activated in every terminal

To use it:

1. Install the [Dev Containers](https://marketplace.visualstudio.com/items?itemName=ms-vscode-remote.remote-containers) extension in VS Code.
2. Open the project folder.
3. When prompted, click **Reopen in Container** (or use the command palette: `Dev Containers: Reopen in Container`).

The `post-create.sh` script runs automatically to install Python/Node dependencies and OpenStudio. No manual setup needed.

---

## Frontend Development

The frontend is a React + Vite app in the `frontend/` directory:

```bash
cd frontend
npm install
npm run dev      # Development server at http://localhost:5173
npm run build    # Production build
npm run lint     # ESLint
```

The frontend expects the API to be running at `http://localhost:8000`. Start the API in a separate terminal:

```bash
python -m uvicorn app.main:app --host 0.0.0.0
```

---

## Project Structure

```
backend/
  app/
    main.py                              # FastAPI REST API
  workflow/
    process_community_workflow.py        # Main CLI workflow
    service.py                           # Public API wrapper for workflow
    calculate_community_analysis.py      # Aggregates timeseries → community totals
    change_weather_location_regex.py     # Updates weather reference in .H2K files
    requirements.py                      # Reads community data from communities.json
    outputs.py                           # Output file management (paths, ZIP creation)
    config.py                            # Constants and environment variable readers
    paths.py                             # Shared paths (output_dir, json_dir, etc.)
    debug_outputs.py                     # Output validation and debug logs
tests/
  conftest.py                            # Shared fixtures
  unit/                                  # Unit tests (fast, no external deps)
  integration/                           # Integration tests (may need full environment)
frontend/                                # React + Vite frontend
data/
  json/                                  # Community requirements and configuration
  source-archetypes/                     # H2K archetype library (not in git)
tools/
  data-scrubbing/                        # Data preparation scripts
output/                                  # Generated per-run (not in git)
docs/                                    # User-facing documentation
```

---

## Code Style

The project uses automated formatting and linting, all configured in `pyproject.toml`:

| Tool | Purpose | Config |
|------|---------|--------|
| [black](https://github.com/psf/black) | Code formatting | Line length 100 |
| [isort](https://pycqa.github.io/isort/) | Import sorting | Black-compatible profile |
| [pylint](https://pylint.readthedocs.io/) | Static analysis | `missing-docstring` and `too-few-public-methods` disabled |
| [mypy](https://mypy.readthedocs.io/) | Type checking | Python 3.10 target, strict optional |

Auto-format your code:

```bash
make format
```

Check formatting without modifying files:

```bash
make lint
```

---

## Testing

### Running Tests

```bash
# All tests with coverage
make test

# Unit tests only
uv run pytest tests/unit/ -m unit

# Integration tests only
uv run pytest tests/integration/ -m integration

# A specific test file
uv run pytest tests/unit/test_outputs.py -v

# Tests matching a name pattern
uv run pytest -k "test_calculate"
```

### Test Structure

Tests use [pytest](https://docs.pytest.org/) with these conventions:

- **Unit tests** (`tests/unit/`) — Fast, isolated. Use `monkeypatch` and `tmp_path`. Marked with `@pytest.mark.unit`.
- **Integration tests** (`tests/integration/`) — May depend on JSON config or real directories. Marked with `@pytest.mark.integration`.
- **Fixtures** — Shared fixtures live in `tests/conftest.py`. Test-specific fixtures go in the test file.

Test files follow the pattern `test_<module_name>.py`, mirroring the source module they test.

### Writing Tests

- One behaviour per test.
- Use `monkeypatch` to mock `output_dir()` and other path functions so tests don't depend on real data.
- Use `tmp_path` (pytest built-in) for tests that create files.
- Mark every test with `@pytest.mark.unit` or `@pytest.mark.integration`.

Example:

```python
import pytest

pytestmark = pytest.mark.unit


def test_my_function(tmp_path, monkeypatch):
    monkeypatch.setattr("workflow.paths.output_dir", lambda: tmp_path)
    # ... test logic
```

---

## Make Commands

> **Windows PowerShell:** `make` is not available natively. Use the Dev Container, WSL, or Git Bash instead. Alternatively, run the underlying commands directly (e.g., `uv run black --check backend/ tests/`) — see the [Makefile](../Makefile) for the full list.

| Command | When to Use | Behaviour |
|---------|-------------|-----------|
| `make format` | Before committing | Auto-format code (black + isort) |
| `make dev-check` | During development | Run all checks, show all issues (does not stop on failure) |
| `make fix-all` | Before pushing | Auto-format then strict checks (stops on first failure) |
| `make check-all` | CI/CD simulation | Strict checks without formatting (stops on first failure) |
| `make lint` | Check formatting | Verify code style without modifying files |
| `make test` | Quick test run | Run all tests with coverage |
| `make clean` | Housekeeping | Remove cache and generated files |
| `make docker-disk` | Check disk usage | Show Docker disk usage |
| `make docker-clean` | Free disk space | Remove dangling images, stopped containers, build cache |
| `make docker-reset` | Full cleanup | Full Docker system prune (removes all unused resources) |

### Recommended Workflow

1. Write your code.
2. Run `make dev-check` to see all issues at once.
3. Fix issues iteratively.
4. Run `make fix-all` before pushing — this must pass cleanly.

### Troubleshooting Failed Checks

- **Formatting errors** — `make format` auto-fixes most issues.
- **Pylint warnings** — Review the specific warnings. Some are informational (e.g. "too many local variables").
- **Type errors (mypy)** — Add type hints or use `# type: ignore` sparingly with justification.
- **Test failures** — Run the failing test in isolation: `uv run pytest path/to/test.py -v`

---

## CI/CD Pipeline

Pull requests trigger GitHub Actions CI (`.github/workflows/ci.yml`) which runs four jobs:

| Job | What It Does |
|-----|-------------|
| **Lint** | black, isort, pylint, mypy |
| **Test** | pytest on Python 3.10, 3.11, and 3.12 with coverage |
| **Docker Build** | Builds the image and verifies the container starts |
| **Security** | safety (dependency vulnerabilities) and bandit (code security scan) |

CI triggers on pushes and pull requests to the `main`, `dev`, and `review` branches.

Pylint, mypy, isort, integration tests, safety, and bandit are set to `continue-on-error` in CI, so they won't block a PR — but you should still aim to fix any warnings they report.

The same checks that CI runs can be reproduced locally with:

```bash
make check-all    # Lint + test (no auto-formatting, matches CI behaviour)
```
