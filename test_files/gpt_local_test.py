"""
End-to-End Compliance Test with Real DocAI Extraction.

This script:
1. Reads real label images from disk
2. Runs DocAI Custom Extractor to extract label facts
3. Runs GPT-based compliance checks against CFIA checklist questions
4. Outputs the results

Usage:
    python test_real_pipeline.py

Requires:
    - DOCAI_PROJECT, DOCAI_LOCATION, DOCAI_PROCESSOR_ID env vars
    - OPENAI_API_KEY env var
    - Google Cloud credentials (gcp-credentials.json)
"""

import os
import sys
import json
from pathlib import Path

from dotenv import load_dotenv
load_dotenv()

sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.append(str(Path(__file__).parent.parent / "core"))

from core.processor import preprocess_image_bytes, run_docai_custom_extractor
from core.checks import run_checks


# Configuration
DOCAI_PROJECT = os.environ.get("DOCAI_PROJECT", "")
DOCAI_LOCATION = os.environ.get("DOCAI_LOCATION", "us")
DOCAI_PROCESSOR_ID = os.environ.get("DOCAI_PROCESSOR_ID", "")

# Default sample images
DEFAULT_IMAGES = [
    "sample_files/ex1/front.png",
    "sample_files/ex1/back.png",
]


def guess_mime(filepath: str) -> str:
    """Guess MIME type from file extension."""
    ext = filepath.lower()
    if ext.endswith(".png"):
        return "image/png"
    if ext.endswith(".jpg") or ext.endswith(".jpeg"):
        return "image/jpeg"
    return "application/octet-stream"


def extract_from_image(image_path: str, preprocess: bool = True) -> dict:
    """
    Extract label facts from a single image using DocAI.
    
    Args:
        image_path: Path to the image file
        preprocess: Whether to preprocess (denoise/deskew) the image
    
    Returns:
        DocAI extraction result with fields, text, panels
    """
    print(f"  Reading: {image_path}")
    with open(image_path, "rb") as f:
        img_bytes = f.read()
    
    if preprocess:
        print(f"  Preprocessing...")
        img_bytes = preprocess_image_bytes(img_bytes)
    
    print(f"  Running DocAI extraction...")
    result = run_docai_custom_extractor(
        project_id=DOCAI_PROJECT,
        location=DOCAI_LOCATION,
        processor_id=DOCAI_PROCESSOR_ID,
        file_bytes=img_bytes,
        mime_type=guess_mime(image_path),
    )
    
    return result


def merge_facts(all_facts: list) -> dict:
    """Merge label facts from multiple images."""
    merged = {
        "text": "",
        "fields": {},
        "fields_all": {},
        "panels": {},
    }
    
    for facts in all_facts:
        # Concatenate text
        t = facts.get("text", "")
        if t:
            merged["text"] += t[:5000] + "\n"
        
        # Best confidence wins for each field
        for k, v in (facts.get("fields", {}) or {}).items():
            if k not in merged["fields"]:
                merged["fields"][k] = v
            else:
                if (v.get("confidence", 0) or 0) > (merged["fields"][k].get("confidence", 0) or 0):
                    merged["fields"][k] = v
        
        # Collect all candidates
        for k, arr in (facts.get("fields_all", {}) or {}).items():
            merged["fields_all"].setdefault(k, []).extend(arr)
        
        # Panels
        for k, v in (facts.get("panels", {}) or {}).items():
            merged["panels"][k] = v
    
    merged["text"] = merged["text"][:30000]
    return merged


def run_pipeline(image_paths: list, use_gpt: bool = True) -> dict:
    """
    Run the full compliance pipeline on given images.
    
    Args:
        image_paths: List of image file paths
        use_gpt: Whether to use GPT-based compliance (True) or legacy (False)
    
    Returns:
        Complete compliance result
    """
    print("=" * 60)
    print("CFIA Label Compliance Pipeline")
    print("=" * 60)
    
    # Validate env vars
    if not DOCAI_PROJECT or not DOCAI_PROCESSOR_ID:
        print("ERROR: Missing DocAI configuration!")
        print("  Required: DOCAI_PROJECT, DOCAI_LOCATION, DOCAI_PROCESSOR_ID")
        return {"error": "Missing DocAI configuration"}
    
    # Step 1: Extract from each image
    print("\n[Step 1] DocAI Extraction")
    print("-" * 40)
    all_facts = []
    for img_path in image_paths:
        if not Path(img_path).exists():
            print(f"  WARNING: Image not found: {img_path}")
            continue
        facts = extract_from_image(img_path)
        all_facts.append(facts)
        print(f"  ✓ Extracted {len(facts.get('fields', {}))} fields")
    
    if not all_facts:
        return {"error": "No images processed"}
    
    # Step 2: Merge facts from all images
    print("\n[Step 2] Merging Facts")
    print("-" * 40)
    merged_facts = merge_facts(all_facts)
    print(f"  Total fields: {len(merged_facts.get('fields', {}))}")
    
    # Print extracted fields
    print("\n  Extracted Fields:")
    for field_name, field_data in merged_facts.get("fields", {}).items():
        text = field_data.get("text", "")[:50]
        conf = field_data.get("confidence", 0)
        print(f"    • {field_name}: \"{text}...\" ({conf:.0%})")
    
    # Save extracted facts for debugging
    with open("extracted_facts.json", "w", encoding="utf-8") as f:
        json.dump(merged_facts, f, indent=2, ensure_ascii=False)
    print(f"\n  ✓ Saved to: extracted_facts.json")
    
    # Step 3: Run compliance checks
    print("\n[Step 3] Compliance Checks")
    print("-" * 40)
    print(f"  Mode: {'GPT-based' if use_gpt else 'Legacy'}")
    
    result = run_checks(
        label_facts=merged_facts,
        cfia_evidence={},
        product_metadata={"mode": "AS_IS"},
        use_gpt=use_gpt
    )
    
    # Print results
    print(f"\n  Evaluation Method: {result.get('evaluation_method')}")
    print(f"  Verdict: {result.get('verdict')}")
    print(f"  Compliance Score: {result.get('compliance_score')}%")
    print(f"  Checks Passed: {result.get('checks_passed')}/{result.get('checks_total')}")
    
    print("\n  Results by Attribute:")
    for attr, status in result.get("check_results", {}).items():
        emoji = "✓" if status == "pass" else "✗" if status == "fail" else "?"
        print(f"    {emoji} {attr}: {status}")
    
    if result.get("issues"):
        print("\n  Issues Found:")
        for issue in result.get("issues", []):
            print(f"    [{issue['severity']}] {issue['code']}")
    
    # Save full result
    with open("compliance_result.json", "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)
    print(f"\n  ✓ Saved to: compliance_result.json")
    
    print("\n" + "=" * 60)
    
    return result


if __name__ == "__main__":
    # Use command line args or default images
    if len(sys.argv) > 1:
        images = sys.argv[1:]
    else:
        images = DEFAULT_IMAGES
    
    print(f"\nImages to process: {images}")
    
    result = run_pipeline(images, use_gpt=True)
