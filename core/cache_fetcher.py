import json
from typing import Dict, Any, Optional
from google.cloud import storage


def get_cached_label_facts(
    job_id: str,
    out_bucket: str,
    storage_client: Optional[storage.Client] = None
) -> Optional[Dict[str, Any]]:
    """
    Fetch cached label_facts from GCP OUT Bucket.
    
    Args:
        job_id: Unique job identifier
        out_bucket: GCS bucket name containing reports
        storage_client: Optional pre-initialized storage client
        
    Returns:
        label_facts dict if found, None otherwise
    """
    if storage_client is None:
        storage_client = storage.Client()
    
    report_path = f"reports/{job_id}.json"
    
    try:
        blob = storage_client.bucket(out_bucket).blob(report_path)
        
        if not blob.exists():
            print(f"Cache miss: {report_path} not found in {out_bucket}")
            return None
        
        report_data = json.loads(blob.download_as_text())
        label_facts = report_data.get("label_facts")
        
        if not label_facts:
            print(f"Warning: {report_path} exists but has no label_facts")
            return None
        
        print(f"Cache hit: Loaded label_facts from {report_path}")
        return label_facts
        
    except Exception as e:
        print(f"Error fetching cached label_facts for {job_id}: {e}")
        return None


def is_cache_valid(label_facts: Dict[str, Any]) -> bool:
    """
    Validate that cached label_facts has expected structure.
    
    Args:
        label_facts: The cached label_facts dictionary
        
    Returns:
        True if valid, False otherwise
    """
    if not isinstance(label_facts, dict):
        return False
    
    # Check for required keys
    required_keys = ["fields"]
    for key in required_keys:
        if key not in label_facts:
            print(f"Invalid cache: missing required key '{key}'")
            return False
    
    # Check that fields is a dict
    if not isinstance(label_facts.get("fields"), dict):
        print("Invalid cache: 'fields' is not a dictionary")
        return False
    
    return True
