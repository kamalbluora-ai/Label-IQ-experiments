"""
LabelIQ API - CFIA Food Label Compliance Backend
Merged from core/main.py - contains job endpoints for image upload and compliance processing
"""

import os
from dotenv import load_dotenv

load_dotenv()

import json
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import (
    FastAPI,
    HTTPException,
    Request,
    UploadFile,
    File,
    Form,
    BackgroundTasks,
)
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

# Import from core module (works when deployed from project root)
from core.orchestrator import (
    process_manifest,
    get_storage_client,
    write_json,
    IN_BUCKET,
    OUT_BUCKET,
)
from core.reevaluation import reevaluate_question

# Cloud Run detection - for local testing vs production
IS_CLOUD_RUN = os.environ.get("K_SERVICE") is not None

app = FastAPI(
    title="LabelIQ API",
    description="Backend API for CFIA Food Labelling Analysis",
    version="1.0.0",
)

# Configure CORS for frontend - allow all origins for development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,  # Must be False when using wildcard origins
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================================
# Pydantic Models
# ============================================================================


class ReevaluationRequest(BaseModel):
    question_id: str
    question: str
    original_answer: str
    original_tag: str
    original_rationale: str
    user_comment: str


# ============================================================================
# Health Check Endpoints
# ============================================================================


@app.get("/")
async def root():
    return {"message": "LabelIQ API is running", "docs": "/docs"}


@app.get("/healthz")
def healthz():
    """Health check endpoint."""
    return {"ok": True}


# ============================================================================
# Job Endpoints - Image Upload and Compliance Processing
# ============================================================================


@app.post("/v1/jobs")
async def upload_and_create_job(
    background_tasks: BackgroundTasks,
    files: List[UploadFile] = File(...),
    product_metadata: Optional[str] = Form(default=None),
    tags: Optional[str] = Form(default=None),
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
        filename = file.filename or f"image_{i}.jpg"
        ext = os.path.splitext(filename)[1] or ".jpg"
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
        json.dumps(manifest, indent=2), content_type="application/json"
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
        json.dumps(initial_status, indent=2), content_type="application/json"
    )

    # Trigger processing in background (only for local dev)
    # In Cloud Run, Eventarc handles triggering via the POST /eventarc endpoint
    if not IS_CLOUD_RUN:
        background_tasks.add_task(process_manifest, bucket=IN_BUCKET, manifest=manifest)

    return {"job_id": job_id, "status": "QUEUED", "images": len(image_paths)}


@app.get("/v1/jobs/{job_id}")
def get_job_status(job_id: str):
    """Get job status."""
    storage_client = get_storage_client()
    path = f"jobs/{job_id}.json"
    blob = storage_client.bucket(OUT_BUCKET).blob(path)
    if not blob.exists():
        raise HTTPException(404, "Job not found")
    return json.loads(blob.download_as_text())


@app.get("/v1/jobs/{job_id}/report")
def get_job_report(job_id: str):
    """Retrieve a completed compliance report."""
    storage_client = get_storage_client()
    path = f"reports/{job_id}.json"
    blob = storage_client.bucket(OUT_BUCKET).blob(path)
    if not blob.exists():
        raise HTTPException(404, "Report not found yet")
    return json.loads(blob.download_as_text())


@app.post("/v1/jobs/{job_id}/reevaluate")
async def reevaluate_question_endpoint(job_id: str, request: ReevaluationRequest):
    """
    Re-evaluate a single compliance question with user feedback and persist changes.
    """
    # 1. Run Re-evaluation Logic
    reval_result = await reevaluate_question(
        question_id=request.question_id,
        question=request.question,
        original_answer=request.original_answer,
        original_tag=request.original_tag,
        original_rationale=request.original_rationale,
        user_comment=request.user_comment,
    )

    # 2. Persist to GCS (Read-Modify-Write)
    try:
        storage_client = get_storage_client()
        bucket = storage_client.bucket(OUT_BUCKET)
        blob_path = f"reports/{job_id}.json"
        blob = bucket.blob(blob_path)

        if blob.exists():
            report_data = json.loads(blob.download_as_text())
            updated = False

            if "results" in report_data:
                # Iterate sections
                for section_name, section_data in report_data["results"].items():
                    # Get results list (handling both schema variations)
                    results_list = section_data.get(
                        "check_results"
                    ) or section_data.get("results")
                    if not isinstance(results_list, list):
                        continue

                    # Optimized Search: Find specific item by question_id
                    target_item = next(
                        (
                            item
                            for item in results_list
                            if item.get("question_id") == request.question_id
                        ),
                        None,
                    )

                    if target_item:
                        # Update fields in-place
                        target_item["result"] = reval_result["new_tag"]
                        target_item["rationale"] = reval_result["new_rationale"]
                        target_item["user_comment"] = request.user_comment
                        updated = True
                        break  # Found it, stop searching sections

            if updated:
                blob.upload_from_string(
                    json.dumps(report_data, indent=2), content_type="application/json"
                )
    except Exception as e:
        print(f"Warning: Failed to persist re-evaluation to GCS: {e}")
        # Note: We don't fail the request if persistence fails, but logging is important.

    return reval_result


# ============================================================================
# Eventarc Webhook - GCS Trigger Entry Point
# ============================================================================


@app.post("/eventarc")
async def eventarc_entry(request: Request):
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
    report = process_manifest(bucket=bucket, manifest=manifest)

    return {
        "processed": True,
        "job_id": report["job_id"],
        "report_path": report["report_path"],
    }
