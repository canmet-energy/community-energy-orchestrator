#!/usr/bin/env bash
# Post-create setup script for Community Energy Orchestrator devcontainer
# Runs once after the container is created to set up the development environment
set -euo pipefail

# Fix workspace ownership — Windows Docker Desktop can mount files as root:root,
# which prevents non-sudo commands (npm ci, os-setup) from writing to the workspace.
echo "==> Fixing workspace file ownership..."
sudo chown -R vscode:vscode .

echo "==> Installing uv package manager..."
sudo pip install --no-cache-dir uv

echo "==> Installing Python dependencies (editable, with dev tools)..."
sudo uv pip install --system -e ".[dev]"

echo "==> Installing OpenStudio/EnergyPlus..."
os-setup --install-quiet

echo "==> Making h2k_hpxml utils writable for weather lock files..."
sudo find /usr/local/lib -path "*/h2k_hpxml/utils" -type d -exec chmod -R a+w {} +

echo "==> Installing frontend dependencies..."
cd frontend
npm config set cafile /etc/ssl/certs/ca-certificates.crt
npm ci
cd ..

# Fix ownership again — sudo commands above create root-owned files
# (e.g. egg-info from editable install). Ensures vscode user can run
# uv sync, pytest, etc. without permission errors.
echo "==> Fixing workspace file ownership..."
sudo chown -R vscode:vscode .

echo "==> Dev container ready!"
