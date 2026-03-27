# Dev container — standalone dev environment for Community Energy Orchestrator
FROM mcr.microsoft.com/vscode/devcontainers/base:ubuntu-22.04

ENV DEBIAN_FRONTEND=noninteractive

# Install system dependencies required by OpenStudio/EnergyPlus + Python + pip
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
    python3-pip \
    && ln -sf /usr/bin/python3.10 /usr/local/bin/python \
    && ln -sf /usr/bin/python3.10 /usr/local/bin/python3 \
    && rm -rf /var/lib/apt/lists/*

# Without this, the -k flag on curl and strict-ssl=false on npm are used as fallbacks.
ARG GIT_API_TOKEN='nothing'
ARG LOCALNRCAN=''
RUN if [ -n "$LOCALNRCAN" ] ; then \
      echo "Installing NRCan certificates from private repo..." \
      && git clone https://${GIT_API_TOKEN}:x-oauth-basic@github.com/canmet-energy/linux_nrcan_certs.git \
         --depth 1 --single-branch /tmp/linux_nrcan_certs \
      && cd /tmp/linux_nrcan_certs \
      && ./install_nrcan_certs.sh \
      && echo "NRCan certs installed (revision: $(git rev-parse --short HEAD))" \
      && rm -rf /tmp/linux_nrcan_certs; \
    fi

# Install Node.js LTS (direct binary)
# Note: uses -k as fallback when NRCan certs are not installed (corporate proxy)
ARG NODE_VERSION=22.14.0
RUN curl -fsSL$(if [ -z "$LOCALNRCAN" ]; then echo "k"; fi) \
        "https://nodejs.org/dist/v${NODE_VERSION}/node-v${NODE_VERSION}-linux-x64.tar.gz" \
        -o /tmp/node.tar.gz \
    && tar -xzf /tmp/node.tar.gz -C /usr/local --strip-components=1 \
    && rm /tmp/node.tar.gz \
    && node --version && npm --version

# Default command for development
CMD ["/bin/bash"]
