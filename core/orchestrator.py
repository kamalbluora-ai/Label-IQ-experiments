import os
from dotenv import load_dotenv
load_dotenv()

import json
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from google.cloud import storage

import io
from PIL import Image

from core.processor import preprocess_image_bytes, run_docai_custom_extractor
from core.translate_fields import translate_foreign_fields
from compliance.attributes_orchestrator import AttributeOrchestrator
from core.db import DatabaseManager
from core.pubsub import publish_group_done, publish_fan_out

# Environment configuration
IN_BUCKET = os.environ.get("IN_BUCKET", "")
OUT_BUCKET = os.environ.get("OUT_BUCKET", "")

DOCAI_PROJECT = os.environ.get("DOCAI_PROJECT", "")
DOCAI_LOCATION = os.environ.get("DOCAI_LOCATION", "")
DOCAI_PROCESSOR_ID = os.environ.get("DOCAI_PROCESSOR_ID", "")

VS_PROJECT = os.environ.get("VS_PROJECT", "")
VS_LOCATION = os.environ.get("VS_LOCATION", "global")
VS_DATASTORE_ID = os.environ.get("VS_DATASTORE_ID", "")
VS_SERVING_CONFIG = os.environ.get("VS_SERVING_CONFIG", "default_search")

TRANSLATE_PROJECT = os.environ.get("TRANSLATE_PROJECT", "")
TRANSLATE_LOCATION = os.environ.get("TRANSLATE_LOCATION", "global")
TRANSLATE_GLOSSARY_ID = os.environ.get("TRANSLATE_GLOSSARY_ID")

GCP_PROJECT = os.environ.get("GOOGLE_CLOUD_PROJECT") or os.environ.get("DOCAI_PROJECT", "")

# Determine environment
IS_CLOUD_RUN = os.environ.get("K_SERVICE") is not None

# Lazy-initialized storage client
_storage_client = None

def get_storage_client() -> storage.Client:
    """Get or create the GCS storage client."""
    global _storage_client
    if _storage_client is None:
        _storage_client = storage.Client(project=GCP_PROJECT)
    return _storage_client

def detect_mode(label_facts: Dict[str, Any]) -> str:
    """Auto-detect mode based on presence of foreign language fields."""
    fields = label_facts.get("fields", {}) or {}
    foreign_keys = [
        "common_name_foreign",
        "ingredients_list_foreign",
        "nft_text_block_foreign",
        "contains_statement_foreign",
    ]
    has_foreign = any(fields.get(k) for k in foreign_keys)
    return "RELABEL" if has_foreign else "AS_IS"


def split_image_bytes(image_bytes: bytes) -> list[tuple[str, bytes]]:
    """
    Splits the image width-wise (x-axis) into two halves (Left and Right panels).
    Returns a list of tuples: [(panel_name, bytes), ...]
    """
    try:
        img = Image.open(io.BytesIO(image_bytes))
        width, height = img.size
        
        # Split width-wise (vertical split line)
        mid_point = width // 2
        
        # Left half
        left_half = img.crop((0, 0, mid_point, height))
        left_buffer = io.BytesIO()
        left_half.save(left_buffer, format=img.format or "JPEG")
        left_bytes = left_buffer.getvalue()
        
        # Right half
        right_half = img.crop((mid_point, 0, width, height))
        right_buffer = io.BytesIO()
        right_half.save(right_buffer, format=img.format or "JPEG")
        right_bytes = right_buffer.getvalue()
        
        return [("left_panel", left_bytes), ("right_panel", right_bytes)]
    except Exception as e:
        print(f"Error splitting image: {e}")
        return []



    
