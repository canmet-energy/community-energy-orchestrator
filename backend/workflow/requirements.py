import json

from workflow.paths import json_dir


def normalize_community_name(community_name):
    """
    Normalize community name by stripping whitespace and converting to title case.

    Args:
        community_name: Raw community name input

    Returns:
        Normalized community name with proper capitalization

    Examples:
        >>> normalize_community_name("  NORMAN'S BAY  ")
        "Norman's Bay"
        >>> normalize_community_name("ogoki")
        "Ogoki"
    """
    # Strip leading/trailing whitespace
    normalized = community_name.strip()
    # Split by spaces and capitalize first letter of each word
    # This avoids .title() which capitalizes after apostrophes
    words = normalized.split()
    capitalized_words = [word[0].upper() + word[1:].lower() if word else word for word in words]
    normalized = " ".join(capitalized_words)
    return normalized


def _load_communities_json():
    """Load and cache the communities JSON file."""
    json_path = json_dir() / "communities.json"
    if not json_path.exists():
        raise FileNotFoundError(f"Communities JSON not found: {json_path}")

    with open(json_path, encoding="utf-8-sig") as f:
        data = json.load(f)

    # Validate structure
    if "communities" not in data:
        raise ValueError(
            f"Invalid JSON structure in {json_path}. Expected top-level 'communities' key."
        )

    return data


def get_community_requirements(community_name):
    """
    Read housing type requirements from JSON file.

    Args:
        community_name: Name of the community (case-insensitive)

    Returns:
        Dict mapping housing types (e.g., 'pre-2002-single') to required counts.
        Returns {} if community not found (graceful fallback).
    """
    data = _load_communities_json()
    communities = data["communities"]

    # Normalize community name for consistent lookup
    normalized_name = normalize_community_name(community_name)
    community_data = communities.get(normalized_name)

    if not community_data:
        print(f"[INFO] Community '{community_name}' not found in JSON. Using graceful fallback.")
        return {}

    return community_data.get("housing_requirements", {})


def get_weather_location(community_name):
    """
    Look up weather location from JSON.

    Args:
        community_name: Name of the community (case-insensitive)

    Returns:
        Weather location string, or empty string if not found
    """
    data = _load_communities_json()
    communities = data["communities"]

    # Normalize community name for consistent lookup
    normalized_name = normalize_community_name(community_name)
    community_data = communities.get(normalized_name)

    if community_data:
        return community_data.get("weather_location", "")
    return ""


def get_all_communities():
    """
    Get metadata for all communities from JSON file.

    Returns:
        List of dicts with keys: name, province_territory, population,
        total_houses, hdd, weather_location
    """
    data = _load_communities_json()
    communities_data = data["communities"]

    communities = []

    for name, community_data in communities_data.items():
        # Calculate total houses from housing requirements
        total_houses = sum(community_data.get("housing_requirements", {}).values())

        communities.append(
            {
                "name": name,
                "province_territory": community_data.get("province_territory"),
                "population": community_data.get("population"),
                "total_houses": total_houses if total_houses > 0 else None,
                "hdd": community_data.get("hdd"),
                "weather_location": community_data.get("weather_location"),
            }
        )

    return communities


def get_community_info(community_name):
    """
    Get metadata for a single community from JSON file.

    Args:
        community_name: Name of the community (case-insensitive)

    Returns:
        Dict with keys: name, province_territory, population,
        total_houses, hdd, weather_location, housing_distribution.
        Returns None if community not found.
    """
    data = _load_communities_json()
    communities = data["communities"]

    # Normalize community name for consistent lookup
    normalized_name = normalize_community_name(community_name)
    community_data = communities.get(normalized_name)

    if not community_data:
        return None

    housing_requirements = community_data.get("housing_requirements", {})
    total_houses = sum(housing_requirements.values())

    return {
        "name": normalized_name,
        "province_territory": community_data.get("province_territory"),
        "population": community_data.get("population"),
        "total_houses": total_houses if total_houses > 0 else None,
        "hdd": community_data.get("hdd"),
        "weather_location": community_data.get("weather_location"),
        "housing_distribution": housing_requirements,
    }


def get_weather_region(location):
    """
    Get region information for a weather location.

    Args:
        location: Weather location name (e.g., "OLD CROW")

    Returns:
        Dict with keys: code, english, french
        Returns None if location not found.
    """
    data = _load_communities_json()
    weather_regions = data.get("weather_regions", {})
    return weather_regions.get(location.upper())
