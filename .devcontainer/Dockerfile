# Dev container — standalone dev environment for Community Energy Orchestrator
FROM mcr.microsoft.com/vscode/devcontainers/base:ubuntu-22.04

ENV DEBIAN_FRONTEND=noninteractive

# Install system dependencies required by OpenStudio/EnergyPlus + Python
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    ca-certificates \
    curl \
    libgfortran5 \
    libgomp1 \
    unzip \
    wget \
    python3.10 \
    python3.10-venv \
    python3.10-dev \
    && ln -sf /usr/bin/python3.10 /usr/local/bin/python \
    && ln -sf /usr/bin/python3.10 /usr/local/bin/python3 \
    && rm -rf /var/lib/apt/lists/*

# Install certificate management (follows bluesky pattern)
COPY .devcontainer/certs/ /tmp/certs/
COPY .devcontainer/scripts/certctl-safe.sh /tmp/
RUN chmod +x /tmp/certctl-safe.sh && \
    /tmp/certctl-safe.sh install && \
    /tmp/certctl-safe.sh certs-refresh && \
    rm -rf /tmp/certctl-safe.sh /tmp/certs/

# Install uv package manager to /usr/local/bin (available to all users, no sudo needed)
RUN bash -c '. /usr/local/bin/certctl && \
    certctl_load && \
    curl $CURL_FLAGS -Lo /tmp/uv.tar.gz https://github.com/astral-sh/uv/releases/latest/download/uv-x86_64-unknown-linux-gnu.tar.gz && \
    tar xzf /tmp/uv.tar.gz -C /tmp/ && \
    mv /tmp/uv-*/uv /usr/local/bin/uv && \
    mv /tmp/uv-*/uvx /usr/local/bin/uvx && \
    rm -rf /tmp/uv.tar.gz /tmp/uv-*'

# Install Node.js LTS (direct binary)
ARG NODE_VERSION=22.14.0
RUN bash -c '. /usr/local/bin/certctl && \
    certctl_load && \
    curl $CURL_FLAGS \
        "https://nodejs.org/dist/v${NODE_VERSION}/node-v${NODE_VERSION}-linux-x64.tar.gz" \
        -o /tmp/node.tar.gz && \
    tar -xzf /tmp/node.tar.gz -C /usr/local --strip-components=1 && \
    rm /tmp/node.tar.gz && \
    node --version && npm --version'

# Ensure /workspaces exists and is owned by vscode for "Clone in Container Volume"
RUN mkdir -p /workspaces && chown vscode:vscode /workspaces

# Default command for development
CMD ["/bin/bash"]
