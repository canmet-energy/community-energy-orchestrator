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
    git \
    libgfortran5 \
    libgomp1 \
    unzip \
    wget \
    && rm -rf /var/lib/apt/lists/*

# Install certificate management (follows bluesky pattern)
# Place corporate certificates in .devcontainer/certs/ before building
COPY .devcontainer/certs/ /tmp/certs/
COPY .devcontainer/scripts/certctl-safe.sh /tmp/
RUN chmod +x /tmp/certctl-safe.sh && \
    /tmp/certctl-safe.sh install && \
    /tmp/certctl-safe.sh certs-refresh && \
    rm -rf /tmp/certctl-safe.sh /tmp/certs/

# Copy dependency files first
COPY pyproject.toml uv.lock* ./

# Copy source code needed for package installation
# (pyproject.toml specifies packages in backend/, so backend/ must exist before pip install)
COPY backend/app/ ./backend/app/
COPY backend/workflow/ ./backend/workflow/

# Load certificate environment and install uv
# Download uv binary directly (the install script makes its own curl calls that don't use $CURL_FLAGS)
RUN bash -c '. /usr/local/bin/certctl && \
    certctl_load && \
    certctl_banner && \
    curl $CURL_FLAGS -Lo /tmp/uv.tar.gz https://github.com/astral-sh/uv/releases/latest/download/uv-x86_64-unknown-linux-gnu.tar.gz && \
    tar xzf /tmp/uv.tar.gz -C /tmp/ && \
    mv /tmp/uv-*/uv /usr/local/bin/uv && \
    mv /tmp/uv-*/uvx /usr/local/bin/uvx && \
    rm -rf /tmp/uv.tar.gz /tmp/uv-* && \
    uv --version'

# Install Python dependencies using uv (respects uv.lock if present)
RUN bash -c '. /usr/local/bin/certctl && \
    certctl_load && \
    uv pip install --system --no-cache .'

# Persist certificate status from build into runtime environment
# certctl_load sets CERT_STATUS during RUN but it doesn't survive across layers.
# Re-probe and write the result so the API can report it at runtime.
RUN bash -c '. /usr/local/bin/certctl && certctl_load && \
    echo "CERT_STATUS=${CERT_STATUS:-UNKNOWN}" >> /etc/environment'

# Make h2k_hpxml utils dir writable so non-root user can create weather .lock files
RUN find /usr/local/lib -path "*/h2k_hpxml/utils" -type d -exec chmod -R a+w {} +

# Copy JSON configuration files (required for community requirements and weather mapping)
COPY data/json/ ./data/json/

# NOTE: source-archetypes directory is NOT included in git and must be provided at runtime
# Either mount as a volume: -v ./data/source-archetypes:/app/data/source-archetypes
# Or download into the container after starting

# Create non-root user for security (UID 1000 for compatibility with host volume mounts)
# Use --create-home so appuser owns /app and can write to ~/.local, ~/.config, etc.
RUN groupadd -g 1000 appuser && useradd -u 1000 -g appuser -d /app --no-create-home appuser \
    && chown -R appuser:appuser /app

# Create runtime directories for outputs and logs
RUN mkdir -p output logs communities

# Install OpenStudio/EnergyPlus as appuser so binaries land in /app/.local/share/
USER appuser
RUN bash -c '. /usr/local/bin/certctl && certctl_load && \
    os-setup --install-quiet && os-setup --check-only'

# Set Python to run in unbuffered mode (better for Docker logs)
ENV PYTHONUNBUFFERED=1

# Set APP_ROOT so installed package can find data/, communities/, etc.
ENV APP_ROOT=/app

# Expose the default FastAPI port
EXPOSE 8000

# Run the FastAPI application with uvicorn
# Uses 'app.main:app' — packages are installed as top-level modules via
# setuptools packages.find where=["backend"]
CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
