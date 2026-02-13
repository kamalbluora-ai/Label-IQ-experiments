import psycopg2
from psycopg2.extras import RealDictCursor
import json
import os
from datetime import datetime, timezone
from typing import Dict, Any, Optional

# Cloud SQL connection via environment variables
DB_HOST = os.environ.get("DB_HOST")
DB_PORT = os.environ.get("DB_PORT")
DB_NAME = os.environ.get("DB_NAME")
DB_USER = os.environ.get("DB_USER")
DB_PASSWORD = os.environ.get("DB_PASSWORD")

# Cloud SQL connection via Unix socket (when using Cloud SQL Proxy)
CLOUD_SQL_CONNECTION_NAME = os.environ.get("CLOUD_SQL_CONNECTION_NAME")

from psycopg2 import pool

_pool = None
_db_initialized = False

def _setup_pool():
    global _pool
    if _pool is None:
        if CLOUD_SQL_CONNECTION_NAME:
             # Cloud Run with Cloud SQL Connector
            unix_socket = f"/cloudsql/{CLOUD_SQL_CONNECTION_NAME}"
            _pool = pool.ThreadedConnectionPool(
                minconn=1,
                maxconn=10,
                host=unix_socket,
                database=DB_NAME,
                user=DB_USER,
                password=DB_PASSWORD,
                cursor_factory=RealDictCursor
            )
        else:
             # Direct IP connection (dev/testing)
            _pool = pool.ThreadedConnectionPool(
                minconn=1,
                maxconn=10,
                host=DB_HOST,
                port=DB_PORT,
                database=DB_NAME,
                user=DB_USER,
                password=DB_PASSWORD,
                cursor_factory=RealDictCursor
            )


