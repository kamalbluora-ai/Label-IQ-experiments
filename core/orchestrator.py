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


def process_manifest(bucket: str, manifest: Dict[str, Any]) -> Dict[str, Any]:
    """
    Process a job manifest and run the full compliance pipeline.
    """
    storage_client = get_storage_client()
    
    # Initialize DB
    db = DatabaseManager()
    
    # Validate basic shape
    job_id = manifest.get("job_id") or str(uuid.uuid4())
    
    # Create initial job record
    db.create_job(job_id, status="PENDING", mode=manifest.get("mode"))
    
    manifest_mode = manifest.get("mode")  # May be None for auto-detection
    product_metadata = (manifest.get("product_metadata") or {}) or {}
    tags = manifest.get("tags") or []  # Tags from frontend (e.g., ["front", "back"])

    images = manifest.get("images") or []
    if not images:
        raise RuntimeError("Manifest has no images[]")

    update_job(job_id, {
        "status": "PROCESSING",
        "mode": manifest_mode, 
        "product_metadata": product_metadata,
        "manifest_path": f"gs://{bucket}/incoming/{job_id}/job.json",
        "images": images,
        "tags": tags,
    })
    
    # Update DB status
    db.update_job_status(job_id, "PROCESSING")

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

    # NEW PIPELINE - Multi-attribute compliance evaluation
    orchestrator = AttributeOrchestrator()
    user_context = {"food_type": product_metadata.get("food_type", "unknown")}
    
    # Pass job_id to evaluate_sync for granular status usage
    compliance = orchestrator.evaluate_sync(merged_facts, job_id=job_id)

    report = {
        "job_id": job_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "mode": mode,
        "source_images": [f"gs://{bucket}/{p}" for p in images],
        "label_facts": merged_facts,
        "results": compliance,
        "cfia_evidence": {},  # Placeholder for frontend compatibility
    }

    report_path = f"reports/{job_id}.json"
    write_json(report_path, report)
    update_job(job_id, {"status": "DONE", "report_path": f"gs://{OUT_BUCKET}/{report_path}"})
    db.update_job_status(job_id, "DONE", mode=mode)
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
