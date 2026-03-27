# Use Python 3.10 for maximum compatibility (project supports 3.10-3.12)
# Using bookworm instead of slim (trixie) for better dev container feature compatibility
FROM python:3.10-bookworm

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    ca-certificates \
    curl \
    libgfortran5 \
    libgomp1 \
    unzip \
    wget \
    && rm -rf /var/lib/apt/lists/*

# Copy dependency files first
COPY pyproject.toml uv.lock* ./

# Copy source code needed for package installation
# (pyproject.toml specifies packages in src/, so src/ must exist before pip install)
COPY src/app/ ./src/app/
COPY src/workflow/ ./src/workflow/

# Install uv for faster, reproducible dependency management
RUN pip install --no-cache-dir uv

# Install Python dependencies using uv (respects uv.lock if present)
RUN uv pip install --system --no-cache .

# Make h2k_hpxml utils dir writable so non-root user can create weather .lock files
RUN find /usr/local/lib -path "*/h2k_hpxml/utils" -type d -exec chmod -R a+w {} +

# Copy CSV data files (required for community requirements and weather mapping)
COPY csv/ ./csv/

# NOTE: source-archetypes directory is NOT included in git and must be provided at runtime
# Either mount as a volume: -v ./src/source-archetypes:/app/src/source-archetypes
# Or download into the container after starting

# Create non-root user for security (UID 1000 for compatibility with host volume mounts)
# Use --create-home so appuser owns /app and can write to ~/.local, ~/.config, etc.
RUN groupadd -g 1000 appuser && useradd -u 1000 -g appuser -d /app --no-create-home appuser \
    && chown -R appuser:appuser /app

# Create runtime directories for outputs and logs
RUN mkdir -p output logs communities

# Install OpenStudio/EnergyPlus as appuser so binaries land in /app/.local/share/
USER appuser
RUN os-setup --install-quiet && os-setup --check-only

# Set Python to run in unbuffered mode (better for Docker logs)
ENV PYTHONUNBUFFERED=1

# Set APP_ROOT so installed package can find csv/, communities/, etc.
ENV APP_ROOT=/app

# Expose the default FastAPI port
EXPOSE 8000

# Run the FastAPI application with uvicorn
# Note: Use 'app.main:app' not 'src.app.main:app' because packages are installed
# as top-level 'app' and 'workflow' modules (setuptools packages.find where=["src"])
CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
