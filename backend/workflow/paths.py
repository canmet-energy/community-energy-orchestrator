"""Path utilities for the workflow package."""

import os
from pathlib import Path


def project_root() -> Path:
    root = os.environ.get("APP_ROOT")
    if root:
        return Path(root)
    # When running from source (not pip-installed), traverse up from this file.
    # Verify the candidate contains pyproject.toml to avoid silently resolving
    # to the Python installation directory when the package is installed.
    candidate = Path(__file__).resolve().parent.parent.parent
    if (candidate / "pyproject.toml").exists():
        return candidate
    # Fall back to current working directory (matches WORKDIR in Docker)
    cwd = Path.cwd()
    if (cwd / "pyproject.toml").exists():
        return cwd
    raise RuntimeError(
        "Cannot determine project root. Set the APP_ROOT environment variable "
        "to the directory containing data/, output/, etc."
    )


def output_dir() -> Path:
    return project_root() / "output"


def data_dir() -> Path:
    return project_root() / "data"


def json_dir() -> Path:
    return project_root() / "data" / "json"


def logs_dir() -> Path:
    return project_root() / "logs"


def source_archetypes_dir() -> Path:
    return project_root() / "data" / "source-archetypes"
