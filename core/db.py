import sqlite3
import json
import os
from datetime import datetime, timezone
from typing import Dict, Any, Optional

DB_PATH = os.environ.get("SQLITE_DB_PATH", "label_iq.db")

class DatabaseManager:
    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _sanitize_row(self, row: dict) -> dict:
        """Recursively convert datetime objects to ISO strings."""
        if not row:
            return row
        new_row = {}
        for k, v in row.items():
            if isinstance(v, datetime):
                new_row[k] = v.isoformat()
            elif isinstance(v, dict):
                new_row[k] = self._sanitize_row(v)
            else:
                new_row[k] = v
        return new_row

    def _init_db(self):
        """Initialize the database schema."""
        conn = self._get_connection()
        try:
            cur = conn.cursor()
            
            # Jobs table
            cur.execute("""
            CREATE TABLE IF NOT EXISTS jobs (
                job_id TEXT PRIMARY KEY,
                status TEXT, -- PENDING, PROCESSING, COMPLETED, FAILED
                mode TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            """)

            # DocAI Extractions table
            cur.execute("""
            CREATE TABLE IF NOT EXISTS docai_extractions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                job_id TEXT,
                image_tag TEXT, -- "front", "back", "left_panel", etc.
                raw_json TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(job_id) REFERENCES jobs(job_id)
            );
            """)

            # Label Facts table
            cur.execute("""
            CREATE TABLE IF NOT EXISTS label_facts (
                job_id TEXT PRIMARY KEY,
                merged_facts_json TEXT,
                translated_facts_json TEXT,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(job_id) REFERENCES jobs(job_id)
            );
            """)

            # Compliance Results table
            cur.execute("""
            CREATE TABLE IF NOT EXISTS compliance_results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                job_id TEXT,
                agent_name TEXT,
                status TEXT, -- RUNNING, DONE, ERROR
                result_json TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(job_id) REFERENCES jobs(job_id),
                UNIQUE(job_id, agent_name)
            );
            """)

            # Projects table
            cur.execute("""
            CREATE TABLE IF NOT EXISTS projects (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                description TEXT DEFAULT '',
                tags TEXT DEFAULT '[]',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            """)

            # Analyses table (links projects to jobs)
            cur.execute("""
            CREATE TABLE IF NOT EXISTS analyses (
                id TEXT PRIMARY KEY,
                project_id TEXT NOT NULL,
                name TEXT NOT NULL,
                status TEXT DEFAULT 'running',
                progress INTEGER DEFAULT 0,
                job_id TEXT NOT NULL,
                image_names TEXT DEFAULT '[]',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(project_id) REFERENCES projects(id),
                FOREIGN KEY(job_id) REFERENCES jobs(job_id)
            );
            """)

            conn.commit()
        finally:
            conn.close()

    def create_job(self, job_id: str, status: str = "PENDING", mode: Optional[str] = None):
        """Create a new job record."""
        conn = self._get_connection()
        try:
            cur = conn.cursor()
            cur.execute(
                "INSERT OR REPLACE INTO jobs (job_id, status, mode, updated_at) VALUES (?, ?, ?, ?)",
                (job_id, status, mode, datetime.now(timezone.utc))
            )
            conn.commit()
        finally:
            conn.close()

    def update_job_status(self, job_id: str, status: str, mode: Optional[str] = None):
        """Update job status and optionally mode."""
        conn = self._get_connection()
        try:
            cur = conn.cursor()
            if mode:
                cur.execute(
                    "UPDATE jobs SET status = ?, mode = ?, updated_at = ? WHERE job_id = ?",
                    (status, mode, datetime.now(timezone.utc), job_id)
                )
            else:
                cur.execute(
                    "UPDATE jobs SET status = ?, updated_at = ? WHERE job_id = ?",
                    (status, datetime.now(timezone.utc), job_id)
                )
            conn.commit()
        finally:
            conn.close()

    def add_docai_extraction(self, job_id: str, image_tag: str, raw_json: Dict[str, Any]):
        """Save a raw DocAI extraction result."""
        conn = self._get_connection()
        try:
            cur = conn.cursor()
            cur.execute(
                "INSERT INTO docai_extractions (job_id, image_tag, raw_json) VALUES (?, ?, ?)",
                (job_id, image_tag, json.dumps(raw_json))
            )
            conn.commit()
        finally:
            conn.close()

    def save_merged_facts(self, job_id: str, merged_facts: Dict[str, Any], translated_facts: Optional[Dict[str, Any]] = None):
        """Save the merged (and optionally translated) label facts."""
        conn = self._get_connection()
        try:
            cur = conn.cursor()
            cur.execute(
                """
                INSERT OR REPLACE INTO label_facts (job_id, merged_facts_json, translated_facts_json, updated_at)
                VALUES (?, ?, ?, ?)
                """,
                (
                    job_id, 
                    json.dumps(merged_facts), 
                    json.dumps(translated_facts) if translated_facts else None, 
                    datetime.now(timezone.utc)
                )
            )
            conn.commit()
        finally:
            conn.close()

    def update_compliance_result(self, job_id: str, agent_name: str, status: str, result: Optional[Dict[str, Any]] = None):
        """Update the status and result of a specific compliance agent."""
        conn = self._get_connection()
        try:
            cur = conn.cursor()
            cur.execute(
                """
                INSERT INTO compliance_results (job_id, agent_name, status, result_json, created_at)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(job_id, agent_name) DO UPDATE SET
                    status=excluded.status,
                    result_json=excluded.result_json,
                    created_at=excluded.created_at
                """,
                (
                    job_id, 
                    agent_name, 
                    status, 
                    json.dumps(result) if result else None,
                    datetime.now(timezone.utc)
                )
            )
            conn.commit()
        finally:
            conn.close()

    def get_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve job details."""
        conn = self._get_connection()
        try:
            cur = conn.cursor()
            cur.execute("SELECT * FROM jobs WHERE job_id = ?", (job_id,))
            row = cur.fetchone()
            if row:
                return self._sanitize_row(dict(row))
            return None
        finally:
            conn.close()

    # ===== PROJECT METHODS =====

    def create_project(self, id: str, name: str, description: str = "", tags: list = None) -> Dict[str, Any]:
        """Create a new project."""
        tags_json = json.dumps(tags or [])
        conn = self._get_connection()
        try:
            cur = conn.cursor()
            now = datetime.now(timezone.utc)
            cur.execute(
                """
                INSERT INTO projects (id, name, description, tags, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (id, name, description, tags_json, now, now)
            )
            conn.commit()
            return {
                "id": id,
                "name": name,
                "description": description,
                "tags": tags or [],
                "createdAt": now.isoformat(),
                "updatedAt": now.isoformat()
            }
        finally:
            conn.close()

    def list_projects(self) -> list[Dict[str, Any]]:
        """List all projects."""
        conn = self._get_connection()
        try:
            cur = conn.cursor()
            cur.execute("SELECT * FROM projects ORDER BY created_at DESC")
            rows = cur.fetchall()
            projects = []
            for row in rows:
                row_dict = dict(row)
                projects.append({
                    "id": row_dict["id"],
                    "name": row_dict["name"],
                    "description": row_dict["description"],
                    "tags": json.loads(row_dict["tags"]),
                    "createdAt": row_dict["created_at"],
                    "updatedAt": row_dict["updated_at"]
                })
            return projects
        finally:
            conn.close()

    def get_project(self, id: str) -> Optional[Dict[str, Any]]:
        """Get a single project."""
        conn = self._get_connection()
        try:
            cur = conn.cursor()
            cur.execute("SELECT * FROM projects WHERE id = ?", (id,))
            row = cur.fetchone()
            if not row:
                return None
            row_dict = dict(row)
            return {
                "id": row_dict["id"],
                "name": row_dict["name"],
                "description": row_dict["description"],
                "tags": json.loads(row_dict["tags"]),
                "createdAt": row_dict["created_at"],
                "updatedAt": row_dict["updated_at"]
            }
        finally:
            conn.close()

    def update_project(self, id: str, name: str, description: str, tags: list) -> Dict[str, Any]:
        """Update a project."""
        tags_json = json.dumps(tags)
        conn = self._get_connection()
        try:
            cur = conn.cursor()
            now = datetime.now(timezone.utc)
            cur.execute(
                """
                UPDATE projects SET name = ?, description = ?, tags = ?, updated_at = ?
                WHERE id = ?
                """,
                (name, description, tags_json, now, id)
            )
            conn.commit()
            return self.get_project(id)
        finally:
            conn.close()

    def delete_project(self, id: str):
        """Delete a project and its analyses."""
        conn = self._get_connection()
        try:
            cur = conn.cursor()
            # Delete analyses first (foreign key constraint)
            cur.execute("DELETE FROM analyses WHERE project_id = ?", (id,))
            cur.execute("DELETE FROM projects WHERE id = ?", (id,))
            conn.commit()
        finally:
            conn.close()

    # ===== ANALYSIS METHODS =====

    def create_analysis(self, id: str, project_id: str, name: str, job_id: str, image_names: list = None) -> Dict[str, Any]:
        """Create a new analysis record."""
        image_names_json = json.dumps(image_names or [])
        conn = self._get_connection()
        try:
            cur = conn.cursor()
            now = datetime.now(timezone.utc)
            cur.execute(
                """
                INSERT INTO analyses (id, project_id, name, status, progress, job_id, image_names, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (id, project_id, name, "running", 0, job_id, image_names_json, now)
            )
            conn.commit()
            return {
                "id": id,
                "projectId": project_id,
                "name": name,
                "status": "running",
                "progress": 0,
                "jobId": job_id,
                "createdAt": now.isoformat()
            }
        finally:
            conn.close()

    def list_analyses(self, project_id: str) -> list[Dict[str, Any]]:
        """List all analyses for a project."""
        conn = self._get_connection()
        try:
            cur = conn.cursor()
            cur.execute("SELECT * FROM analyses WHERE project_id = ? ORDER BY created_at DESC", (project_id,))
            rows = cur.fetchall()
            analyses = []
            for row in rows:
                row_dict = dict(row)
                analyses.append({
                    "id": row_dict["id"],
                    "projectId": row_dict["project_id"],
                    "name": row_dict["name"],
                    "status": row_dict["status"],
                    "progress": row_dict["progress"],
                    "jobId": row_dict["job_id"],
                    "createdAt": row_dict["created_at"]
                })
            return analyses
        finally:
            conn.close()

    def update_analysis_status(self, id: str, status: str, progress: int = None):
        """Update analysis status and progress."""
        conn = self._get_connection()
        try:
            cur = conn.cursor()
            if progress is not None:
                cur.execute(
                    "UPDATE analyses SET status = ?, progress = ? WHERE id = ?",
                    (status, progress, id)
                )
            else:
                cur.execute(
                    "UPDATE analyses SET status = ? WHERE id = ?",
                    (status, id)
                )
            conn.commit()
        finally:
            conn.close()
