"""Energy analysis workflow package.

This package provides tools for:
- Processing housing archetypes
- Running energy simulations
- Generating community-level energy analysis

Public API:
    run_community_workflow: Execute workflow for a community

Internal modules should be imported directly:
    from workflow.config import ...
    from workflow.core import ...
    from workflow.requirements import ...
"""

from workflow.service import run_community_workflow

__all__ = ["run_community_workflow"]
