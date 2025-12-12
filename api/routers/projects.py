from fastapi import APIRouter, HTTPException
from typing import List
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from models import Project, ProjectCreate, ProjectUpdate
from storage import storage

router = APIRouter(prefix="/api/projects", tags=["projects"])


@router.get("", response_model=List[Project])
async def list_projects():
    """List all projects."""
    return storage.list_projects()


@router.post("", response_model=Project)
async def create_project(data: ProjectCreate):
    """Create a new project."""
    project = storage.create_project(
        name=data.name,
        description=data.description,
        tags=data.tags
    )
    return project


@router.get("/{project_id}", response_model=Project)
async def get_project(project_id: str):
    """Get a single project by ID."""
    project = storage.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


@router.put("/{project_id}", response_model=Project)
async def update_project(project_id: str, data: ProjectUpdate):
    """Update an existing project."""
    project = storage.update_project(
        project_id=project_id,
        name=data.name,
        description=data.description,
        tags=data.tags
    )
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


@router.delete("/{project_id}")
async def delete_project(project_id: str):
    """Delete a project and all associated files and analyses."""
    success = storage.delete_project(project_id)
    if not success:
        raise HTTPException(status_code=404, detail="Project not found")
    return {"message": "Project deleted"}
