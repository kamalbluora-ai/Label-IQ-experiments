import os
from dotenv import load_dotenv
load_dotenv()

import json
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException, Request, UploadFile, File, Form, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from core.orchestrator import process_manifest, get_storage_client, write_json, IN_BUCKET, OUT_BUCKET
from core.db import DatabaseManager
from core.orchestrator import execute_compliance_phase
from core.orchestrator import execute_report_assembly_phase
import base64
from core.orchestrator import update_job
from fastapi.responses import StreamingResponse, Response
from core.report_generator_docx import ReportGeneratorDocx
import asyncio
import base64

# Cloud Run detection - for local testing vs production
IS_CLOUD_RUN = os.environ.get("K_SERVICE") is not None

app = FastAPI(title="CFIA Label Compliance API", version="0.1.0")

# CORS for frontend (configurable via CORS_ORIGINS env var)
_raw = os.environ.get("CORS_ORIGINS", "*")
_origins = [o.strip() for o in _raw.split(",")] if _raw != "*" else ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_origins,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

class SubmitRequest(BaseModel):
    gcs_uri: str = Field(..., description="gs://bucket/path/to/image")
    product_metadata: Dict[str, Any] = Field(default_factory=dict)
    mode: str = Field(default="AS_IS", description="AS_IS or RELABEL")

class JobManifest(BaseModel):
    job_id: str
    mode: Optional[str] = None  # Optional - auto-detected if not provided
    product_metadata: Dict[str, Any] = Field(default_factory=dict)
    images: list[str] = Field(default_factory=list, description="GCS object paths relative to IN_BUCKET")

class ReportEditItem(BaseModel):
    question_id: str
    new_tag: Optional[str] = None
    user_comment: Optional[str] = None
    new_answer: Optional[str] = None

class SaveReportEditsRequest(BaseModel):
    edits: List[ReportEditItem]

class ProjectCreate(BaseModel):
    name: str
    description: str = ""
    tags: List[str] = []

class ProjectUpdate(BaseModel):
    name: str
    description: str = ""
    tags: List[str] = []

@app.get("/api/healthz")
def healthz():
    """Health check endpoint."""
    return {"ok": True}


# ===== PROJECT ENDPOINTS =====

@app.get("/api/v1/projects")
def list_projects():
    """List all projects."""
    db = DatabaseManager()
    return db.list_projects()

@app.post("/api/v1/projects")
def create_project(data: ProjectCreate):
    """Create a new project."""
    db = DatabaseManager()
    project_id = f"project-{uuid.uuid4()}"
    return db.create_project(project_id, data.name, data.description, data.tags)

@app.get("/api/v1/projects/{project_id}")
def get_project(project_id: str):
    """Get a single project."""
    db = DatabaseManager()
    project = db.get_project(project_id)
    if not project:
        raise HTTPException(404, "Project not found")
    return project

@app.put("/api/v1/projects/{project_id}")
def update_project(project_id: str, data: ProjectUpdate):
    """Update a project."""
    db = DatabaseManager()
    if not db.get_project(project_id):
        raise HTTPException(404, "Project not found")
    return db.update_project(project_id, data.name, data.description, data.tags)

@app.delete("/api/v1/projects/{project_id}")
def delete_project(project_id: str):
    """Delete a project and its analyses."""
    db = DatabaseManager()
    if not db.get_project(project_id):
        raise HTTPException(404, "Project not found")
    db.delete_project(project_id)
    return {"success": True}

@app.get("/api/v1/projects/{project_id}/analyses")
def list_analyses(project_id: str):
    """List all analyses for a project."""
    db = DatabaseManager()
    if not db.get_project(project_id):
        raise HTTPException(404, "Project not found")
    return db.list_analyses(project_id)


