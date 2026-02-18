"""Public API for workflow operations.

This module provides the public interface for external consumers (API, CLI, etc).
Internal implementation details are kept in other workflow modules.
"""


def run_community_workflow(community_name: str) -> None:
    """
    Execute complete community energy analysis workflow.
    
    Public interface for running the workflow. Decouples external consumers
    from internal implementation details.
    
    Args:
        community_name: Name of the community to process
        
    Raises:
        ValueError: If community is not found in database
        FileNotFoundError: If required CSV files or archetype files are missing
        
    Note:
        Communities with 0 houses will complete successfully without processing.
        
    Example:
        >>> run_community_workflow("Old Crow")
    """
    from workflow.process_community_workflow import main
    main(community_name)
