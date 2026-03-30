"""Configuration management for the workflow."""

import os
from typing import Any

# Conversion constants
# Primary units: GJ (gigajoules) for energy values
KBTU_TO_GJ = 0.00105505585  # 1 kBtu = 0.001055... GJ
KWH_TO_GJ = 0.0036  # 1 kWh = 0.0036 GJ
GJ_TO_KW = 277.778  # 1 GJ/hour = 277.778 kW (for hourly power values)
EXPECTED_ROWS = 8760  # 365 days × 24 hours/day

# ---------------------------------------------------------------------------
# Energy analysis categories
# ---------------------------------------------------------------------------
# Each category defines which CSV columns to extract and how to convert them.
# - "load": Optional thermal load column (only meaningful for heating).
# - "sources": Fuel-type breakdown. Each source has:
#       "output_col" – column name in the community-total CSV
#       "csv_cols"   – list of *fallback groups*.  Each element is either a
#                      plain string (single column) or a list of alternative
#                      column names for the same measurement (first match wins).
#                      Different groups are summed (e.g. wood-cord + wood-pellets).
#       "unit"       – "kWh" or "kBtu"
#       "additive_cols" (optional) – extra CSV columns to ADD to the value
# - "total_col": Name of the summed column in the community-total CSV.
#
# Adding a new category (e.g. "hot_water") only requires a new entry here;
# read_timeseries, aggregation, and output logic all adapt automatically.
# ---------------------------------------------------------------------------
ENERGY_CATEGORIES: dict[str, dict[str, Any]] = {
    "heating": {
        "label": "Heating",
        "load": {
            "output_col": "Heating_Load_GJ",
            "csv_col": "Load: Heating: Delivered",
            "unit": "kBtu",
        },
        "sources": {
            "propane": {
                "output_col": "Heating_Propane_GJ",
                "csv_cols": [
                    ["End Use: Propane: Heating", "System Use: HeatingSystem1: Propane: Heating"],
                ],
                "unit": "kBtu",
            },
            "oil": {
                "output_col": "Heating_Oil_GJ",
                "csv_cols": [
                    ["End Use: Fuel Oil: Heating", "System Use: HeatingSystem1: Fuel Oil: Heating"],
                ],
                "unit": "kBtu",
            },
            "electricity": {
                "output_col": "Heating_Electricity_GJ",
                "csv_cols": [
                    [
                        "End Use: Electricity: Heating",
                        "System Use: HeatingSystem1: Electricity: Heating",
                    ],
                ],
                "unit": "kWh",
                "additive_cols": [
                    "End Use: Electricity: Heating Fans/Pumps",
                    "End Use: Electricity: Heating Heat Pump Backup",
                ],
            },
            "natural_gas": {
                "output_col": "Heating_Natural_Gas_GJ",
                "csv_cols": [
                    [
                        "End Use: Natural Gas: Heating",
                        "System Use: HeatingSystem1: Natural Gas: Heating",
                    ],
                ],
                "unit": "kBtu",
            },
            "wood": {
                "output_col": "Heating_Wood_GJ",
                "csv_cols": [
                    [
                        "End Use: Wood Cord: Heating",
                        "System Use: SupplHeatingSystem1: Wood Cord: Heating",
                    ],
                    [
                        "End Use: Wood Pellets: Heating",
                        "System Use: SupplHeatingSystem1: Wood Pellets: Heating",
                    ],
                ],
                "unit": "kBtu",
            },
        },
        "total_col": "Total_Heating_Energy_GJ",
    },
    "total": {
        "label": "Total",
        "load": None,
        "sources": {
            "propane": {
                "output_col": "Total_Propane_GJ",
                "csv_cols": ["Fuel Use: Propane: Total"],
                "unit": "kBtu",
            },
            "oil": {
                "output_col": "Total_Oil_GJ",
                "csv_cols": ["Fuel Use: Fuel Oil: Total"],
                "unit": "kBtu",
            },
            "electricity": {
                "output_col": "Total_Electricity_GJ",
                "csv_cols": ["Fuel Use: Electricity: Total"],
                "unit": "kWh",
            },
            "natural_gas": {
                "output_col": "Total_Natural_Gas_GJ",
                "csv_cols": ["Fuel Use: Natural Gas: Total"],
                "unit": "kBtu",
            },
            "wood": {
                "output_col": "Total_Wood_GJ",
                "csv_cols": [
                    "Fuel Use: Wood Cord: Total",
                    "Fuel Use: Wood Pellets: Total",
                ],
                "unit": "kBtu",
            },
        },
        "total_col": "Total_Energy_GJ",
    },
}

# Archetype patterns for matching housing types
ARCHETYPE_TYPE_PATTERNS = {
    "pre-2000-single": [r"pre-2000-single_.*\.H2K$"],
    "2001-2015-single": [r"2001-2015-single_.*\.H2K$"],
    "post-2016-single": [r"post-2016-single_.*\.H2K$"],
    "pre-2000-semi": [r"pre-2000-semi_.*\.H2K$", r"pre-2000-double_.*\.H2K$"],
    "2001-2015-semi": [r"2001-2015-semi_.*\.H2K$", r"2001-2015-double_.*\.H2K$"],
    "post-2016-semi": [r"post-2016-semi_.*\.H2K$", r"post-2016-double_.*\.H2K$"],
    "pre-2000-row-mid": [r"pre-2000-row-mid_.*\.H2K$", r"pre-2000-row-middle_.*\.H2K$"],
    "2001-2015-row-mid": [r"2001-2015-row-mid_.*\.H2K$", r"2001-2015-row-middle_.*\.H2K$"],
    "post-2016-row-mid": [r"post-2016-row-mid_.*\.H2K$", r"post-2016-row-middle_.*\.H2K$"],
    "pre-2000-row-end": [r"pre-2000-row-end_.*\.H2K$"],
    "2001-2015-row-end": [r"2001-2015-row-end_.*\.H2K$"],
    "post-2016-row-end": [r"post-2016-row-end_.*\.H2K$"],
}


def get_max_workers():
    """
    Calculate optimal worker count for parallel operations.

    Returns:
        int: Number of worker processes to use
    """
    # Allow manual override
    env_workers = os.environ.get("MAX_PARALLEL_WORKERS")
    if env_workers:
        try:
            return max(1, int(env_workers))
        except ValueError:
            pass

    cpu_count = os.cpu_count() or 1

    if cpu_count < 4:
        return 1
    elif cpu_count < 18:
        return int(cpu_count * 0.8)  # Use 80% of available cores
    else:
        return cpu_count - 4  # Reserve 4 cores for other processes


def get_analysis_random_seed():
    """
    Get random seed for deterministic analysis if set.

    Returns:
        int or None: Seed value if ANALYSIS_RANDOM_SEED is set, None otherwise
    """
    seed = os.environ.get("ANALYSIS_RANDOM_SEED")
    return int(seed) if seed else None


def get_archetype_selection_seed():
    """
    Get random seed for deterministic archetype selection if set.

    Returns:
        str or None: Seed value if ARCHETYPE_SELECTION_SEED is set, None otherwise
    """
    return os.environ.get("ARCHETYPE_SELECTION_SEED")
