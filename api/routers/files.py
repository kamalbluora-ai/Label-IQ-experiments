from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from typing import List
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from models import ProjectFile
from storage import storage
import base64

router = APIRouter(tags=["files"])


@router.get("/api/projects/{project_id}/files", response_model=List[ProjectFile])
async def list_files(project_id: str):
    """List all files for a project."""
    return storage.list_files(project_id)


@router.post("/api/projects/{project_id}/files", response_model=ProjectFile)
async def upload_file(
    project_id: str,
    file: UploadFile = File(...),
    tags: str = Form(default="")
):
    """Upload a file to a project."""
    # For demo purposes, create a data URL or use placeholder
    content = await file.read()
    
    # Determine file type
    file_type = "image" if file.content_type and file.content_type.startswith("image/") else "file"
    
    # Create a data URL for images (for demo - in production you'd use cloud storage)
    if file_type == "image" and len(content) < 5_000_000:  # Only encode if < 5MB
        base64_content = base64.b64encode(content).decode("utf-8")
        url = f"data:{file.content_type};base64,{base64_content}"
    else:
        # Use a placeholder for larger files or non-images
        url = f"https://placehold.co/400x400/2a2a2a/ffffff?text={file.filename}"
    
    # Parse tags
    tag_list = [t.strip() for t in tags.split(",") if t.strip()]
    
    project_file = storage.create_file(
        project_id=project_id,
        name=file.filename or "unnamed",
        file_type=file_type,
        url=url,
        tags=tag_list
    )
    return project_file


@router.delete("/api/files/{file_id}")
async def delete_file(file_id: str):
    """Delete a file."""
    success = storage.delete_file(file_id)
    if not success:
        raise HTTPException(status_code=404, detail="File not found")
    return {"message": "File deleted"}
