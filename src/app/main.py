"""Community Energy Orchestrator API.

This module exposes a small REST API for running the community workflow in
background and polling for status.

How to run:
    python -m uvicorn src.app.main:app

Key behavior:
    - Single-run-at-a-time: this API enforces at most one active run per process.
    - In-memory state: run state is stored in-process (cleared on restart).
    - Not multi-worker safe: if you run multiple Uvicorn workers/processes, each
        process will have its own run state. Keep workers=1 unless you externalize
        state.

Endpoints:
    - GET  /health
    - GET  /runs
    - POST /runs
    - GET  /runs/current
    - GET  /runs/{run_id}
    - GET  /runs/{run_id}/analysis-md
"""

import re
import threading
from pathlib import Path
from typing import Dict, Literal, Optional
from uuid import uuid4

from fastapi import BackgroundTasks, FastAPI, HTTPException
from pydantic import BaseModel

from workflow.service import run_community_workflow
from workflow.core import communities_dir

app = FastAPI(
    title="Community Energy Orchestrator API",
    description=(
        "Run the community workflow in background and poll for status/results. "
        "See /docs for interactive Swagger UI."
    ),
    version="0.1.0",
)
RunState = Literal["queued", "running", "completed", "failed"]

class RunRequest(BaseModel):
    """Request body for creating a new run."""

    community_name: str


class RunRecord(BaseModel):
    """A single workflow run and its current state."""

    run_id: str
    community_name: str
    status: RunState
    error: Optional[str] = None


class HealthResponse(BaseModel):
    status: str

_runs: Dict[str, dict] = {}

_lock = threading.Lock()

_current_run_id: Optional[str] = None

def _run_workflow(run_id: str, community_name: str) -> None:
    """Worker executed in the background.

    Updates the in-memory run record with status transitions:
    queued -> running -> completed|failed.
    """

    global _current_run_id

    with _lock:
        _runs[run_id]["status"] = "running"

    try: 
        run_community_workflow(community_name)
    
        with _lock:
            _runs[run_id]["status"] = "completed"

    except Exception as e:
        with _lock:
            _runs[run_id]["status"] = "failed"
            _runs[run_id]["error"] = str(e)
    
    finally:
        with _lock:
            _current_run_id = None


@app.get(
    "/health",
    response_model=HealthResponse,
    summary="Health check",
    description="Simple liveness endpoint.",
)
def health():
    return {"status": "ok"}

@app.post(
    "/runs",
    response_model=RunRecord,
    summary="Create a run",
    description=(
        "Starts a new workflow run in the background. "
        "If another run is active, returns 409."
    ),
)
def create_run(req: RunRequest, background_tasks: BackgroundTasks):
    global _current_run_id

    # Validate community name is not empty or malformed
    if not req.community_name or not req.community_name.strip():
        raise HTTPException(status_code=400, detail="Community name cannot be empty.")
    
    # Validate no path traversal or dangerous characters
    if re.search(r'[/\\<>:"|?*\x00-\x1f]', req.community_name):
        raise HTTPException(
            status_code=400, 
            detail="Community name contains invalid characters."
        )

    with _lock:
        if _current_run_id is not None and _runs.get(_current_run_id, {}).get("status") in ("queued", "running"):
            raise HTTPException(status_code=409, detail="Another run is already in progress.")
        
        run_id = str(uuid4())
        _runs[run_id] = {
            "run_id": run_id,
            "community_name": req.community_name,
            "status": "queued",
            "error": None}
        
        _current_run_id = run_id

        background_tasks.add_task(_run_workflow, run_id, req.community_name)

        return _runs[run_id]
    
@app.get(
    "/runs",
    response_model=Dict[str, RunRecord],
    summary="List all runs",
    description=(
        "Returns a dictionary of all runs by run ID."
    ),
)
def get_all_runs():
    with _lock:
        return _runs
    
    
@app.get(
    "/runs/current",
    summary="Get current run",
    description=(
        "Returns the currently-active run (if any). "
        "If idle, returns {'current_run_id': null}."
    ),
)
def get_current_run():
    with _lock:
        if _current_run_id is None:
            return {"current_run_id": None}
        
        return _runs[_current_run_id]


@app.get(
    "/runs/{run_id}",
    response_model=RunRecord,
    summary="Get run status",
    description="Fetches the status and metadata for a specific run.",
)
def get_run(run_id: str):
    with _lock:
        run = _runs.get(run_id)
        if run is None:
            raise HTTPException(status_code=404, detail="Run not found.")
        return run
    
@app.get(
    "/runs/{run_id}/analysis-md",
    summary="Get analysis markdown",
    description=(
        "Returns the generated analysis markdown for a completed run. "
        "If the file is not present yet, returns 404."
    ),
)
def get_run_analysis_md(run_id: str):
    with _lock:
        run = _runs.get(run_id)
        if run is None:
            raise HTTPException(status_code=404, detail="Run not found.")
        community_name = run["community_name"]
    
    analysis_md_path = communities_dir() / community_name / "analysis" / f'{community_name}_analysis.md'
    if not analysis_md_path.exists():
        raise HTTPException(status_code=404, detail="Analysis markdown file not found.")
    
    return {
        "community_name": community_name,
        "path": str(analysis_md_path),
        "markdown": analysis_md_path.read_text(encoding="utf-8", errors="replace")}