@app.post("/api/v1/jobs")
async def upload_and_create_job(
    files: List[UploadFile] = File(...),
    product_metadata: Optional[str] = Form(default=None),
    tags: Optional[str] = Form(default=None),
    project_id: Optional[str] = Form(default=None),
    background_tasks: BackgroundTasks = None,  # For local testing
):
    """
    Upload images and create a compliance job.
    
    - Accepts multiple image files
    - Accepts tags (JSON array as string, e.g., '["front", "back"]')
    - Uploads to GCS IN_BUCKET
    - Creates job.json manifest
    - Returns job_id for status polling
    """
    job_id = str(uuid.uuid4())
    storage_client = get_storage_client()
    bucket = storage_client.bucket(IN_BUCKET)
    
    image_paths = []
    for i, file in enumerate(files):
        ext = os.path.splitext(file.filename)[1] or ".jpg"
        blob_path = f"incoming/{job_id}/image_{i}{ext}"
        blob = bucket.blob(blob_path)
        
        content = await file.read()
        blob.upload_from_string(content, content_type=file.content_type or "image/jpeg")
        image_paths.append(blob_path)
    
    # Parse metadata if provided
    metadata = {}
    if product_metadata:
        try:
            metadata = json.loads(product_metadata)
        except json.JSONDecodeError:
            pass
    
    # Parse tags if provided
    parsed_tags = []
    if tags:
        try:
            parsed_tags = json.loads(tags)
        except json.JSONDecodeError:
            pass
    
    # Create manifest (mode=None triggers auto-detection)
    manifest = {
        "job_id": job_id,
        "images": image_paths,
        "product_metadata": metadata,
        "tags": parsed_tags,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    
    # Upload manifest to trigger Eventarc
    manifest_blob = bucket.blob(f"incoming/{job_id}/job.json")
    manifest_blob.upload_from_string(
        json.dumps(manifest, indent=2),
        content_type="application/json"
    )
    
    # Write initial job status to OUT_BUCKET immediately (prevents 404 during polling)
    out_bucket = storage_client.bucket(OUT_BUCKET)
    initial_status = {
        "job_id": job_id,
        "status": "QUEUED",
        "created_at": manifest["created_at"],
        "images": image_paths,
        "product_metadata": metadata,
        "tags": parsed_tags,
    }
    out_bucket.blob(f"jobs/{job_id}.json").upload_from_string(
        json.dumps(initial_status, indent=2),
        content_type="application/json"
    )
    
    # Create analysis record if project_id provided
    if project_id:
        db = DatabaseManager()
        # Ensure job exists first to satisfy FK constraint
        db.create_job(job_id, status="QUEUED")
        
        filenames = [f.filename for f in files]
        analysis_name = f"Analysis of {filenames[0]}" if len(filenames) == 1 else f"Analysis of {len(filenames)} files"
        db.create_analysis(
            id=job_id,
            project_id=project_id,
            name=analysis_name,
            job_id=job_id,
            image_names=filenames
        )

    # Trigger processing in background (only for local dev)
    # Note: Agents run sequentially inside process_manifest()
    if not IS_CLOUD_RUN and background_tasks:
        background_tasks.add_task(
            process_manifest,
            bucket=IN_BUCKET,
            manifest=manifest
        )

    return {"job_id": job_id, "status": "QUEUED", "images": len(image_paths)}


@app.get("/api/v1/jobs/{job_id}")
def get_job_status(job_id: str):
    """Get job status."""
    # Try DB first
    db = DatabaseManager()
    job = db.get_job(job_id)
    if job:
        # Construct response from DB job record
        return {
            "job_id": job["job_id"],
            "status": job["status"],
            "created_at": job["created_at"],
            # You might need to add images/metadata to jobs table if needed here, 
            # or fetch from GCS if detailed metadata is required but not in DB.
            # For now, simplistic status return:
            "mode": job["mode"]
        }

    # Fallback to GCS
    storage_client = get_storage_client()
    path = f"jobs/{job_id}.json"
    blob = storage_client.bucket(OUT_BUCKET).blob(path)
    if not blob.exists():
        raise HTTPException(404, "Job not found")
    return json.loads(blob.download_as_text())


@app.get("/api/v1/jobs/{job_id}/report")
def get_job_report(job_id: str):
    """Retrieve a completed compliance report."""
    storage_client = get_storage_client()
    path = f"reports/{job_id}.json"
    blob = storage_client.bucket(OUT_BUCKET).blob(path)
    if not blob.exists():
        raise HTTPException(404, "Report not found yet")
    return json.loads(blob.download_as_text())

@app.post("/api/v1/jobs/{job_id}/save-edits")
async def save_report_edits(job_id: str, request: SaveReportEditsRequest):
    """
    Save manual edits (tags and comments) to the report in GCS.
    """
    storage_client = get_storage_client()
    bucket = storage_client.bucket(OUT_BUCKET)
    blob_path = f"reports/{job_id}.json"
    blob = bucket.blob(blob_path)
    
    if not blob.exists():
        raise HTTPException(404, "Report not found")
        
    try:
        report_data = json.loads(blob.download_as_text())
        updated = False
        
        # Create a lookup for edits
        edits_map = {item.question_id: item for item in request.edits}
        
        if "results" in report_data:
            for section_name, section_data in report_data["results"].items():
                if isinstance(section_data, dict):
                    # Handle lists of results (agent checks)
                    results_list = section_data.get("check_results") or section_data.get("results")
                    if isinstance(results_list, list):
                        for item in results_list:
                            q_id = item.get("question_id")
                            if q_id in edits_map:
                                edit = edits_map[q_id]
                                if edit.new_tag:
                                    item["result"] = edit.new_tag
                                if edit.user_comment is not None: # Allow empty string to clear
                                    item["user_comment"] = edit.user_comment
                                if edit.new_answer is not None:
                                    item["selected_value"] = edit.new_answer
                                updated = True
        
        if updated:
            # Upload updated JSON
            blob.upload_from_string(
                json.dumps(report_data, indent=2),
                content_type="application/json"
            )

            # Also generate and upload DOCX
            from core.report_generator_docx import ReportGeneratorDocx
            generator = ReportGeneratorDocx(report_data)
            docx_io = generator.generate()
            docx_blob = bucket.blob(f"reports/{job_id}.docx")
            docx_blob.upload_from_string(
                docx_io.read(),
                content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            )

            return {"success": True, "updated": len(request.edits)}
        else:
            return {"success": True, "updated": 0, "message": "No matching questions found"}

    except Exception as e:
        print(f"Error saving report edits: {e}")
        raise HTTPException(500, f"Failed to save edits: {str(e)}")


@app.get("/api/v1/jobs/{job_id}/download-docx")
def download_report_docx_endpoint(job_id: str):
    """Generate and download DOCX report."""
    storage_client = get_storage_client()
    blob = storage_client.bucket(OUT_BUCKET).blob(f"reports/{job_id}.json")

    if not blob.exists():
        raise HTTPException(404, "Report not found")

    report_data = json.loads(blob.download_as_text())

    generator = ReportGeneratorDocx(report_data)
    docx_io = generator.generate()

    return StreamingResponse(
        docx_io,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": f"attachment; filename=Compliance_Report_{job_id}.docx"}
    )

@app.get("/api/v1/jobs/{job_id}/images")
def get_job_images(job_id: str):
    """Return list of images for a job."""
    storage_client = get_storage_client()
    bucket = storage_client.bucket(IN_BUCKET)
    prefix = f"incoming/{job_id}/"

    blobs = list(bucket.list_blobs(prefix=prefix))
    image_blobs = [b for b in blobs if not b.name.endswith("job.json")]

    return {
        "images": [
            {
                "name": blob.name.split("/")[-1],
                "url": f"/v1/jobs/{job_id}/images/{i}"
            }
            for i, blob in enumerate(image_blobs)
        ]
    }

@app.get("/api/v1/jobs/{job_id}/images/{image_index}")
def get_job_image(job_id: str, image_index: int):
    """Proxy an image from GCS."""
    storage_client = get_storage_client()
    bucket = storage_client.bucket(IN_BUCKET)
    prefix = f"incoming/{job_id}/"

    blobs = [b for b in bucket.list_blobs(prefix=prefix) if not b.name.endswith("job.json")]

    if image_index >= len(blobs):
        raise HTTPException(404, "Image not found")

    blob = blobs[image_index]
    content = blob.download_as_bytes()
    content_type = blob.content_type or "image/jpeg"

    return Response(content=content, media_type=content_type)


@app.post("/api/eventarc")
async def eventarc_entry(request: Request, background_tasks: BackgroundTasks):
    """Eventarc webhook entry point for GCS triggers."""
    body = await request.body()
    try:
        payload = json.loads(body.decode("utf-8"))
    except Exception:
        payload = {}

    bucket = payload.get("bucket") or payload.get("data", {}).get("bucket")
    name = payload.get("name") or payload.get("data", {}).get("name")

    if not bucket or not name:
        return {"ignored": True, "reason": "Missing bucket/name"}
    if bucket != IN_BUCKET:
        return {"ignored": True, "reason": "Wrong bucket"}

    # Only trigger on manifest files
    if not name.endswith("/job.json"):
        return {"ignored": True, "reason": "Not a manifest file (job.json)"}

    # Load manifest from GCS and process
    storage_client = get_storage_client()
    manifest_blob = storage_client.bucket(bucket).blob(name)
    manifest = json.loads(manifest_blob.download_as_text())
    job_id = manifest.get("job_id")

    if not job_id:
        return {"ignored": True, "reason": "Missing job_id in manifest"}

    # Idempotency gate: ignore duplicate Eventarc deliveries once processing has started
    db = DatabaseManager()
    existing = db.get_job(job_id)
    if existing and existing.get("status") in {
        "EXTRACTING",
        "EXTRACTED",
        "COMPLIANCE_STARTED",
        "PROCESSING",
        "DONE",
    }:
        return {
            "ignored": True,
            "reason": f"Already processing or done: {existing.get('status')}",
            "job_id": job_id,
        }

    # Acknowledge quickly to avoid Eventarc redelivery due to long processing time
    background_tasks.add_task(process_manifest, bucket=bucket, manifest=manifest)
    return {"accepted": True, "job_id": job_id}


# ===== PHASE 2: Compliance Group Execution (Pub/Sub Push) =====

@app.post("/api/compliance/execute")
async def compliance_execute(request: Request):
    """
    Pub/Sub push endpoint: Executes a single compliance agent group.
    Triggered by compliance-fan-out subscription.

    Expected Pub/Sub push body:
    {
        "message": {
            "data": "<base64-encoded JSON>",
            "attributes": {"job_id": "...", "group": "..."}
        }
    }
    """
    import base64

    body = await request.json()

    # Parse Pub/Sub push message
    pubsub_message = body.get("message", {})
    data_b64 = pubsub_message.get("data", "")

    try:
        data = json.loads(base64.b64decode(data_b64).decode("utf-8"))
    except Exception:
        data = pubsub_message.get("attributes", {})

    job_id = data.get("job_id")
    group = data.get("group")
    facts_path = data.get("facts_path")

    if not job_id or not group:
        return {"ignored": True, "reason": "Missing job_id or group"}

    db = DatabaseManager()
    if db.has_group_done_marker(job_id, group):
        return {
            "ignored": True,
            "reason": f"Group already completed: {group}",
            "job_id": job_id,
            "group": group,
        }

    if not db.claim_group_execution(job_id, group):
        return {
            "ignored": True,
            "reason": f"Group execution already claimed: {group}",
            "job_id": job_id,
            "group": group,
        }
    
    # Execute Phase 2 (Compliance)
    try:
        # Now calling the async function directly (no more asyncio.to_thread)
        result = await execute_compliance_phase(job_id, group, facts_path)
        return result
    except Exception as e:
        db.release_group_execution_claim(job_id, group)
        print(f"Error in compliance_execute for job {job_id}, group {group}: {e}")
        # Return 500 to trigger Pub/Sub retry
        raise HTTPException(status_code=500, detail=str(e))


# ===== PHASE 3: Report Assembly (Pub/Sub Fan-In) =====

@app.post("/api/compliance/finalize")
async def compliance_finalize(request: Request):
    """
    Pub/Sub push endpoint: Checks if all groups are done and assembles the report.
    Triggered by compliance-group-done subscription.

    Uses atomic increment to handle race conditions — only the LAST group
    to complete triggers report assembly.
    """
    
    body = await request.json()

    pubsub_message = body.get("message", {})
    data_b64 = pubsub_message.get("data", "")

    try:
        data = json.loads(base64.b64decode(data_b64).decode("utf-8"))
    except Exception:
        data = pubsub_message.get("attributes", {})

    job_id = data.get("job_id")
    group = data.get("group")

    if not job_id or not group:
        return {"ignored": True, "reason": "Missing job_id or group"}

    print(f"[FINALIZE] Group '{group}' done for job {job_id}")

    # One-shot guard: if already DONE, ignore duplicate finalize deliveries
    db = DatabaseManager()
    status = await asyncio.to_thread(db.get_job_status, job_id)
    if status == "DONE":
        return {"ignored": True, "reason": "Job already finalized", "job_id": job_id}

    # Use asyncio.to_thread for blocking DB call to avoid blocking event loop
    def _increment_and_check(jid, grp):
        db = DatabaseManager()
        return db.increment_completed_groups_if_pending(jid, grp)

    completed, total, incremented = await asyncio.to_thread(_increment_and_check, job_id, group)

    print(f"[FINALIZE] Job {job_id}: {completed}/{total} groups complete (incremented={incremented})")

    if completed < total:
        # Not all groups done yet — another invocation will handle it
        return {"waiting": True, "completed": completed, "total": total}

    # ═══ ALL GROUPS DONE — ASSEMBLE REPORT ═══
    claimed = await asyncio.to_thread(db.claim_report_finalize, job_id)
    if not claimed:
        return {"ignored": True, "reason": "Finalize already in progress or complete", "job_id": job_id}

    try:
        # execute_report_assembly_phase is sync/blocking
        return await asyncio.to_thread(execute_report_assembly_phase, job_id)
    except Exception:
        await asyncio.to_thread(db.release_report_finalize_claim, job_id)
        raise


