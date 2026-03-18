.PHONY: help test lint static-analysis format check-all fix-all dev-check clean

help:
	@echo "Available commands:"
	@echo "  make test        - Run pytest with coverage"
	@echo "  make lint        - Run all linters (black, isort, pylint, mypy)"
	@echo "  make format      - Auto-format code with black and isort"
	@echo "  make check-all   - Run all checks (strict, stops on first failure)"
	@echo "  make fix-all     - Auto-format then run strict checks (recommended before push)"
	@echo "  make dev-check   - Show all issues without stopping (local development)"
	@echo "  make clean       - Remove cache and coverage files"

# Auto-format, then run strict checks (fail fast - recommended before push)
fix-all: format static-analysis test
	@echo "✓ Code formatted and all checks passed!"

# Local development: run all checks and show summary (continue on errors)
dev-check: format
	@echo "========================================"
	@echo "Running All Checks (dev mode)..."
	@echo "========================================"
	@PYLINT_EXIT=0; \
	uv run pylint src/ || PYLINT_EXIT=$$?; \
	echo ""; \
	echo "========================================"; \
	echo "Running mypy..."; \
	echo "========================================"; \
	MYPY_EXIT=0; \
	uv run mypy src/ || MYPY_EXIT=$$?; \
	echo ""; \
	echo "========================================"; \
	echo "Running Tests..."; \
	echo "========================================"; \
	TEST_EXIT=0; \
	uv run pytest tests/unit/ -m unit --cov=src/ --cov-report=term-missing || TEST_EXIT=$$?; \
	uv run pytest tests/integration/ -m integration || TEST_EXIT=$$?; \
	echo ""; \
	echo "========================================"; \
	echo "SUMMARY"; \
	echo "========================================"; \
	if [ $$PYLINT_EXIT -eq 0 ]; then \
		echo "✓ Pylint: PASSED"; \
	else \
		echo "✗ Pylint: FAILED (exit code $$PYLINT_EXIT) - Review warnings above"; \
	fi; \
	if [ $$MYPY_EXIT -eq 0 ]; then \
		echo "✓ Mypy: PASSED"; \
	else \
		echo "✗ Mypy: FAILED (exit code $$MYPY_EXIT)"; \
	fi; \
	if [ $$TEST_EXIT -eq 0 ]; then \
		echo "✓ Tests: PASSED"; \
	else \
		echo "✗ Tests: FAILED (exit code $$TEST_EXIT)"; \
	fi; \
	echo "========================================"; \
	if [ $$PYLINT_EXIT -eq 0 ] && [ $$MYPY_EXIT -eq 0 ] && [ $$TEST_EXIT -eq 0 ]; then \
		echo "✓ All checks passed! Safe to push."; \
		exit 0; \
	else \
		echo "⚠ Some checks failed - review output above"; \
		exit 1; \
	fi

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
