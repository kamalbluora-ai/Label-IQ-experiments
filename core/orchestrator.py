"""
CFIA Label Compliance Orchestrator

Pure business logic for processing label compliance jobs.
This module coordinates:
- DocAI extraction
- Evidence retrieval (Vertex Search / ChatGPT)
- Translation (for RELABEL mode)
- Compliance checks
"""
import os
from dotenv import load_dotenv
load_dotenv()

import json
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from google.cloud import storage

from processor import preprocess_image_bytes, run_docai_custom_extractor
from vertex_search import cfia_retrieve_snippets
from checks import run_checks
from translate_fields import translate_foreign_fields
from chatgpt_search import cfia_search_chatgpt_agent

# Environment configuration (use .get() to allow import without full config)
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


def get_evidence(
    label_facts: Dict[str, Any],
    product_metadata: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Factory method to retrieve CFIA evidence based on configured provider.
    Supports swapping between vertex_search and chatgpt_search implementations.
    
    Configure via CFIA_EVIDENCE_PROVIDER env var:
    - 'vertex_search': Use Google Vertex AI Search (default)
    - 'chatgpt_search': Use ChatGPT web search agent
    
    Args:
        label_facts: Extracted label facts from document
        product_metadata: Product metadata
    
    Returns:
        Evidence dictionary from chosen provider
    """
    provider = os.environ.get("CFIA_EVIDENCE_PROVIDER", "chatgpt_search")
    
    if provider == "chatgpt_search":
        return cfia_search_chatgpt_agent(
            project_id=VS_PROJECT,
            location=VS_LOCATION,
            datastore_id=VS_DATASTORE_ID,
            serving_config=VS_SERVING_CONFIG,
            label_facts=label_facts,
            product_metadata=product_metadata,
        )
    else:
        # Default to vertex_search
        return cfia_retrieve_snippets(
            project_id=VS_PROJECT,
            location=VS_LOCATION,
            datastore_id=VS_DATASTORE_ID,
            serving_config=VS_SERVING_CONFIG,
            label_facts=label_facts,
            product_metadata=product_metadata,
        )


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


def process_manifest(bucket: str, manifest: Dict[str, Any]) -> Dict[str, Any]:
    """
    Process a job manifest and run the full compliance pipeline.
    
    Args:
        bucket: GCS bucket name containing the images
        manifest: Job manifest with job_id, mode, product_metadata, images
    
    Returns:
        Complete report dictionary with job_id, results, evidence, etc.
    """
    storage_client = get_storage_client()
    
    # Validate basic shape
    job_id = manifest.get("job_id") or str(uuid.uuid4())
    manifest_mode = manifest.get("mode")  # May be None for auto-detection
    product_metadata = (manifest.get("product_metadata") or {}) or {}

    images = manifest.get("images") or []
    if not images:
        raise RuntimeError("Manifest has no images[]")

    update_job(job_id, {
        "status": "PROCESSING",
        "mode": manifest_mode, 
        "product_metadata": product_metadata,
        "manifest_path": f"gs://{bucket}/incoming/{job_id}/job.json",
        "images": images,
    })

    # Extract each image and merge
    all_facts = []
    for obj_name in images:
        img_bytes = storage_client.bucket(bucket).blob(obj_name).download_as_bytes()
        pre_bytes = preprocess_image_bytes(img_bytes)
        with open("temp_img.jpg", "wb") as f:
            f.write(pre_bytes)

        facts = run_docai_custom_extractor(
            project_id=DOCAI_PROJECT,
            location=DOCAI_LOCATION,
            processor_id=DOCAI_PROCESSOR_ID,
            file_bytes=img_bytes,
            mime_type=guess_mime(obj_name),
        )
        data = {"key": "value", "number": 42}
        with open("facts-front.json", "w") as f:
            json.dump(facts, f, indent=2)
        all_facts.append(facts)

    merged_facts = merge_label_facts(all_facts)

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

    evidence = get_evidence(
        label_facts=merged_facts,
        product_metadata=product_metadata,
    )

    compliance = run_checks(label_facts=merged_facts, cfia_evidence=evidence, product_metadata=product_metadata)

    report = {
        "job_id": job_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "mode": mode,
        "source_images": [f"gs://{bucket}/{p}" for p in images],
        "label_facts": merged_facts,
        "results": compliance,
        "cfia_evidence": evidence,
    }

    report_path = f"reports/{job_id}.json"
    write_json(report_path, report)
    update_job(job_id, {"status": "DONE", "report_path": f"gs://{OUT_BUCKET}/{report_path}"})
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
