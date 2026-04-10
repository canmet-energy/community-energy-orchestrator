# Docker Deployment Guide

Complete guide for building and running the Community Energy Orchestrator using Docker.

## Prerequisites

1. **Docker installed** - Get it from https://docs.docker.com/get-docker/
2. **Source archetypes downloaded** - See below

## Setup: Download Archetype Library

**⚠️ REQUIRED:** This directory is needed to process communities.

1. Go to https://github.com/canmet-energy/housing-archetypes.git
2. Navigate to `data/h2k_files/existing-stock`
3. Download folder: `retrofit-archetypes-for-diesel-reduction-modelling-in-remote-communities`
4. Rename it to `source-archetypes`
5. Place it in the `data/` directory of this repo

**Verify:** Check that `data/source-archetypes/2002-2016-single/2002-2016-single_EX-0001.H2K` exists.

## Building the Image

```bash
# Build from the repo root directory
docker build -t community-energy-orchestrator .
```

**For NRCan network:** Place your corporate certificate files (`.crt` or `.pem`) in the `.devcontainer/certs/` folder before building. The build process will:
- Automatically detect and validate certificates
- Display security status (SECURE or INSECURE mode)
- Set appropriate SSL settings for all tools

See `.devcontainer/certs/README.md` for detailed instructions.

**Build time:** ~5-10 minutes
**Image size:** ~2-3 GB (includes Python, dependencies, OpenStudio, EnergyPlus)

### Build Process

