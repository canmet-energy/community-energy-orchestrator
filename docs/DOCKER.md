# Docker Guide

Run the Community Energy Orchestrator in a container with all dependencies pre-installed. No need to install Python, OpenStudio, or EnergyPlus on your machine.

> **Prefer installing locally?** See the [Installation Guide](INSTALLATION.md) for manual setup without Docker.

## Prerequisites

- **Docker** installed — get it from https://docs.docker.com/get-docker/
- **Git** — to clone the repository

## Step 1: Clone the Repository

```bash
git clone https://github.com/canmet-energy/community-energy-orchestrator.git
cd community-energy-orchestrator
```

## Step 2: Download the Archetype Library

The workflow requires a local library of Hot2000 archetype files. Follow the download instructions in the [Installation Guide](INSTALLATION.md#step-6-download-the-archetype-library).

The archetype library is **not** baked into the Docker image. It is mounted as a volume at runtime via docker-compose, so you need it on your host machine before running `docker-compose up`.

## Step 3: Build the Docker Image

```bash
docker build -t community-energy-orchestrator .
```

The build installs Python 3.10, all dependencies (via uv), and OpenStudio/EnergyPlus automatically inside the container.

**Build time:** ~5–10 minutes | **Image size:** ~2–3 GB

<details>
<summary>NRCan network: Corporate certificate setup</summary>

If you are building behind the NRCan corporate network (SSL inspection), place your certificate files (`.crt` or `.pem`) in `.devcontainer/certs/` before building. The build process will automatically detect and configure them. See `.devcontainer/certs/README.md` for details.

Without certificates, the build falls back to insecure mode — acceptable for development but not recommended for production.

</details>

## Step 4: Run the Application

### Option A: Docker Compose (Recommended)

Starts both the API and the web frontend:

```bash
# Start both services
docker-compose up

# Or run in the background
docker-compose up -d
```

Then open:
- **Frontend:** http://localhost:5173
- **API docs:** http://localhost:8000/docs

Docker Compose automatically mounts `output/`, `logs/`, and `data/source-archetypes/` from your host machine, so outputs persist after the container stops.

```bash
# View logs
docker-compose logs -f

# Stop services
docker-compose down
```

### Option B: Docker Run (API Only)

```bash
docker run -p 8000:8000 community-energy-orchestrator
```

Then open http://localhost:8000/docs.

> **Note:** With `docker run`, outputs are lost when the container stops unless you add volume mounts. See [Persistent Storage](#persistent-storage) below.

## Running the CLI in Docker

The default container command starts the API server. To run the CLI workflow instead:

Linux/macOS:

```bash
docker run -it \
  -v $(pwd)/output:/app/output \
  -v $(pwd)/logs:/app/logs \
  -v $(pwd)/data/source-archetypes:/app/data/source-archetypes \
  community-energy-orchestrator \
  process-community "Old Crow"
```

Windows (PowerShell):

```powershell
docker run -it `
  -v ${PWD}/output:/app/output `
  -v ${PWD}/logs:/app/logs `
  -v ${PWD}/data/source-archetypes:/app/data/source-archetypes `
  community-energy-orchestrator `
  process-community "Old Crow"
```

## Environment Variables

Configure the workflow with environment variables:

| Variable | Description | Default |
|----------|-------------|---------|
| `MAX_PARALLEL_WORKERS` | Number of parallel simulation processes | Auto-detected from CPU count |
| `ANALYSIS_RANDOM_SEED` | Seed for reproducible file duplication in analysis | Random |
| `ARCHETYPE_SELECTION_SEED` | Seed for reproducible archetype selection | Random |

With docker run:

```bash
docker run -p 8000:8000 \
  -e MAX_PARALLEL_WORKERS=4 \
  -e ARCHETYPE_SELECTION_SEED=12345 \
  community-energy-orchestrator
```

With docker-compose, uncomment the environment variables in `docker-compose.yml` or create a `.env` file.

## Troubleshooting

### Build errors

| Error | Solution |
|-------|----------|
| "SSL certificate problem: self-signed certificate in certificate chain" | Place corporate certificates in `.devcontainer/certs/` and rebuild |
| "os-setup command not found" | The h2k-hpxml package may not have installed — check `pyproject.toml` |
| "git clone failed" | Check internet connectivity (h2k-hpxml is installed from GitHub) |

### Runtime errors

**API not responding:**

```bash
docker ps                    # Check if container is running
docker logs community-energy-api   # View application logs
```

**Simulations failing:**

```bash
# Verify OpenStudio installation inside the container
docker exec -it community-energy-api os-setup --test-installation

# Check that source-archetypes are mounted
docker exec -it community-energy-api ls data/source-archetypes/
```

### Performance

The container auto-detects CPU count for parallel processing. To limit resources:

```bash
docker run -p 8000:8000 \
  --cpus=4 \
  --memory=8g \
  -e MAX_PARALLEL_WORKERS=4 \
  community-energy-orchestrator
```

## Next Steps

- [User Guide](USER_GUIDE.md) — Learn how to use the CLI, API, and frontend
- [Background](BACKGROUND.md) — Understand what the tool does and how it works