class DatabaseManager:
    def __init__(self):
        global _db_initialized
        _setup_pool()
        if not _db_initialized:
            self._init_db()
            _db_initialized = True

    def _get_connection(self):
        """Get a PostgreSQL connection from the pool."""
        global _pool
        if _pool is None:
            _setup_pool()
        return _pool.getconn()

    def _release_connection(self, conn):
        """Return a connection to the pool."""
        global _pool
        if _pool and conn:
            _pool.putconn(conn)

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
                status TEXT,
                mode TEXT,
                total_groups INTEGER DEFAULT 3,
                completed_groups INTEGER DEFAULT 0,
                facts_path TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            """)

            # Add columns if they don't exist (for existing tables)
            cur.execute("""
            DO $$
            BEGIN
                IF NOT EXISTS (SELECT 1 FROM information_schema.columns
                            WHERE table_name='jobs' AND column_name='total_groups') THEN
                    ALTER TABLE jobs ADD COLUMN total_groups INTEGER DEFAULT 3;
                END IF;
                IF NOT EXISTS (SELECT 1 FROM information_schema.columns
                            WHERE table_name='jobs' AND column_name='completed_groups') THEN
                    ALTER TABLE jobs ADD COLUMN completed_groups INTEGER DEFAULT 0;
                END IF;
                IF NOT EXISTS (SELECT 1 FROM information_schema.columns
                            WHERE table_name='jobs' AND column_name='facts_path') THEN
                    ALTER TABLE jobs ADD COLUMN facts_path TEXT;
                END IF;
            END $$;
            """)

            # DocAI Extractions table
            cur.execute("""
            CREATE TABLE IF NOT EXISTS docai_extractions (
                id SERIAL PRIMARY KEY,
                job_id TEXT,
                image_tag TEXT,
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
                id SERIAL PRIMARY KEY,
                job_id TEXT,
                agent_name TEXT,
                status TEXT,
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
            self._release_connection(conn)

    def create_job(self, job_id: str, status: str = "PENDING", mode: Optional[str] = None):
        """Create a new job record."""
        conn = self._get_connection()
        try:
            cur = conn.cursor()
            cur.execute(
                """
                INSERT INTO jobs (job_id, status, mode, updated_at)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (job_id) DO UPDATE SET
                    status = EXCLUDED.status,
                    mode = EXCLUDED.mode,
                    updated_at = EXCLUDED.updated_at
                """,
                (job_id, status, mode, datetime.now(timezone.utc))
            )
            conn.commit()
        finally:
            self._release_connection(conn)

    def claim_job_processing(self, job_id: str, mode: Optional[str] = None) -> bool:
        """Atomically claim a job for processing. Returns True only for the winner."""
        conn = self._get_connection()
        try:
            cur = conn.cursor()
            now = datetime.now(timezone.utc)

            cur.execute(
                """
                INSERT INTO jobs (job_id, status, mode, updated_at)
                VALUES (%s, 'PENDING', %s, %s)
                ON CONFLICT (job_id) DO NOTHING
                """,
                (job_id, mode, now)
            )

            cur.execute(
                """
                UPDATE jobs
                SET status = 'EXTRACTING',
                    mode = COALESCE(%s, mode),
                    updated_at = %s
                WHERE job_id = %s
                  AND status IN ('PENDING', 'QUEUED')
                RETURNING job_id
                """,
                (mode, now, job_id)
            )

            claimed = cur.fetchone() is not None
            conn.commit()
            return claimed
        finally:
            self._release_connection(conn)

    def update_job_status(self, job_id: str, status: str, mode: Optional[str] = None, facts_path: Optional[str] = None):
        """Update job status and optionally mode and facts_path."""
        conn = self._get_connection()
        try:
            cur = conn.cursor()
            cur.execute(
                """
                UPDATE jobs 
                SET status = %s, 
                    mode = COALESCE(%s, mode), 
                    facts_path = COALESCE(%s, facts_path),
                    updated_at = %s
                WHERE job_id = %s
                """,
                (status, mode, facts_path, datetime.now(timezone.utc), job_id)
            )
            conn.commit()
        finally:
            self._release_connection(conn)

    def add_docai_extraction(self, job_id: str, image_tag: str, raw_json: Dict[str, Any]):
        """Save a raw DocAI extraction result."""
        conn = self._get_connection()
        try:
            cur = conn.cursor()
            cur.execute(
                "INSERT INTO docai_extractions (job_id, image_tag, raw_json) VALUES (%s, %s, %s)",
                (job_id, image_tag, json.dumps(raw_json))
            )
            conn.commit()
        finally:
            self._release_connection(conn)

    def save_merged_facts(self, job_id: str, merged_facts: Dict[str, Any], translated_facts: Optional[Dict[str, Any]] = None):
        """Save the merged (and optionally translated) label facts."""
        conn = self._get_connection()
        try:
            cur = conn.cursor()
            cur.execute(
                """
                INSERT INTO label_facts (job_id, merged_facts_json, translated_facts_json, updated_at)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (job_id) DO UPDATE SET
                    merged_facts_json = EXCLUDED.merged_facts_json,
                    translated_facts_json = EXCLUDED.translated_facts_json,
                    updated_at = EXCLUDED.updated_at
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
            self._release_connection(conn)

    def update_compliance_result(self, job_id: str, agent_name: str, status: str, result: Optional[Dict[str, Any]] = None):
        """Update the status and result of a specific compliance agent."""
        conn = self._get_connection()
        try:
            cur = conn.cursor()
            cur.execute(
                """
                INSERT INTO compliance_results (job_id, agent_name, status, result_json, created_at)
                VALUES (%s, %s, %s, %s, %s)
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
            self._release_connection(conn)

    def get_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve job details."""
        conn = self._get_connection()
        try:
            cur = conn.cursor()
            cur.execute("SELECT * FROM jobs WHERE job_id = %s", (job_id,))
            row = cur.fetchone()
            if row:
                return self._sanitize_row(dict(row))
            return None
        finally:
            self._release_connection(conn)

    def increment_completed_groups(self, job_id: str) -> tuple[int, int]:
        """Atomically increment completed_groups. Returns (completed, total)."""
        conn = self._get_connection()
        try:
            cur = conn.cursor()
            cur.execute(
                """
                UPDATE jobs
                SET completed_groups = completed_groups + 1,
                    updated_at = %s
                WHERE job_id = %s
                RETURNING completed_groups, total_groups
                """,
                (datetime.now(timezone.utc), job_id)
            )
            row = cur.fetchone()
            conn.commit()
            if row:
                r = dict(row)
                return r["completed_groups"], r["total_groups"]
            return 0, 3
        finally:
            self._release_connection(conn)

    def get_job_status(self, job_id: str) -> Optional[str]:
        """Get current status for a job."""
        conn = self._get_connection()
        try:
            cur = conn.cursor()
            cur.execute("SELECT status FROM jobs WHERE job_id = %s", (job_id,))
            row = cur.fetchone()
            if not row:
                return None
            return dict(row).get("status")
        finally:
            self._release_connection(conn)

    def has_group_done_marker(self, job_id: str, group: str) -> bool:
        """Check whether a group-done marker already exists for a job/group."""
        conn = self._get_connection()
        try:
            cur = conn.cursor()
            marker = f"__group_done__:{group}"
            cur.execute(
                """
                SELECT 1
                FROM compliance_results
                WHERE job_id = %s AND agent_name = %s
                LIMIT 1
                """,
                (job_id, marker)
            )
            return cur.fetchone() is not None
        finally:
            self._release_connection(conn)

    def claim_group_execution(self, job_id: str, group: str) -> bool:
        """Atomically claim execution for a job/group. Returns True only once."""
        conn = self._get_connection()
        try:
            cur = conn.cursor()
            marker = f"__group_exec__:{group}"
            now = datetime.now(timezone.utc)
            cur.execute(
                """
                INSERT INTO compliance_results (job_id, agent_name, status, result_json, created_at)
                VALUES (%s, %s, 'RUNNING', %s, %s)
                ON CONFLICT(job_id, agent_name) DO NOTHING
                """,
                (job_id, marker, json.dumps({"group": group, "dedupe_marker": True}), now)
            )
            claimed = cur.rowcount > 0
            conn.commit()
            return claimed
        finally:
            self._release_connection(conn)

    def release_group_execution_claim(self, job_id: str, group: str):
        """Release execution claim for a job/group (used when execution fails)."""
        conn = self._get_connection()
        try:
            cur = conn.cursor()
            marker = f"__group_exec__:{group}"
            cur.execute(
                """
                DELETE FROM compliance_results
                WHERE job_id = %s AND agent_name = %s AND status = 'RUNNING'
                """,
                (job_id, marker)
            )
            conn.commit()
        finally:
            self._release_connection(conn)

    def increment_completed_groups_if_pending(self, job_id: str, group: str) -> tuple[int, int, bool]:
        """
        Increment completed_groups only once per group.
        Returns (completed, total, incremented).
        """
        conn = self._get_connection()
        try:
            cur = conn.cursor()
            marker = f"__group_done__:{group}"
            now = datetime.now(timezone.utc)

            cur.execute(
                """
                INSERT INTO compliance_results (job_id, agent_name, status, result_json, created_at)
                VALUES (%s, %s, 'DONE', %s, %s)
                ON CONFLICT(job_id, agent_name) DO NOTHING
                """,
                (job_id, marker, json.dumps({"group": group, "dedupe_marker": True}), now)
            )
            inserted = cur.rowcount > 0

            if inserted:
                cur.execute(
                    """
                    UPDATE jobs
                    SET completed_groups = completed_groups + 1,
                        updated_at = %s
                    WHERE job_id = %s
                    RETURNING completed_groups, total_groups
                    """,
                    (now, job_id)
                )
                row = cur.fetchone()
                conn.commit()
                if row:
                    r = dict(row)
                    return r["completed_groups"], r["total_groups"], True
                return 0, 3, True

            cur.execute(
                "SELECT completed_groups, total_groups FROM jobs WHERE job_id = %s",
                (job_id,)
            )
            row = cur.fetchone()
            conn.commit()
            if row:
                r = dict(row)
                return r["completed_groups"], r["total_groups"], False
            return 0, 3, False
        finally:
            self._release_connection(conn)

    def claim_report_finalize(self, job_id: str) -> bool:
        """Atomically claim final report assembly for a job. Returns True only once."""
        conn = self._get_connection()
        try:
            cur = conn.cursor()
            now = datetime.now(timezone.utc)
            cur.execute(
                """
                UPDATE jobs
                SET status = 'FINALIZING',
                    updated_at = %s
                WHERE job_id = %s
                  AND status <> 'DONE'
                  AND status <> 'FINALIZING'
                RETURNING job_id
                """,
                (now, job_id)
            )
            claimed = cur.fetchone() is not None
            conn.commit()
            return claimed
        finally:
            self._release_connection(conn)

    def release_report_finalize_claim(self, job_id: str):
        """Release FINALIZING status back to PROCESSING if report assembly fails."""
        conn = self._get_connection()
        try:
            cur = conn.cursor()
            now = datetime.now(timezone.utc)
            cur.execute(
                """
                UPDATE jobs
                SET status = 'PROCESSING',
                    updated_at = %s
                WHERE job_id = %s
                  AND status = 'FINALIZING'
                """,
                (now, job_id)
            )
            conn.commit()
        finally:
            self._release_connection(conn)

    def get_all_compliance_results(self, job_id: str) -> Dict[str, Any]:
        """Get all compliance results for a job, keyed by agent_name."""
        conn = self._get_connection()
        try:
            cur = conn.cursor()
            cur.execute(
                                """
                                SELECT agent_name, result_json
                                FROM compliance_results
                                WHERE job_id = %s
                                    AND status = 'DONE'
                                    AND agent_name NOT LIKE '\\_\\_group\\_%' ESCAPE '\\'
                                """,
                (job_id,)
            )
            rows = cur.fetchall()
            results = {}
            for row in rows:
                r = dict(row)
                agent_name = r["agent_name"]
                result_json = r["result_json"]
                if result_json:
                    results[agent_name] = json.loads(result_json)
            return results
        finally:
            self._release_connection(conn)

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
                VALUES (%s, %s, %s, %s, %s, %s)
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
            self._release_connection(conn)

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
            self._release_connection(conn)

    def get_project(self, id: str) -> Optional[Dict[str, Any]]:
        """Get a single project."""
        conn = self._get_connection()
        try:
            cur = conn.cursor()
            cur.execute("SELECT * FROM projects WHERE id = %s", (id,))
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
            self._release_connection(conn)

    def update_project(self, id: str, name: str, description: str, tags: list) -> Dict[str, Any]:
        """Update a project."""
        tags_json = json.dumps(tags)
        conn = self._get_connection()
        try:
            cur = conn.cursor()
            now = datetime.now(timezone.utc)
            cur.execute(
                """
                UPDATE projects SET name = %s, description = %s, tags = %s, updated_at = %s
                WHERE id = %s
                """,
                (name, description, tags_json, now, id)
            )
            conn.commit()
            return self.get_project(id)
        finally:
            self._release_connection(conn)

    def delete_project(self, id: str):
        """Delete a project and its analyses."""
        conn = self._get_connection()
        try:
            cur = conn.cursor()
            # Delete analyses first (foreign key constraint)
            cur.execute("DELETE FROM analyses WHERE project_id = %s", (id,))
            cur.execute("DELETE FROM projects WHERE id = %s", (id,))
            conn.commit()
        finally:
            self._release_connection(conn)

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
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
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
            self._release_connection(conn)

    def list_analyses(self, project_id: str) -> list[Dict[str, Any]]:
        """List all analyses for a project."""
        conn = self._get_connection()
        try:
            cur = conn.cursor()
            cur.execute("SELECT * FROM analyses WHERE project_id = %s ORDER BY created_at DESC", (project_id,))
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
            self._release_connection(conn)

    def update_analysis_status(self, id: str, status: str, progress: int = None):
        """Update analysis status and progress."""
        conn = self._get_connection()
        try:
            cur = conn.cursor()
            if progress is not None:
                cur.execute(
                    "UPDATE analyses SET status = %s, progress = %s WHERE id = %s",
                    (status, progress, id)
                )
            else:
                cur.execute(
                    "UPDATE analyses SET status = %s WHERE id = %s",
                    (status, id)
                )
            conn.commit()
        finally:
            self._release_connection(conn)
