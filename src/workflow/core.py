


from pathlib import Path
import os

# Constants
KBTU_TO_GJ = 0.001055056
EXPECTED_ROWS = 8761

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