The Dockerfile:
1. Installs Python 3.10 (compatible with your project's 3.10-3.12 range)
2. Installs certificate management (`certctl`) and any certificates from `certs/`
3. Copies application source code (app/ and workflow/ directories)
4. Installs `uv` package manager for fast, reproducible dependency installation
5. Installs all Python dependencies (using your `uv.lock` if present)
6. Installs OpenStudio/EnergyPlus via `os-setup`
7. Copies JSON configuration files
8. Creates runtime directories


### Common Build Issues

**Error: "SSL certificate problem: self-signed certificate in certificate chain"**
- Cause: Corporate network with SSL inspection
- Solution: Place your corporate certificate files in `.devcontainer/certs/` folder and rebuild. See `.devcontainer/certs/README.md`

**Build shows "⚠️ Certificates: Insecure mode"**
- This is acceptable for development/testing or building outside corporate networks
- For production in NRCan network, add certificates to `.devcontainer/certs/` folder
- The build will automatically use insecure mode (-k flags) as a fallback

**Error: "os-setup command not found"**
- Solution: The h2k-hpxml package may not have installed. Check that pyproject.toml is correct.

**Error: "git clone failed"**
- Solution: Check internet connectivity. The h2k-hpxml dependency is installed from GitHub.

## Running the Container

### Option 1: Using Docker Run (Simple)

```bash
# Run the FastAPI server (default)
docker run -p 8000:8000 community-energy-orchestrator

# Access the API at: http://localhost:8000/docs
```

### Option 2: Using Docker Compose (Recommended)

Starts both the API and the web frontend:

```bash
# Start services (API on port 8000, frontend on port 5173)
docker-compose up

# Run in background (detached mode)
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down
```

**Benefits of docker-compose:**
- Starts both API and frontend together
- Automatic volume mounting for outputs
- Easy restart policies
- Health checks configured
- Environment variable management

### With Persistent Storage

By default, outputs (output/ and logs/) are generated inside the container and lost when the container stops. To persist them:

Linux/macOS:

```bash
# With docker run
docker run -p 8000:8000 \
  -v $(pwd)/output:/app/output \
  -v $(pwd)/logs:/app/logs \
  community-energy-orchestrator
```

Windows (PowerShell):

```powershell
# With docker run
docker run -p 8000:8000 `
  -v ${PWD}/output:/app/output `
  -v ${PWD}/logs:/app/logs `
  community-energy-orchestrator
```

With docker-compose (all platforms):

```bash
# With docker-compose (already configured)
docker-compose up
```

## Running the CLI Workflow

The default container command runs the FastAPI server. To run the CLI script instead:

Linux/macOS:

```bash
# Run a specific community
docker run -it community-energy-orchestrator \
  process-community "Old Crow"

# With persistent outputs
docker run -it \
  -v $(pwd)/output:/app/output \
  -v $(pwd)/logs:/app/logs \
  community-energy-orchestrator \
  process-community "Old Crow"
```

Windows (PowerShell):

```powershell
# Run a specific community
docker run -it community-energy-orchestrator `
  process-community "Old Crow"

# With persistent outputs
docker run -it `
  -v ${PWD}/output:/app/output `
  -v ${PWD}/logs:/app/logs `
  community-energy-orchestrator `
  process-community "Old Crow"
```

## Environment Variables

Configure the workflow with environment variables:

Linux/macOS:

```bash
# Using docker run
docker run -p 8000:8000 \
  -e MAX_PARALLEL_WORKERS=4 \
  -e ANALYSIS_RANDOM_SEED=42 \
  -e ARCHETYPE_SELECTION_SEED=12345 \
  community-energy-orchestrator
```

Windows (PowerShell):

```powershell
# Using docker run
docker run -p 8000:8000 `
  -e MAX_PARALLEL_WORKERS=4 `
  -e ANALYSIS_RANDOM_SEED=42 `
  -e ARCHETYPE_SELECTION_SEED=12345 `
  community-energy-orchestrator
```

Or with docker-compose:

```bash
# Or create a .env file for docker-compose (already configured)
```

Available variables:
- `MAX_PARALLEL_WORKERS`: Number of parallel processes (default: auto-detected)
- `ANALYSIS_RANDOM_SEED`: Seed for reproducible file duplication in analysis
- `ARCHETYPE_SELECTION_SEED`: Seed for reproducible archetype selection

## Accessing Running Containers

```bash
# List running containers
docker ps

# Get a shell inside the running container
docker exec -it community-energy-api /bin/bash

# View container logs
docker logs community-energy-api

# Follow logs in real-time
docker logs -f community-energy-api
```

## Stopping and Cleaning Up

```bash
# Stop the container (docker run)
docker stop <container-id>

# Stop services (docker-compose)
docker-compose down

# Remove the image
docker rmi community-energy-orchestrator

# Clean up all stopped containers and unused images
docker system prune -a
```

## Comparison: Docker vs Dev Container

| Docker (Production) | Dev Container (Development) |
|--------------------|-----------------------------|
| Runs the API server | Full VS Code dev environment |
| Minimal runtime only | Includes dev tools (pytest, black, pylint) |
| No source code mounting | Live code editing with hot reload |
| Immutable image | Interactive development |
| For end users | For contributors |

**When to use which:**
- **Docker**: Share your app, deploy to servers, run in production
- **Dev Container**: Develop new features, debug issues, contribute code

## Troubleshooting

### API not responding

```bash
# Check if container is running
docker ps

# Check health status
docker inspect community-energy-api | grep Health

# View application logs
docker logs community-energy-api
```

### Simulations failing inside container

```bash
# Verify OpenStudio installation
docker exec -it community-energy-api os-setup --test-installation

# Check if source-archetypes were copied
docker exec -it community-energy-api ls -la data/source-archetypes/
```

Run a test community:

Linux/macOS:

```bash
docker exec -it community-energy-api \
  process-community "Old Crow"
```

Windows (PowerShell):

```powershell
docker exec -it community-energy-api `
  process-community "Old Crow"
```

### Performance Issues

The container uses automatic CPU detection for parallel processing. To limit resources:

Linux/macOS:

```bash
# Limit CPU and memory
docker run -p 8000:8000 \
  --cpus=4 \
  --memory=8g \
  -e MAX_PARALLEL_WORKERS=4 \
  community-energy-orchestrator
```

Windows (PowerShell):

```powershell
# Limit CPU and memory
docker run -p 8000:8000 `
  --cpus=4 `
  --memory=8g `
  -e MAX_PARALLEL_WORKERS=4 `
  community-energy-orchestrator
```

### Rebuilding After Changes

```bash
# Rebuild without cache (clean build)
docker build --no-cache -t community-energy-orchestrator .

# Or with docker-compose
docker-compose build --no-cache
```

## Security Notes

- Container runs as a non-root user (`appuser`) for security
- No secrets should be baked into the image
- Use environment variables or secrets management for sensitive data
- The API has no authentication - add a reverse proxy with auth for production

## Advanced: Multi-Stage Builds

For smaller production images, consider a multi-stage build (not included in current Dockerfile):
- Stage 1: Build dependencies and install tools
- Stage 2: Copy only runtime artifacts
- Result: ~30-50% smaller image size

## Next Steps

- See [User Guide](USER_GUIDE.md) for API usage
- See [Installation Guide](INSTALLATION.md) for manual setup
- See [README.md](../README.md) for project overview