def execute_extraction_phase(job_id: str, bucket: str, manifest: Dict[str, Any]) -> tuple[Dict[str, Any], str, str]:
    storage_client = get_storage_client()
    db = DatabaseManager()

    manifest_mode = manifest.get("mode")
    product_metadata = (manifest.get("product_metadata") or {}) or {}
    tags = manifest.get("tags") or []
    images = manifest.get("images") or []

    if not images:
        raise RuntimeError("Manifest has no images[]")
    
    # Update GCS job record with extraction status
    update_job(job_id, {
        "status": "EXTRACTING",
        "mode": manifest_mode, 
        "product_metadata": product_metadata,
        "manifest_path": f"gs://{bucket}/incoming/{job_id}/job.json",
        "images": images,
        "tags": tags,
    })
    
    # Update DB status
    db.update_job_status(job_id, "EXTRACTING")

    # Always run DocAI pipeline
    print(f"Running DocAI pipeline for job {job_id}")
    
    # Extract each image and merge
    all_facts = []
    for i, obj_name in enumerate(images):
        img_bytes = storage_client.bucket(bucket).blob(obj_name).download_as_bytes()
            
        # Check tag for this image
        current_tag = tags[i].lower() if i < len(tags) and tags[i] else ""
        
        if current_tag == "front":
            # Split image into Left and Right panels
            print(f"Splitting image {obj_name} (tag: front) into two halves...")
            split_success = False
            try:
                panels = split_image_bytes(img_bytes)
                if panels:
                    for panel_name, panel_bytes in panels:
                        print(f"Processing split panel: {panel_name}")
                        facts = run_docai_custom_extractor(
                            project_id=DOCAI_PROJECT,
                            location=DOCAI_LOCATION,
                            processor_id=DOCAI_PROCESSOR_ID,
                            file_bytes=panel_bytes,
                            mime_type=guess_mime(obj_name),
                        )
                        # Save extraction to DB
                        db.add_docai_extraction(job_id, f"{current_tag}_{panel_name}", facts)
                        all_facts.append(facts)
                    split_success = True
            except Exception as e:
                print(f"Error splitting image: {e}")
            
            if not split_success:
                # Fallback to normal processing
                facts = run_docai_custom_extractor(
                    project_id=DOCAI_PROJECT,
                    location=DOCAI_LOCATION,
                    processor_id=DOCAI_PROCESSOR_ID,
                    file_bytes=img_bytes,
                    mime_type=guess_mime(obj_name),
                )
                # Save extraction to DB
                db.add_docai_extraction(job_id, f"{current_tag}_fallback", facts)
                all_facts.append(facts)
        else:
            # Normal processing
            facts = run_docai_custom_extractor(
                project_id=DOCAI_PROJECT,
                location=DOCAI_LOCATION,
                processor_id=DOCAI_PROCESSOR_ID,
                file_bytes=img_bytes,
                mime_type=guess_mime(obj_name),
            )
            # Save extraction to DB
            db.add_docai_extraction(job_id, current_tag or f"image_{i}", facts)
            all_facts.append(facts)

    merged_facts = merge_label_facts(all_facts)
    
    # Persist merged facts to DB
    db.save_merged_facts(job_id, merged_facts)

    # Auto-detect mode if not specified in manifest
    mode = manifest_mode.upper() if manifest_mode else detect_mode(merged_facts)
    product_metadata["mode"] = mode

    # Translation for RELABEL mode (before evidence retrieval)
    if mode == "RELABEL":
        if not TRANSLATE_PROJECT:
            raise RuntimeError("RELABEL mode requires TRANSLATE_PROJECT env var and Translation API enabled.")
        merged_facts = translate_foreign_fields(
            label_facts=merged_facts,
            project_id=TRANSLATE_PROJECT,
            location=TRANSLATE_LOCATION,
            glossary_id=TRANSLATE_GLOSSARY_ID,
        )
        
        # Update DB with translated facts
        db.save_merged_facts(job_id, merged_facts, translated_facts=merged_facts)

    facts_path = f"facts/{job_id}.json"
    facts_payload = {
        "job_id": job_id,
        "mode": mode,
        "merged_facts": merged_facts,
        "product_metadata": product_metadata,
        "source_images": [f"gs://{bucket}/{p}" for p in images],
    }
    write_json(facts_path, facts_payload)

    # Update status
    db.update_job_status(job_id, "EXTRACTED", mode=mode, facts_path=facts_path)
    update_job(job_id, {"status": "EXTRACTED", "mode": mode, "facts_path": facts_path})

    return merged_facts, mode, facts_path

async def execute_compliance_phase(job_id: str, group: str, facts_path: str) -> Dict[str, Any]:
    print(f"[COMPLIANCE] Executing group '{group}' for job {job_id}")
    
    db = DatabaseManager()
    db.update_job_status(job_id, "COMPLIANCE_STARTED")
    db.update_job_status(job_id, "PROCESSING")

    # Load facts from GCS
    storage_client = get_storage_client()
    facts_blob = storage_client.bucket(OUT_BUCKET).blob(facts_path)

    if not facts_blob.exists():
        print(f"[ERROR] Facts not found at {facts_path}")
        return {"error": True, "reason": f"Facts not found: {facts_path}"}

    facts_payload = json.loads(facts_blob.download_as_text())
    label_facts = facts_payload["merged_facts"]

    # Execute the agent group
    from compliance.group_executor import GroupExecutor
    executor = GroupExecutor()
    results = await executor.execute_group(group, label_facts, job_id)

    agents_completed = list(results.keys())
    print(f"[COMPLIANCE] Group '{group}' completed for job {job_id}: {agents_completed}")

    if IS_CLOUD_RUN:
        # ── Cloud Run: Publish Group Done Event ──
        publish_group_done(job_id=job_id, group=group, agents_completed=agents_completed)
        pass

    return {
        "processed": True,
        "job_id": job_id,
        "group": group,
        "agents_completed": agents_completed,
    }


