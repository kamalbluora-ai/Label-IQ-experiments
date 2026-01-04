"""
CFIA Label Compliance API - FastAPI Application Entry Point

This module contains only the API endpoints and request handling.
Business logic is delegated to orchestrator.py.
"""
import os
from dotenv import load_dotenv
load_dotenv()

import json
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException, Request, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from orchestrator import (
    process_manifest,
    get_storage_client,
    write_json,
    IN_BUCKET,
    OUT_BUCKET,
)


app = FastAPI(title="CFIA Label Compliance API", version="0.1.0")

# CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
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


@app.get("/healthz")
def healthz():
    """Health check endpoint."""
    return {"ok": True}


@app.post("/v1/jobs")
async def upload_and_create_job(
    files: List[UploadFile] = File(...),
    product_metadata: Optional[str] = Form(default=None),
):
    """
    Upload images and create a compliance job.
    
    - Accepts multiple image files
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
    
    # Create manifest (mode=None triggers auto-detection)
    manifest = {
        "job_id": job_id,
        "images": image_paths,
        "product_metadata": metadata,
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
    }
    out_bucket.blob(f"jobs/{job_id}.json").upload_from_string(
        json.dumps(initial_status, indent=2),
        content_type="application/json"
    )
    
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


@app.post("/")
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

    return {"processed": True, "job_id": report["job_id"], "report_path": report["report_path"]}

