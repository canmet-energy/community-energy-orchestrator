.PHONY: help test lint static-analysis format check-all fix-all clean

help:
	@echo "Available commands:"
	@echo "  make test        - Run pytest with coverage"
	@echo "  make lint        - Run all linters (black, isort, pylint, mypy)"
	@echo "  make format      - Auto-format code with black and isort"
	@echo "  make check-all   - Run all checks (lint + test) - same as CI/CD"
	@echo "  make fix-all     - Auto-format then run all checks (recommended before push)"
	@echo "  make clean       - Remove cache and coverage files"

# Auto-format, then run static analysis + tests (recommended before pushing)
fix-all: format static-analysis test
	@echo "✓ Code formatted and all checks passed!"

# Run all checks like CI/CD does (no auto-formatting)
check-all: lint test
	@echo "✓ All checks passed!"

# Run all linters including format checks (for CI/CD or manual checking)
lint:
	@echo "Running black..."
	uv run black --check src/ tests/
	@echo "Running isort..."
	uv run isort --check-only src/ tests/
	@echo "Running pylint..."
	uv run pylint src/
	@echo "Running mypy..."
	uv run mypy src/

# Run only static analysis (pylint + mypy), skipping format checks
static-analysis:
	@echo "Running pylint..."
	uv run pylint src/
	@echo "Running mypy..."
	uv run mypy src/

# Run tests with coverage (matching CI/CD)
test:
	@echo "Running unit tests..."
	uv run pytest tests/unit/ -m unit --cov=src/ --cov-report=term-missing
	@echo "Running integration tests..."
	uv run pytest tests/integration/ -m integration

# Auto-format code
format:
	@echo "Formatting with black..."
	uv run black src/ tests/
	@echo "Sorting imports with isort..."
	uv run isort src/ tests/

# Clean up generated files
clean:
	@echo "Cleaning up..."
	rm -rf __pycache__ .pytest_cache .mypy_cache .coverage htmlcov/ coverage.xml
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
