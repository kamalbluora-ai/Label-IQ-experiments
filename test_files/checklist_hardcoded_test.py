"""
Test file for checklist hardcoded compliance checks.

This tests the common_name_hardcoded.py module against sample data.
"""

import json
import os
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from checklist_questions.common_name_hardcoded import (
    evaluate_common_name,
)


# ============================================================================
# NET QUANTITY TESTS
# ============================================================================

from checklist_questions.net_quantity_hardcoded import (
    evaluate_net_quantity,
)


# ============================================================================
# LIVE INTEGRATION TEST (Calls DocAI API)
# ============================================================================

def test_live_docai_integration():
    """
    Test the compliance logic using LIVE DocAI output from a sample image.
    This calls the actual Google Cloud Document AI API.
    """
    print("\n=== Testing Live DocAI Integration ===")
    
    # 1. Load Environment Variables
    from dotenv import load_dotenv
    load_dotenv()
    
    project_id = os.environ.get("DOCAI_PROJECT")
    location = os.environ.get("DOCAI_LOCATION")
    processor_id = os.environ.get("DOCAI_PROCESSOR_ID")
    
    if not (project_id and location and processor_id):
        print("  SKIPPING: Missing DocAI environment variables (DOCAI_PROJECT, etc.)")
        return

    # 2. Load Sample Image
    # Try to find a sample image in sample_files/ex1/front.png
    sample_img_path = Path(__file__).parent.parent / "sample_files" / "ex1" / "front.png"
    
    if not sample_img_path.exists():
        print(f"  SKIPPING: Sample image not found at {sample_img_path}")
        return
        
    print(f"  Processing image: {sample_img_path}")
    
    with open(sample_img_path, "rb") as f:
        image_bytes = f.read()
    
    # 3. Call DocAI
    try:
        from core.processor import run_docai_custom_extractor
        
        print("  Calling DocAI API... (this may take a few seconds)")
        label_facts = run_docai_custom_extractor(
            project_id=project_id,
            location=location,
            processor_id=processor_id,
            file_bytes=image_bytes,
            mime_type="image/png"  # Assuming PNG based on extension
        )
        print("  DocAI processing complete.")
        
    except ImportError as e:
        print(f"  ERROR: Missing dependencies: {e}")
        return
    except Exception as e:
        import traceback
        print(f"  ERROR calling DocAI type: {type(e)}")
        print(f"  ERROR message: {str(e)[:500]}")
        # print(traceback.format_exc())
        return

    # 4. Run Logic Checks
    
    # Common Name Check
    print("\n  [Common Name Compliance Check]")
    cn_result = evaluate_common_name(label_facts, tags=["front"])
    
    print(f"    Selected Common Name: '{cn_result['extracted_value']}'")
    print(f"    Confidence: {cn_result['extraction_confidence']:.2%}")
    print(f"    Overall Status: {cn_result['overall_status']}")
    
    for r in cn_result.get('results', []):
        print(f"    Q{r['question_id']}: {r['answer']} - {r['reason']}")
    
    # Net Quantity Check
    print("\n  [Net Quantity Compliance Check]")
    nq_result = evaluate_net_quantity(label_facts, tags=["front"])
    
    print(f"    Selected Net Quantity: '{nq_result['extracted_value']}'")
    print(f"    Confidence: {nq_result['extraction_confidence']:.2%}")
    print(f"    Parsed: {nq_result['parsed']}")
    print(f"    Overall Status: {nq_result['overall_status']}")
    
    for r in nq_result.get('results', []):
        print(f"    Q{r['question_id']}: {r['answer']} - {r['reason']}")


def main():
    """Run tests."""
    print("=" * 60)
    print("Label-IQ Compliance Logic Tests")
    print("=" * 60)
    
    # Only Live Integration Test
    test_live_docai_integration()
    
    print("\n" + "=" * 60)
    print("Tests completed.")
    print("=" * 60)


if __name__ == "__main__":
    main()
