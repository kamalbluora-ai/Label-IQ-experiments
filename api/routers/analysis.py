from fastapi import APIRouter, BackgroundTasks
from typing import List
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from models import Analysis, AnalysisCreate
from storage import storage

router = APIRouter(tags=["analysis"])


@router.get("/api/projects/{project_id}/analyses", response_model=List[Analysis])
async def list_analyses(project_id: str):
    """List all analyses for a project."""
    return storage.list_analyses(project_id)


@router.post("/api/projects/{project_id}/analyses", response_model=Analysis)
async def run_analysis(project_id: str, data: AnalysisCreate, background_tasks: BackgroundTasks):
    """Start a new analysis for a project."""
    analysis = storage.create_analysis(
        project_id=project_id,
        name=data.name
    )
    
    # Start background task to run real AI-powered analysis
    background_tasks.add_task(storage.run_real_analysis, analysis.id)
    
    return analysis

