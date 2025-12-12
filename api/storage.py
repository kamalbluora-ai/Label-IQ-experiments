"""
In-memory storage with seed data for testing.
"""
from typing import Dict, List, Optional
from datetime import datetime, timedelta
import asyncio
import random
from models import Project, ProjectFile, Analysis, User


class Storage:
    def __init__(self):
        self.users: Dict[str, User] = {}
        self.projects: Dict[str, Project] = {}
        self.files: Dict[str, ProjectFile] = {}
        self.analyses: Dict[str, Analysis] = {}
        self._seed_data()

    def _seed_data(self):
        """Seed with sample data for immediate testing."""
        # Create sample projects
        project1 = Project(
            id="proj-1",
            name="Maple Syrup Label Review",
            description="Compliance review for Grade A maple syrup products for Canadian market",
            tags=["maple", "grade-a", "organic"],
            createdAt=(datetime.now() - timedelta(days=5)).isoformat()
        )
        project2 = Project(
            id="proj-2",
            name="Organic Honey Labels",
            description="Review multi-language honey product labels for CFIA compliance",
            tags=["honey", "bilingual", "organic"],
            createdAt=(datetime.now() - timedelta(days=2)).isoformat()
        )
        self.projects[project1.id] = project1
        self.projects[project2.id] = project2

        # Create sample files for project 1
        file1 = ProjectFile(
            id="file-1",
            name="maple_syrup_front.jpg",
            type="image",
            url="https://placehold.co/400x600/2a2a2a/ffffff?text=Maple+Syrup+Front",
            tags=["front"],
            projectId="proj-1"
        )
        file2 = ProjectFile(
            id="file-2",
            name="maple_syrup_back.jpg",
            type="image",
            url="https://placehold.co/400x600/2a2a2a/ffffff?text=Maple+Syrup+Back",
            tags=["back"],
            projectId="proj-1"
        )
        self.files[file1.id] = file1
        self.files[file2.id] = file2

        # Create a completed analysis for project 1
        analysis1 = Analysis(
            id="analysis-1",
            name="Food Labelling Analysis #1",
            status="completed",
            progress=100,
            resultSummary="All labelling requirements met. Minor recommendation: Consider increasing font size for allergen warnings.",
            details={
                "bilingual_compliance": "Pass",
                "net_quantity": "Pass",
                "ingredients_list": "Pass",
                "nutrition_facts": "Pass",
                "allergens": "Minor Issue"
            },
            createdAt=(datetime.now() - timedelta(hours=2)).isoformat(),
            projectId="proj-1"
        )
        self.analyses[analysis1.id] = analysis1

    # User methods
    def get_mock_user(self) -> User:
        return User(
            id="user-1",
            name="Demo User",
            email="demo@bluora.ai",
            avatar="https://api.dicebear.com/7.x/avataaars/svg?seed=demo"
        )

    # Project methods
    def list_projects(self) -> List[Project]:
        return list(self.projects.values())

    def get_project(self, project_id: str) -> Optional[Project]:
        return self.projects.get(project_id)

    def create_project(self, name: str, description: Optional[str], tags: List[str]) -> Project:
        project = Project(name=name, description=description, tags=tags)
        self.projects[project.id] = project
        return project

    def update_project(self, project_id: str, name: Optional[str], description: Optional[str], tags: Optional[List[str]]) -> Optional[Project]:
        project = self.projects.get(project_id)
        if not project:
            return None
        if name is not None:
            project.name = name
        if description is not None:
            project.description = description
        if tags is not None:
            project.tags = tags
        return project

    def delete_project(self, project_id: str) -> bool:
        if project_id in self.projects:
            del self.projects[project_id]
            # Also delete associated files and analyses
            self.files = {k: v for k, v in self.files.items() if v.projectId != project_id}
            self.analyses = {k: v for k, v in self.analyses.items() if v.projectId != project_id}
            return True
        return False

    # File methods
    def list_files(self, project_id: str) -> List[ProjectFile]:
        return [f for f in self.files.values() if f.projectId == project_id]

    def create_file(self, project_id: str, name: str, file_type: str, url: str, tags: List[str]) -> ProjectFile:
        file = ProjectFile(
            name=name,
            type=file_type,
            url=url,
            tags=tags,
            projectId=project_id
        )
        self.files[file.id] = file
        return file

    def delete_file(self, file_id: str) -> bool:
        if file_id in self.files:
            del self.files[file_id]
            return True
        return False

    # Analysis methods
    def list_analyses(self, project_id: str) -> List[Analysis]:
        return [a for a in self.analyses.values() if a.projectId == project_id]

    def create_analysis(self, project_id: str, name: str) -> Analysis:
        analysis = Analysis(
            name=name,
            status="running",
            progress=0,
            projectId=project_id
        )
        self.analyses[analysis.id] = analysis
        return analysis

    async def simulate_analysis_progress(self, analysis_id: str):
        """Simulate analysis progress in the background."""
        analysis = self.analyses.get(analysis_id)
        if not analysis:
            return
        
        # Simulate progress over ~10 seconds
        for i in range(10):
            await asyncio.sleep(1)
            if analysis_id not in self.analyses:
                return  # Analysis was deleted
            analysis.progress = min(100, (i + 1) * 10)
            if analysis.progress >= 100:
                analysis.status = "completed"
                analysis.resultSummary = "Analysis completed successfully. All labelling requirements verified."
                analysis.details = {
                    "bilingual_compliance": "Pass",
                    "net_quantity": "Pass",
                    "ingredients_list": "Pass",
                    "nutrition_facts": "Pass",
                    "country_of_origin": "Pass"
                }


# Global storage instance
storage = Storage()
