# Contributing

Thank you for your interest in contributing to the Community Energy Orchestrator! This guide covers everything you need to develop, test, and submit changes.

## Getting Started

### Prerequisites

- Python 3.10–3.12
- [uv](https://github.com/astral-sh/uv) package manager
- Node.js 18+ (for frontend work)
- Git

### Setup

```bash
# 1. Fork and clone the repo
git clone https://github.com/YOUR_USERNAME/community-energy-orchestrator.git
cd community-energy-orchestrator

# 2. Install uv (if not already installed)
pip install uv

# 3. Install all dependencies (including dev/test tools)
uv sync --all-extras

# 4. Activate the virtual environment
source .venv/bin/activate        # Linux/macOS
# .venv\Scripts\Activate.ps1    # Windows PowerShell
```

> **Note:** For full environment setup including OpenStudio/EnergyPlus and the archetype library (needed to actually run communities), see the [Installation Guide](docs/INSTALLATION.md).

### Dev Container

If you use VS Code, the repo includes a `.devcontainer/` configuration. Opening the project in a dev container will automatically build the Docker image and give you a fully configured environment with Python, Node.js, and all dependencies pre-installed. No manual setup needed.

### Frontend Setup

The frontend is a React + Vite app in the `frontend/` directory:

```bash
cd frontend
npm install
npm run dev      # Development server at http://localhost:5173
npm run build    # Production build
npm run lint     # ESLint
```

The frontend expects the API to be running at `http://localhost:8000`. Start the API with:

```bash
python3 -m uvicorn src.app.main:app --host 0.0.0.0
```

## Project Structure

```
src/
  app/
    main.py                              # FastAPI REST API
  workflow/
    process_community_workflow.py        # Main CLI workflow driver
    service.py                           # Public API for workflow operations
    calculate_community_analysis.py      # Aggregates timeseries into community outputs
    change_weather_location_regex.py     # Updates weather reference in .H2K files
    requirements.py                      # Reads community requirements from CSV
    outputs.py                           # Output file management (paths, ZIP creation)
    config.py                            # Environment-based configuration
    core.py                              # Shared paths (communities_dir, csv_dir, etc.)
    debug_outputs.py                     # Output validation and debug logs
tests/
  conftest.py                            # Shared fixtures
  unit/                                  # Unit tests (fast, no external deps)
  integration/                           # Integration tests (may need full environment)
frontend/                                # React + Vite frontend
csv/                                     # Community requirements and weather mapping data
communities/                             # Generated per-run (gitignored)
docs/                                    # User-facing documentation
```

## Code Style

The project uses automated formatting and linting tools configured in `pyproject.toml`:

- **[black](https://github.com/psf/black)** — Code formatting (line length: 100)
- **[isort](https://pycqa.github.io/isort/)** — Import sorting (black-compatible profile)
- **[pylint](https://pylint.readthedocs.io/)** — Static analysis
- **[mypy](https://mypy.readthedocs.io/)** — Type checking

To auto-format your code:

```bash
make format
```

To check formatting without modifying files:

```bash
make lint
```

## Testing

### Running Tests

```bash
# Run all unit tests with coverage
make test

# Or run specific test files
uv run pytest tests/unit/test_outputs.py -v

# Run only unit tests
uv run pytest tests/unit/ -m unit

# Run only integration tests
uv run pytest tests/integration/ -m integration
```

### Test Structure

Tests use [pytest](https://docs.pytest.org/) with the following conventions:

- **Unit tests** (`tests/unit/`): Fast, isolated tests. Use `monkeypatch` and `tmp_path` to avoid filesystem dependencies. Marked with `@pytest.mark.unit`.
- **Integration tests** (`tests/integration/`): May depend on CSV data or real directory structures. Marked with `@pytest.mark.integration`.
- **Fixtures**: Shared fixtures live in `tests/conftest.py`. Test-specific fixtures go in the test file itself.

Test files follow the pattern `test_<module_name>.py`, mirroring the source module they test.

### Writing Tests

- Keep tests focused — one behavior per test.
- Use `monkeypatch` to mock `communities_dir()` and other path functions so tests don't depend on real data.
- Use `tmp_path` (pytest built-in) for tests that create files.
- Mark tests with `@pytest.mark.unit` or `@pytest.mark.integration`.

Example:

```python
import pytest

pytestmark = pytest.mark.unit


def test_my_function(tmp_path, monkeypatch):
    monkeypatch.setattr("workflow.core.communities_dir", lambda: tmp_path)
    # ... test logic
```

## Pre-Push Checklist

Before pushing, run all the same checks that CI/CD runs:

```bash
# Format code, then run all linters and tests
make fix-all
```

This single command will:
1. Auto-format code with black and isort
2. Run all linters (black, isort, pylint, mypy)
3. Run unit and integration tests with coverage

You can also run checks without auto-formatting:

```bash
make check-all
```

See all available Make commands with `make help`.

## CI/CD Pipeline

Pull requests trigger GitHub Actions CI which runs:

| Job | What it does |
|-----|-------------|
| **Lint** | black, isort, pylint, mypy |
| **Test** | pytest on Python 3.10, 3.11, 3.12 |
| **Docker Build** | Builds the image and verifies the container starts |
| **Security** | safety (dependency vulnerabilities) and bandit (code security scan) |

Lint checks for pylint, mypy, and isort are set to `continue-on-error` in CI, so they won't block your PR but you should still aim to fix any warnings.

## Submitting Changes

1. Create a feature branch from `dev`:
   ```bash
   git checkout dev
   git pull origin dev
   git checkout -b your-feature-name
   ```

2. Make your changes and commit with clear messages.

3. Run `make fix-all` to format and verify everything passes.

4. Push and open a pull request against the `dev` branch.

5. CI will automatically run all checks on your PR.

## Common Make Commands

| Command | Description |
|---------|-------------|
| `make help` | List all available commands |
| `make fix-all` | Auto-format + run all checks (recommended before push) |
| `make check-all` | Run all checks without formatting |
| `make format` | Auto-format code with black and isort |
| `make lint` | Run all linters |
| `make test` | Run pytest with coverage |
| `make clean` | Remove cache and generated files |
