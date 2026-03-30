import csv

import pandas as pd

from workflow.core import csv_dir, logs_dir


def get_community_requirements(community_name):
    """
    Read housing type requirements from CSV file.

    Args:
        community_name: Name of the community

    Returns:
        Dict mapping housing types (e.g., 'pre-2000-single') to required counts.
        Returns {} if community not found (graceful fallback).
    """
    comm_upper = community_name.upper()
    csv_path = csv_dir() / "communities-number-of-houses.csv"

    if not csv_path.exists():
        raise FileNotFoundError(f"Requirements CSV not found: {csv_path}")

    df = pd.read_csv(csv_path, header=None, encoding="utf-8-sig")
    # Find the row where the first column matches (case-insensitive)
    mask = df[0].astype(str).str.strip().str.upper() == comm_upper
    if not mask.any():
        print(
            f"[INFO] Community '{community_name}' not found in requirements CSV. Using graceful fallback."
        )
        return {}
    row = df[mask].iloc[0].tolist()
    # Skip the first column (community name) and last 2 columns (Province/Territory and Population)
    kv_pairs = row[1:-2] if len(row) > 3 else row[1:]
    requirements = {}

    # Validate we have pairs
    if len(kv_pairs) % 2 != 0:
        print(f"[WARNING] Odd number of values in CSV row for {community_name}")

    # Parse as key-value pairs
    for i in range(0, len(kv_pairs) - 1, 2):
        key = kv_pairs[i]
        val = kv_pairs[i + 1]

        # Only process valid string keys with hyphens
        if not isinstance(key, str) or "-" not in key:
            continue

        # Extract era and type using known patterns
        era = None
        btype = None

        for era_opt in ["pre-2000", "2001-2015", "post-2016"]:
            if era_opt in key:
                era = era_opt
                break

        for type_opt in ["single", "semi", "row-mid", "row-end"]:
            if type_opt in key:
                btype = type_opt
                break

        # Only add if we successfully identified both era and type
        if era and btype:
            try:
                count = int(val)
                requirements[f"{era}-{btype}"] = count
            except (ValueError, TypeError):
                print(f"[WARNING] Invalid count for {key}: {val}")
    # Write requirements to debug log for inspection
    debug_log_path = logs_dir() / "archetype_copy_debug.log"
    debug_log_path.parent.mkdir(parents=True, exist_ok=True)
    with open(debug_log_path, "a", encoding="utf-8") as debug_log:
        debug_log.write(f"[DEBUG] Extracted requirements for {community_name}: {requirements}\n")
    return requirements


def get_weather_location(community_name):
    """
    Look up weather location from CSV.

    Args:
        community_name: Name of the community

    Returns:
        Weather location string, or empty string if not found
    """
    csv_path = csv_dir() / "communities-hdd-and-weather-location.csv"

    if not csv_path.exists():
        raise FileNotFoundError(f"Weather locations CSV not found: {csv_path}")

    comm_upper = community_name.upper()
    try:
        with open(csv_path, newline="", encoding="utf-8-sig") as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                if row["Community"].strip().upper() == comm_upper:
                    return row["WEATHER"].strip()
    except UnicodeDecodeError:
        with open(csv_path, newline="", encoding="utf-8") as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                if row["Community"].strip().upper() == comm_upper:
                    return row["WEATHER"].strip()
    return ""


def get_all_communities():
    """
    Get metadata for all communities from CSV files.

    Returns:
        List of dicts with keys: name, province_territory, population,
        total_houses, hdd, weather_location
    """
    houses_csv = csv_dir() / "communities-number-of-houses.csv"
    weather_csv = csv_dir() / "communities-hdd-and-weather-location.csv"

    if not houses_csv.exists():
        raise FileNotFoundError(f"Housing data CSV not found: {houses_csv}")
    if not weather_csv.exists():
        raise FileNotFoundError(f"Weather data CSV not found: {weather_csv}")

    # Read housing data (no header row, first row is header labels)
    houses_df = pd.read_csv(houses_csv, header=None, encoding="utf-8-sig")

    # Read weather data (has header row)
    weather_df = pd.read_csv(weather_csv, encoding="utf-8-sig")

    communities = []

    # Process each community from housing CSV (skip header row at index 0)
    for idx in range(1, len(houses_df)):
        row = houses_df.iloc[idx]

        community_name = row[0]
        if pd.isna(community_name) or not str(community_name).strip():
            continue

        # Extract province/territory and population from last 2 columns
        province_territory = row.iloc[-2] if len(row) > 1 else None
        population = row.iloc[-1] if len(row) > 0 else None

        # Calculate total houses from housing type counts
        # Format: community, type1, count1, type2, count2, ..., P/T, Population
        # Skip first column (name) and last 2 columns (P/T, Population)
        housing_values = row[1:-2]
        total_houses = 0

        # Every odd index (1, 3, 5...) is a count
        for i in range(1, len(housing_values), 2):
            try:
                total_houses += int(housing_values.iloc[i])
            except (ValueError, TypeError, IndexError):
                pass

        # Look up weather data (case-insensitive match)
        weather_row = weather_df[
            weather_df["Community"].str.strip().str.upper() == str(community_name).strip().upper()
        ]

        hdd = None
        weather_location = None

        if not weather_row.empty:
            hdd_val = weather_row.iloc[0].get("HDD")
            weather_val = weather_row.iloc[0].get("WEATHER")

            try:
                hdd = int(hdd_val) if pd.notna(hdd_val) else None
            except (ValueError, TypeError):
                pass

            weather_location = str(weather_val).strip() if pd.notna(weather_val) else None

        # Convert population to int if possible
        pop_int = None
        try:
            if pd.notna(population):
                pop_int = int(float(population))  # type: ignore[arg-type]
        except (ValueError, TypeError):
            pass

        # Convert province/territory to string
        pt_str = str(province_territory).strip() if pd.notna(province_territory) else "Unknown"

        communities.append(
            {
                "name": str(community_name).strip(),
                "province_territory": pt_str,
                "population": pop_int,
                "total_houses": total_houses if total_houses > 0 else None,
                "hdd": hdd,
                "weather_location": weather_location,
            }
        )

    return communities


def get_community_info(community_name):
    """
    Get metadata for a single community from CSV files.

    Reuses :func:`get_all_communities` for base metadata and
    :func:`get_community_requirements` for the housing distribution.

    Args:
        community_name: Name of the community

    Returns:
        Dict with keys: name, province_territory, population,
        total_houses, hdd, weather_location, housing_distribution.
        Returns None if community not found.
    """
    comm_upper = community_name.upper()
    all_communities = get_all_communities()
    match = next(
        (c for c in all_communities if c["name"].upper() == comm_upper),
        None,
    )
    if match is None:
        return None

    # Add housing distribution from requirements (already parsed by type)
    requirements = get_community_requirements(community_name)
    match["housing_distribution"] = requirements if requirements else {}
    return match