def execute_report_assembly_phase(job_id: str) -> Dict[str, Any]:
    print(f"[FINALIZE] Assembling report for job {job_id}...")

    db = DatabaseManager()
    storage_client = get_storage_client()
    
    # Load facts from GCS
    facts_path = f"facts/{job_id}.json"
    facts_blob = storage_client.bucket(OUT_BUCKET).blob(facts_path)
    
    if not facts_blob.exists():
        # Fallback if facts missing (should not happen if flow works)
        print(f"[ERROR] Facts not found at {facts_path} during report assembly")
        facts_payload = {}
        merged_facts = {}
    else:
        facts_payload = json.loads(facts_blob.download_as_text())
        merged_facts = facts_payload.get("merged_facts", {})

    # Load all compliance results from database
    compliance_results = db.get_all_compliance_results(job_id)

    # Build report
    report = {
        "job_id": job_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "mode": facts_payload.get("mode", "AS_IS"),
        "source_images": facts_payload.get("source_images", []),
        "label_facts": merged_facts,
        "results": compliance_results,
        "cfia_evidence": {},
    }

    # Write report to GCS
    report_path = f"reports/{job_id}.json"
    write_json(report_path, report)

    # Update job status to DONE
    update_job(job_id, {"status": "DONE", "report_path": f"gs://{OUT_BUCKET}/{report_path}"})
    db.update_job_status(job_id, "DONE", mode=facts_payload.get("mode"))

    # Update analysis status if exists
    try:
        db.update_analysis_status(job_id, "completed", progress=100)
    except Exception:
        pass

    print(f"[FINALIZE] Report assembled for job {job_id}: {report_path}")

    return {
        "assembled": True,
        "job_id": job_id,
        "report_path": f"gs://{OUT_BUCKET}/{report_path}",
    }


def process_manifest(bucket: str, manifest: Dict[str, Any]) -> Dict[str, Any]:
    storage_client = get_storage_client()
    
    # Initialize DB
    db = DatabaseManager()
    
    # Validate basic shape
    job_id = manifest.get("job_id") or str(uuid.uuid4())

    # Defense-in-depth idempotency check for duplicate trigger deliveries
    existing = db.get_job(job_id)
    if existing and existing.get("status") in {
        "EXTRACTING",
        "EXTRACTED",
        "COMPLIANCE_STARTED",
        "PROCESSING",
        "DONE",
    }:
        print(f"[ORCHESTRATOR] Duplicate trigger ignored for job {job_id} (status={existing.get('status')})")
        return {"job_id": job_id, "status": existing.get("status"), "deduped": True}
    
    # Create initial job record
    db.create_job(job_id, status="PENDING", mode=manifest.get("mode"))
    
    # ── Execute Phase 1: Extraction ──
    merged_facts, mode, facts_path = execute_extraction_phase(job_id, bucket, manifest)

    if IS_CLOUD_RUN:
        # ── Cloud Run: Fan-out via Pub/Sub ──
        # Uncomment when deploying to Cloud Run with Eventarc + Pub/Sub fan-out.
        print(f"[ORCHESTRATOR] Cloud Run detected. Fanning out via Pub/Sub for job {job_id}")
        
        groups = ["identity", "content", "tables"]
        for group in groups:
            publish_fan_out(job_id=job_id, group=group, facts_path=facts_path)
            
        return {"job_id": job_id, "status": "EXTRACTED", "facts_path": facts_path}
    else:
        print(f"[ORCHESTRATOR] Local environment detected. Running compliance groups inline for job {job_id}")
        import asyncio
        
        update_job(job_id, {"status": "COMPLIANCE_STARTED"}) 
        db.update_job_status(job_id, "COMPLIANCE_STARTED")
        db.update_job_status(job_id, "PROCESSING")

        from compliance.group_executor import GroupExecutor
        executor = GroupExecutor()
        
        # Execute all 3 groups sequentially using asyncio.run since process_manifest is sync
        print(f"[ORCHESTRATOR] Running group: identity")
        results_identity = asyncio.run(executor.execute_group("identity", merged_facts, job_id))
        
        print(f"[ORCHESTRATOR] Running group: content")
        results_content = asyncio.run(executor.execute_group("content", merged_facts, job_id))
        
        print(f"[ORCHESTRATOR] Running group: tables")
        results_tables = asyncio.run(executor.execute_group("tables", merged_facts, job_id))


        print(f"[ORCHESTRATOR] All groups done. Assembling report...")
        
        # Load all compliance results from database (which were written by execute_group_sync helpers)
        compliance_results = db.get_all_compliance_results(job_id)
        
        # Determine source images again for report payload
        images = manifest.get("images") or []

        report = {
            "job_id": job_id,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "mode": mode,
            "source_images": [f"gs://{bucket}/{p}" for p in images],
            "label_facts": merged_facts,
            "results": compliance_results,
            "cfia_evidence": {},
        }

        report_path = f"reports/{job_id}.json"
        write_json(report_path, report)
        update_job(job_id, {"status": "DONE", "report_path": f"gs://{OUT_BUCKET}/{report_path}"})
        db.update_job_status(job_id, "DONE", mode=mode)
        
        # Update analysis status if exists
        try:
            db.update_analysis_status(job_id, "completed", progress=100)
        except Exception:
            pass

        report["report_path"] = f"gs://{OUT_BUCKET}/{report_path}"
        return report

