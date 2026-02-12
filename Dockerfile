# Use Python 3.10 for maximum compatibility (project supports 3.10-3.13)
FROM python:3.10-slim

# Set working directory
WORKDIR /app

# Install system dependencies needed for building Python packages and OpenStudio
RUN apt-get update && apt-get install -y \
    git \
    build-essential \
    wget \
    curl \
    ca-certificates \
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

# Verify h2k-hpxml is installed and install OpenStudio/EnergyPlus
# Note: os-setup may require sudo privileges for some installations
RUN h2k-hpxml --version && \
    (os-setup --auto-install || echo "WARNING: os-setup auto-install failed, manual setup may be required") && \
    os-setup --test-installation

# Copy CSV data files (required for community requirements and weather mapping)
COPY csv/ ./csv/

# CRITICAL: Verify source-archetypes exists before continuing
# This directory is NOT in git and must be downloaded manually before building
# If missing, the build will fail here with a clear error message
COPY src/source-archetypes/ ./src/source-archetypes/
RUN if [ ! -f "src/source-archetypes/2001-2015-single_EX-0001.H2K" ]; then \
        echo "ERROR: source-archetypes directory is empty or missing required files!"; \
        echo "You must download the archetype library before building Docker image."; \
        echo "See README.md for instructions."; \
        exit 1; \
    fi

# Create runtime directories for outputs and logs
RUN mkdir -p output logs communities

# Set Python to run in unbuffered mode (better for Docker logs)
ENV PYTHONUNBUFFERED=1

# Expose the default FastAPI port
EXPOSE 8000

# Run the FastAPI application with uvicorn
# Note: Use 'app.main:app' not 'src.app.main:app' because packages are installed
# as top-level 'app' and 'workflow' modules (setuptools packages.find where=["src"])
CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
