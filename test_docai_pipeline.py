"""
Test script: Run existing pipeline and copy result from GCP bucket to local file.
Usage: python test_docai_pipeline.py
"""
import os
import json
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

import sys
sys.path.insert(0, str(Path(__file__).parent / "core"))

from google.cloud import storage
from orchestrator import process_manifest

OUT_BUCKET = os.environ.get("OUT_BUCKET", "")
IN_BUCKET = os.environ.get("IN_BUCKET", "")


def upload_local_images(bucket_name: str, local_paths: list, gcs_prefix: str = "") -> list:
    """Upload local images to GCP bucket, return GCS paths."""
    client = storage.Client()
    bucket = client.bucket(bucket_name)
    gcs_paths = []
    
    for local_path in local_paths:
        path = Path(local_path)
        if not path.exists():
            print(f"Warning: {path} not found, skipping")
            continue
        
        gcs_path = f"{gcs_prefix}/{path.name}" if gcs_prefix else path.name
        blob = bucket.blob(gcs_path)
        blob.upload_from_filename(str(path))
        print(f"Uploaded: {path.name} -> gs://{bucket_name}/{gcs_path}")
        gcs_paths.append(gcs_path)
    
    return gcs_paths


def main():
    # Local image paths
    sample_dir = Path(__file__).parent / "sample_files" / "ex6"
    local_images = [
        sample_dir / "front.png",
        sample_dir / "back.png",
    ]
    
    # 1. Upload to GCP IN_BUCKET
    print("Uploading images to GCP...")
    gcs_paths = upload_local_images(IN_BUCKET, local_images, "incoming/test-ex6")
    
    # 2. Create manifest
    manifest = {
        "job_id": "test-ex6",
        "mode": "AS_IS",
        "product_metadata": {"food_type": "test"},
        "images": gcs_paths,
        "tags": ["front", "back"],
    }
    
    # 3. Run the existing pipeline
    print("Running pipeline...")
    report = process_manifest(IN_BUCKET, manifest)
    job_id = report["job_id"]
    print(f"Pipeline complete. Job ID: {job_id}")
    
    # 4. Fetch from GCP bucket and save locally
    print(f"Fetching from gs://{OUT_BUCKET}/reports/{job_id}.json")
    client = storage.Client()
    blob = client.bucket(OUT_BUCKET).blob(f"reports/{job_id}.json")
    data = json.loads(blob.download_as_text())
    
    # 5. Save to doc_ai_output.json
    output_path = Path(__file__).parent / "doc_ai_output.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(data.get("label_facts", {}), f, indent=2, ensure_ascii=False)
    
    print(f"Saved: {output_path}")


if __name__ == "__main__":
    main()
