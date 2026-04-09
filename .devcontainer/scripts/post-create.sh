#!/usr/bin/env bash
# Post-create setup script for Community Energy Orchestrator devcontainer
# Runs once after the container is created to set up the development environment
set -euo pipefail

# Load certificate environment for all subsequent commands
# This sets CURL_FLAGS, GIT_SSL_NO_VERIFY, UV_INSECURE_HOST, NPM_CONFIG_STRICT_SSL, etc.
if [ -f /usr/local/bin/certctl ]; then
    echo "==> Loading certificate environment..."
    # shellcheck disable=SC1091
    . /usr/local/bin/certctl
    certctl_load || true
    certctl_banner || true
fi

# Fix workspace ownership — Windows Docker Desktop can mount files as root:root,
# which prevents non-sudo commands (npm ci, os-setup) from writing to the workspace.
echo "==> Fixing workspace file ownership..."
sudo chown -R vscode:vscode .

# Create/refresh venv owned by vscode (no sudo needed → no root-owned egg-info)
echo "==> Creating Python virtual environment..."
uv venv --python python3.10 --clear
export PATH="${PWD}/.venv/bin:$PATH"
export VIRTUAL_ENV="${PWD}/.venv"

echo "==> Installing Python dependencies (editable, with dev tools)..."
uv pip install -e ".[dev]"

echo "==> Installing OpenStudio/EnergyPlus..."
os-setup --install-quiet

echo "==> Making h2k_hpxml utils writable for weather lock files..."
sudo find /usr/local/lib -path "*/h2k_hpxml/utils" -type d -exec chmod -R a+w {} +

echo "==> Installing frontend dependencies..."
cd frontend
npm config set cafile /etc/ssl/certs/ca-certificates.crt
npm ci
cd ..

# Auto-activate venv in new terminals
if ! grep -q 'Auto-activate project venv' ~/.bashrc 2>/dev/null; then
    cat >> ~/.bashrc << 'EOF'

# Auto-activate project venv
for CANDIDATE in /workspaces/community-energy-orchestrator /workspaces/*; do
  if [ -f "${CANDIDATE}/.venv/bin/activate" ] && [ -z "$VIRTUAL_ENV" ]; then
    . "${CANDIDATE}/.venv/bin/activate"
    break
  fi
done
EOF
fi

echo "==> Dev container ready!"