def merge_label_facts(all_facts: list[Dict[str, Any]]) -> Dict[str, Any]:
    """Merge label facts from multiple images into a single consolidated result."""
    merged = {
        "text": "",
        "fields": {},
        "fields_all": {},
        "panels": {},
        "translated": {},
    }

    for facts in all_facts:
        # concatenate small capped text (optional)
        t = facts.get("text", "")
        if t:
            merged["text"] += (t[:5000] + "\n")

        # best-confidence winner for each field
        for k, v in (facts.get("fields", {}) or {}).items():
            if k not in merged["fields"]:
                merged["fields"][k] = v
            else:
                if (v.get("confidence", 0) or 0) > (merged["fields"][k].get("confidence", 0) or 0):
                    merged["fields"][k] = v

        # collect all candidates
        for k, arr in (facts.get("fields_all", {}) or {}).items():
            merged["fields_all"].setdefault(k, []).extend(arr)

        # panels (keep best confidence if you have it; otherwise last wins)
        for k, v in (facts.get("panels", {}) or {}).items():
            merged["panels"][k] = v

    # cap merged text
    merged["text"] = merged["text"][:30000]
    return merged

# --- GCS Helper Functions ---

def job_id_from_object(name: str) -> Optional[str]:
    """Extract job_id from GCS object path (incoming/{job_id}/filename.jpg)."""
    parts = name.split("/")
    if len(parts) >= 2 and parts[0] == "incoming":
        return parts[1]
    return None

def guess_mime(name: str) -> str:
    """Guess MIME type from filename extension."""
    n = name.lower()
    if n.endswith(".png"):
        return "image/png"
    if n.endswith(".jpg") or n.endswith(".jpeg"):
        return "image/jpeg"
    if n.endswith(".tif") or n.endswith(".tiff"):
        return "image/tiff"
    return "application/octet-stream"

def write_json(path: str, obj: Dict[str, Any]):
    """Write a JSON object to GCS."""
    storage_client = get_storage_client()
    blob = storage_client.bucket(OUT_BUCKET).blob(path)
    blob.upload_from_string(json.dumps(obj, ensure_ascii=False, indent=2), content_type="application/json")

def read_job(job_id: str) -> Optional[Dict[str, Any]]:
    """Read a job record from GCS."""
    storage_client = get_storage_client()
    path = f"jobs/{job_id}.json"
    blob = storage_client.bucket(OUT_BUCKET).blob(path)
    if not blob.exists():
        return None
    return json.loads(blob.download_as_text())

def update_job(job_id: str, patch: Dict[str, Any]):
    """Update a job record in GCS with a patch."""
    storage_client = get_storage_client()
    path = f"jobs/{job_id}.json"
    blob = storage_client.bucket(OUT_BUCKET).blob(path)
    cur = {}
    if blob.exists():
        cur = json.loads(blob.download_as_text())
    cur.update(patch)
    write_json(path, cur)
