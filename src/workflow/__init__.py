"""Energy analysis workflow package.

This package provides tools for:
- Processing housing archetypes
- Running energy simulations
- Generating community-level energy analysis

The workflow processes data stored in the communities/ directory.
"""

from .core import (
    get_max_workers,
    KBTU_TO_GJ,
    EXPECTED_ROWS,
    project_root,
    communities_dir,
    csv_dir,
    logs_dir,
    source_archetypes_dir,
)

from .requirements import (
    get_community_requirements,
    get_weather_location,
)

__all__ = [
    "get_max_workers",
    "KBTU_TO_GJ",
    "EXPECTED_ROWS",
    "project_root",
    "communities_dir",
    "csv_dir",
    "logs_dir",
    "source_archetypes_dir",
    "get_community_requirements",
    "get_weather_location",
]
