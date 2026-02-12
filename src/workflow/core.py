


"""Core path utilities for the workflow package."""
from pathlib import Path


def project_root() -> Path:
    return Path(__file__).resolve().parent.parent.parent


def communities_dir() -> Path:
    return project_root() / "communities"


def csv_dir() -> Path:
    return project_root() / "csv"


def logs_dir() -> Path:
    return project_root() / "logs"


def source_archetypes_dir() -> Path:
    return project_root() / "src" / "source-archetypes"

