"""
Test Multi-Agent Compliance System

Tests the new multi-agent architecture with live DocAI extraction.
"""

import json
import asyncio
import os
from pathlib import Path
from dotenv import load_dotenv

from compliance.agents_orchestrator import ComplianceOrchestrator
from core.processor import run_docai_custom_extractor
from core.orchestrator import merge_label_facts


USER_CONTEXT = {
    "food_type": "ready-to-eat",  # Options: "ready-to-eat", "needs-cooking"
    # Add more context as needed:
    # "is_imported": True,
    # "contains_sweeteners": False,
}


async def main():
    print("=" * 70)
    print("MULTI-AGENT COMPLIANCE TEST (Live DocAI)")
    print("=" * 70)
    
    # Load environment variables
    print("\n[1] Loading environment variables...")
    load_dotenv()
    
    project_id = os.environ.get("DOCAI_PROJECT")
    location = os.environ.get("DOCAI_LOCATION")
    processor_id = os.environ.get("DOCAI_PROCESSOR_ID")
    
    if not (project_id and location and processor_id):
        print("  ERROR: Missing DocAI environment variables")
        print("  Required: DOCAI_PROJECT, DOCAI_LOCATION, DOCAI_PROCESSOR_ID")
        return
    
    print(f"  ✓ Project: {project_id}")
    print(f"  ✓ Location: {location}")
    print(f"  ✓ Processor: {processor_id}")
    
    # Load sample images
    print("\n[2] Loading sample images...")
    sample_dir = Path(__file__).parent / "sample_files" / "ex1"
    front_img = sample_dir / "front.png"
    back_img = sample_dir / "back.png"
    
    if not front_img.exists():
        print(f"  ERROR: front.png not found at {front_img}")
        return
    if not back_img.exists():
        print(f"  ERROR: back.png not found at {back_img}")
        return
    
    print(f"  ✓ Front: {front_img}")
    print(f"  ✓ Back: {back_img}")
    
    # Extract facts from both images
    print("\n[3] Calling DocAI for front image...")
    with open(front_img, "rb") as f:
        front_bytes = f.read()
    
    front_facts = run_docai_custom_extractor(
        project_id=project_id,
        location=location,
        processor_id=processor_id,
        file_bytes=front_bytes,
        mime_type="image/png"
    )
    print(f"  ✓ Extracted {len(front_facts.get('fields', {}))} fields from front")
    
    print("\n[4] Calling DocAI for back image...")
    with open(back_img, "rb") as f:
        back_bytes = f.read()
    
    back_facts = run_docai_custom_extractor(
        project_id=project_id,
        location=location,
        processor_id=processor_id,
        file_bytes=back_bytes,
        mime_type="image/png"
    )
    print(f"  ✓ Extracted {len(back_facts.get('fields', {}))} fields from back")
    
    # Merge facts
    print("\n[5] Merging facts from both images...")
    merged_facts = merge_label_facts([front_facts, back_facts])
    print(f"  ✓ Merged to {len(merged_facts.get('fields', {}))} fields")
    
    # Show user context
    print("\n[6] User Context:")
    for key, value in USER_CONTEXT.items():
        print(f"    - {key}: {value}")
    
    # Initialize orchestrator
    print("\n[7] Initializing orchestrator...")
    orchestrator = ComplianceOrchestrator()
    print(f"  ✓ Loaded {len(orchestrator.questions)} sections")
    print(f"  ✓ Initialized {len(orchestrator.agents)} agents:")
    for agent_name in orchestrator.agents.keys():
        print(f"      - {agent_name}")
    
    # Run evaluation
    print("\n[8] Running multi-agent evaluation...")
    print("    (Agents running in parallel...)")
    result = await orchestrator.evaluate(merged_facts, user_context=USER_CONTEXT)
    
    # Display results
    print("\n" + "=" * 70)
    print("RESULTS")
    print("=" * 70)
    print(f"\nCompliance Score: {result['compliance_score']}%")
    print(f"Checks Passed: {result['checks_passed']}/{result['checks_total']}")
    
    print("\n" + "-" * 70)
    print("DETAILED RESULTS")
    print("-" * 70)
    
    for check in result['check_results']:
        status_icon = {
            "pass": "✓",
            "fail": "✗",
            "needs_review": "?"
        }.get(check['result'], "?")
        
        print(f"\n[{check['section']}] {check['question_id']}")
        print(f"  {status_icon} {check['result'].upper()}")
        print(f"  Q: {check['question']}")
        if check.get('selected_value'):
            print(f"  Value: {check['selected_value']}")
        print(f"  Rationale: {check['rationale']}")
    
    # Save results
    output_file = Path("multi_agent_compliance_result.json")
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)
    
    print("\n" + "=" * 70)
    print(f"✓ Results saved to: {output_file}")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(main())
