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

## Development Workflow

### Before You Start Coding

1. **Format your code automatically:**
   ```bash
   make format
   ```

2. **Run checks during development** (see all issues at once):
   ```bash
   make dev-check
   ```
   This shows all linting and test failures without stopping, giving you the full picture.

### Before Pushing

Run the same strict checks that CI/CD will run:

```bash
make fix-all
```

This will:
1. Auto-format code with black and isort
2. Run pylint and mypy (strict - stops on first failure)
3. Run all tests with coverage (strict - stops on first failure)

**Important:** `make fix-all` uses **fail-fast** mode - it stops at the first error. This matches CI/CD behavior and helps you catch issues early.

If you want to see all issues at once during development, use `make dev-check` instead.

### Available Commands

| Command | When to Use | Behavior |
|---------|-------------|----------|
| `make format` | Before committing | Auto-format code (black + isort) |
| `make dev-check` | During development | Show ALL issues without stopping |
| `make fix-all` | Before pushing | **Strict**: Format + check, stop on first failure |
| `make check-all` | CI/CD simulation | **Strict**: Check only (no format), stop on first failure |
| `make test` | Quick test run | Run all tests with coverage |
| `make lint` | Check formatting | Verify code style without modifying |
| `make docker-disk` | Check disk usage | Show Docker disk usage |
| `make docker-clean` | Free disk space | Remove dangling images, stopped containers, build cache |
| `make docker-reset` | Full cleanup | Full Docker system prune (removes all unused resources) |

**Recommended workflow:**
1. Code your changes
2. Run `make dev-check` to see all issues
3. Fix issues iteratively
4. Run `make fix-all` before pushing - must pass cleanly

### Troubleshooting Failed Checks

**If `make fix-all` fails:**

1. **Formatting errors**: Run `make format` - it auto-fixes most issues
2. **Pylint warnings**: Review the specific warnings. Some are informational and acceptable (e.g., "too many local variables")
3. **Type errors (mypy)**: Add type hints or use `# type: ignore` comments sparingly
4. **Test failures**: Fix the failing tests. Run individual tests with `uv run pytest path/to/test.py -v` for faster iteration

**Common issues:**
- Line too long: black should auto-format this, but some strings may need manual breaking
- Import order: `make format` fixes this automatically
- Missing type hints: Add them or use `# type: ignore[return-value]` if justified

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

1. **Create a feature branch** from `dev`:
   ```bash
   git checkout dev
   git pull origin dev
   git checkout -b your-feature-name
   ```

2. **Make your changes** and commit with clear messages.

3. **Run checks before pushing:**
   ```bash
   make fix-all
   ```
   This must pass without errors before you push. If it fails, fix the issues and run again.

4. **Push and open a pull request** against the `dev` branch.

5. **CI will automatically run** all checks on your PR. The same `make fix-all` checks run in CI, so if it passes locally, it should pass in CI.

### Commit Messages

Write clear, descriptive commit messages:
- Use present tense ("Add feature" not "Added feature")
- Keep first line under 72 characters
- Reference issue numbers where applicable

## Quick Reference

### Make Commands

| Command | Description |
|---------|-------------|
| `make help` | List all available commands |
| `make format` | Auto-format code with black and isort |
| `make dev-check` | **Development:** Show all issues (continues on errors) |
| `make fix-all` | **Pre-push:** Auto-format + strict checks (stops on first failure) |
| `make check-all` | **CI/CD:** Strict checks without formatting (stops on first failure) |
| `make lint` | Check code style without modifying files |
| `make test` | Run all tests with coverage |
| `make clean` | Remove cache and generated files |
| `make docker-disk` | Show Docker disk usage |
| `make docker-clean` | Remove dangling images, stopped containers, build cache |
| `make docker-reset` | Full Docker system prune (removes all unused resources) |

### Testing Quick Reference

```bash
# Run all tests
make test

# Run specific test file
uv run pytest tests/unit/test_outputs.py -v

# Run unit tests only
uv run pytest tests/unit/ -m unit

# Run integration tests only
uv run pytest tests/integration/ -m integration

# Run with verbose output
uv run pytest -v

# Run tests matching a pattern
uv run pytest -k "test_calculate"
```
