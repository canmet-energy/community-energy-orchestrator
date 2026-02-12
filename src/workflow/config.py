"""Configuration management for the workflow."""
import os
import re

# Conversion constants
KBTU_TO_GJ = 0.001055056
EXPECTED_ROWS = 8761

# Archetype patterns for matching housing types
ARCHETYPE_TYPE_PATTERNS = {
    'pre-2000-single': [r'pre-2000-single_.*\.H2K$'],
    '2001-2015-single': [r'2001-2015-single_.*\.H2K$'],
    'post-2016-single': [r'post-2016-single_.*\.H2K$'],
    'pre-2000-semi': [r'pre-2000-semi_.*\.H2K$', r'pre-2000-double_.*\.H2K$'],
    '2001-2015-semi': [r'2001-2015-semi_.*\.H2K$', r'2001-2015-double_.*\.H2K$'],
    'post-2016-semi': [r'post-2016-semi_.*\.H2K$', r'post-2016-double_.*\.H2K$'],
    'pre-2000-row-mid': [r'pre-2000-row-mid_.*\.H2K$', r'pre-2000-row-middle_.*\.H2K$'],
    '2001-2015-row-mid': [r'2001-2015-row-mid_.*\.H2K$', r'2001-2015-row-middle_.*\.H2K$'],
    'post-2016-row-mid': [r'post-2016-row-mid_.*\.H2K$', r'post-2016-row-middle_.*\.H2K$'],
    'pre-2000-row-end': [r'pre-2000-row-end_.*\.H2K$'],
    '2001-2015-row-end': [r'2001-2015-row-end_.*\.H2K$'],
    'post-2016-row-end': [r'post-2016-row-end_.*\.H2K$'],
}


def get_max_workers():
    """
    Calculate optimal worker count for parallel operations.
    
    Returns:
        int: Number of worker processes to use
    """
    # Allow manual override
    env_workers = os.environ.get('MAX_PARALLEL_WORKERS')
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
    seed = os.environ.get('ANALYSIS_RANDOM_SEED')
    return int(seed) if seed is not None else None


def get_archetype_selection_seed():
    """
    Get random seed for deterministic archetype selection if set.
    
    Returns:
        str or None: Seed value if ARCHETYPE_SELECTION_SEED is set, None otherwise
    """
    return os.environ.get('ARCHETYPE_SELECTION_SEED')
