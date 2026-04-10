"""Integration tests for Docker container functionality."""

import json
import os
import shutil
import subprocess
import time

import pytest

# Skip all tests in this module if Docker is not available
docker_available = shutil.which("docker") is not None
pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(not docker_available, reason="Docker is not available"),
]


def test_docker_compose_builds_successfully():
    """Test that docker compose build completes without errors.

    This validates that:
    - Dockerfile syntax is correct
    - All dependencies can be installed (uv, h2k-hpxml, etc.)
    - The image builds successfully in CI environment
    """
    result = subprocess.run(
        ["docker", "compose", "build", "api"],
        capture_output=True,
        text=True,
        timeout=300,
    )

    # Provide both stdout and stderr for better debugging
    assert (
        result.returncode == 0
    ), f"Docker build failed:\nSTDERR: {result.stderr}\nSTDOUT: {result.stdout}"

    # Verify the image was actually created
    check_image = subprocess.run(
        ["docker", "images", "-q", "community-energy-orchestrator:latest"],
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert check_image.returncode == 0, f"Failed to check for Docker image: {check_image.stderr}"
    assert check_image.stdout.strip(), "Docker image was not created"


@pytest.mark.slow
@pytest.mark.skipif(
    os.path.exists("/.dockerenv") or os.environ.get("REMOTE_CONTAINERS") is not None,
    reason="Skipped inside dev containers â€” starting the API container exhausts memory",
)
def test_docker_container_starts_and_responds():
    """Test that container starts and health endpoint responds correctly.

    This validates that:
    - Container starts without crashing
    - Health endpoint is accessible and returns expected response
    - Service is properly configured and running
    """
    # Start container (only the api service)
    subprocess.run(["docker", "compose", "up", "-d", "api"], check=True, timeout=60)

    try:
        # Wait for Docker healthcheck to pass (more reliable than fixed sleep)
        # The healthcheck has start_period=10s, interval=30s, so max wait ~40s
        max_attempts = 15
        wait_interval = 2

        for attempt in range(max_attempts):
            result = subprocess.run(
                ["docker", "inspect", "--format={{.State.Health.Status}}", "community-energy-api"],
                capture_output=True,
                text=True,
                timeout=5,
            )

            # Check if inspect command succeeded
            if result.returncode != 0:
                # Container might not exist yet, continue waiting
                time.sleep(wait_interval)
                continue

            health_status = result.stdout.strip()
            if health_status == "healthy":
                break
            elif health_status == "unhealthy":
                # Get logs for debugging
                logs = subprocess.run(
                    ["docker", "compose", "logs", "api"],
                    capture_output=True,
                    text=True,
                    timeout=10,
                )
                pytest.fail(f"Container became unhealthy.\nLogs:\n{logs.stdout}\n{logs.stderr}")

            time.sleep(wait_interval)
        else:
            pytest.fail(f"Container did not become healthy after {max_attempts * wait_interval}s")

        # Test health endpoint via curl inside container
        health_check = subprocess.run(
            [
                "docker",
                "compose",
                "exec",
                "-T",
                "api",
                "curl",
                "-f",
                "-s",
                "http://localhost:8000/health",
            ],
            capture_output=True,
            text=True,
            timeout=10,
        )

        # Validate health endpoint response
        assert (
            health_check.returncode == 0
        ), f"Health endpoint request failed: {health_check.stderr}"

        # Parse and validate JSON response
        try:
            health_data = json.loads(health_check.stdout)
        except json.JSONDecodeError as e:
            pytest.fail(
                f"Health endpoint returned invalid JSON: {e}\nResponse: {health_check.stdout}"
            )

        # Verify required fields from API specification
        assert (
            health_data.get("status") == "ok"
        ), f"Unexpected health status: {health_data.get('status')}"
        assert (
            "warning" in health_data
        ), "Health response missing 'warning' field (added in recent changes)"
        assert (
            "active_runs" in health_data
        ), "Health response missing 'active_runs' field (added in recent changes)"
        assert isinstance(
            health_data["active_runs"], int
        ), f"active_runs should be int, got {type(health_data['active_runs'])}"
        assert (
            "cert_status" in health_data
        ), "Health response missing 'cert_status' field for security status reporting"

    finally:
        # Clean up - capture errors for debugging but don't fail test
        down_result = subprocess.run(
            ["docker", "compose", "down", "-v"],
            capture_output=True,
            text=True,
            timeout=60,
        )
        if down_result.returncode != 0:
            print(f"Warning: Cleanup failed: {down_result.stderr}")


def test_docker_volume_mounts_exist():
    """Test that expected volume mount directories are configured.

    This validates that:
    - Persistent data volumes are properly mounted
    - Output and log directories will persist across container restarts
    - Source archetypes volume is configured (even if not present locally)
    """
    result = subprocess.run(
        ["docker", "compose", "config"],
        capture_output=True,
        text=True,
        timeout=10,
    )

    assert result.returncode == 0, f"Failed to get docker-compose config: {result.stderr}"
    config = result.stdout

    # Check that key data persistence volumes are mounted
    assert (
        "./output" in config or "/app/output" in config
    ), "output volume mount not found in config"
    assert "./logs" in config or "/app/logs" in config, "logs volume mount not found in config"

    # Check source-archetypes volume exists (required for workflow to function)
    # Path structure: ./data/source-archetypes:/app/data/source-archetypes
    assert (
        "./data/source-archetypes" in config or "/app/data/source-archetypes" in config
    ), "source-archetypes volume mount not found in config"
