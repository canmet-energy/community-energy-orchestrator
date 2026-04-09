.PHONY: help test lint static-analysis format check-all fix-all dev-check clean docker-clean docker-reset docker-disk

help:
	@echo "Available commands:"
	@echo "  make test         - Run pytest with coverage"
	@echo "  make lint         - Run all linters (black, isort, pylint, mypy)"
	@echo "  make format       - Auto-format code with black and isort"
	@echo "  make check-all    - Run all checks (strict, stops on first failure)"
	@echo "  make fix-all      - Auto-format then run strict checks (recommended before push)"
	@echo "  make dev-check    - Show all issues without stopping (local development)"
	@echo "  make clean        - Remove cache and coverage files"
	@echo "  make docker-disk  - Show Docker disk usage"
	@echo "  make docker-clean - Remove dangling images, stopped containers, build cache"
	@echo "  make docker-reset - Full Docker system prune (keeps named volumes)"

# Auto-format, then run strict checks (fail fast - recommended before push)
fix-all: format static-analysis test
	@echo "✓ Code formatted and all checks passed!"

# Local development: run all checks and show summary (continue on errors)
dev-check: format
	@echo "========================================"
	@echo "Running All Checks (dev mode)..."
	@echo "========================================"
	@PYLINT_EXIT=0; \
	uv run pylint backend/ || PYLINT_EXIT=$$?; \
	echo ""; \
	echo "========================================"; \
	echo "Running mypy..."; \
	echo "========================================"; \
	MYPY_EXIT=0; \
	uv run mypy backend/ || MYPY_EXIT=$$?; \
	echo ""; \
	echo "========================================"; \
	echo "Running Tests..."; \
	echo "========================================"; \
	TEST_EXIT=0; \
	uv run pytest tests/unit/ -m unit --cov=backend/ --cov-report=term-missing || TEST_EXIT=$$?; \
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
	uv run black --check backend/ tests/
	@echo "Running isort..."
	uv run isort --check-only backend/ tests/
	@echo "Running pylint..."
	uv run pylint backend/
	@echo "Running mypy..."
	uv run mypy backend/

# Run only static analysis (pylint + mypy), skipping format checks
static-analysis:
	@echo "Running pylint..."
	uv run pylint backend/
	@echo "Running mypy..."
	uv run mypy backend/

# Run tests with coverage (matching CI/CD)
test:
	@echo "Running unit tests..."
	uv run pytest tests/unit/ -m unit --cov=backend/ --cov-report=term-missing
	@echo "Running integration tests..."
	uv run pytest tests/integration/ -m integration

# Auto-format code
format:
	@echo "Formatting with black..."
	uv run black backend/ tests/
	@echo "Sorting imports with isort..."
	uv run isort backend/ tests/

# Clean up generated files
clean:
	@echo "Cleaning up..."
	rm -rf __pycache__ .pytest_cache .mypy_cache .coverage htmlcov/ coverage.xml
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete

# Show Docker disk usage
docker-disk:
	@echo "Docker disk usage:"
	docker system df

# Remove dangling images, stopped containers, and build cache
docker-clean:
	@echo "Cleaning Docker resources..."
	docker container prune -f
	docker image prune -f
	docker builder prune -f
	docker volume prune -f --filter "label!=keep"
	@echo "Done. Run 'make docker-disk' to verify."

# Full system prune (removes all unused images, not just dangling)
docker-reset:
	@echo "WARNING: This removes ALL unused Docker images, containers, networks, and build cache."
	docker system prune -a -f --volumes
	@echo "Done. Run 'make docker-disk' to verify."
