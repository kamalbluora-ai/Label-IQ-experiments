from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
import uuid


def generate_id() -> str:
    return str(uuid.uuid4())


class User(BaseModel):
    id: str = Field(default_factory=generate_id)
    name: str
    email: str
    avatar: Optional[str] = None


class ProjectCreate(BaseModel):
    name: str
    description: Optional[str] = None
    tags: List[str] = []


class ProjectUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    tags: Optional[List[str]] = None


class Project(BaseModel):
    id: str = Field(default_factory=generate_id)
    name: str
    description: Optional[str] = None
    tags: List[str] = []
    createdAt: str = Field(default_factory=lambda: datetime.now().isoformat())


class ProjectFile(BaseModel):
    id: str = Field(default_factory=generate_id)
    name: str
    type: str  # "image" or "file"
    url: str
    tags: List[str] = []
    projectId: str


class AnalysisCreate(BaseModel):
    name: str


class Analysis(BaseModel):
    id: str = Field(default_factory=generate_id)
    name: str
    status: str = "pending"  # "pending", "running", "completed", "failed"
    progress: int = 0
    resultSummary: Optional[str] = None
    details: Optional[Dict[str, Any]] = None
    createdAt: str = Field(default_factory=lambda: datetime.now().isoformat())
    projectId: str
