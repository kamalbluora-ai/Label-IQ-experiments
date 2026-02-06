"""
Test script for Common Name Agent and Nutrition Facts Table attributes.
Uses ex1_doc_ai_output.json as input (bypasses DocAI).
Runs the full pipeline including LLM calls.
"""
import asyncio
import json
from pathlib import Path
from datetime import datetime

# Import orchestrator and agents
from compliance.agents_orchestrator import ComplianceOrchestrator
from compliance.agents.common_name import CommonNameAgent


def load_docai_output(file_path: str) -> dict:
    """Load DocAI output from JSON file."""
    with open(file_path, "r", encoding="utf-8") as f:
        return json.load(f)


async def test_common_name_agent(label_facts: dict) -> dict:
    """
    Test Common Name Agent:
    - Tests guardrail logic (skip if only 1 candidate)
    - Tests full LLM evaluation for multiple candidates
    """
    agent = CommonNameAgent()
    
    # Get questions for common name section
    from compliance.agents_orchestrator import QUESTIONS
    section_questions = QUESTIONS.get("common_name", {}).get("questions", [])
    
    print("\n" + "="*60)
    print("TESTING COMMON NAME AGENT")
    print("="*60)
    
    # Check fields_all for candidates
    fields_all = label_facts.get("fields_all", {})
    en_candidates = fields_all.get("common_name_en", [])
    fr_candidates = fields_all.get("common_name_fr", [])
    
    print(f"\nEN Candidates: {[c.get('text') for c in en_candidates]}")
    print(f"FR Candidates: {[c.get('text') for c in fr_candidates]}")
    
    # Check if guardrail should trigger
    guardrail_should_trigger = len(en_candidates) == 1 and len(fr_candidates) == 1
    print(f"\nGuardrail should trigger: {guardrail_should_trigger}")
    
    # Run evaluation
    print("\nRunning evaluation...")
    result = await agent.evaluate(label_facts, section_questions)
    
    # Check if guardrail actually triggered
    guardrail_triggered = any(
        "Single candidate detected" in r.get("rationale", "")
        for r in result.get("results", [])
    )
    print(f"Guardrail triggered: {guardrail_triggered}")
    
    # Validate guardrail logic
    if guardrail_should_trigger != guardrail_triggered:
        print("⚠️ WARNING: Guardrail logic mismatch!")
    else:
        print("✓ Guardrail logic working correctly")
    
    print(f"\nResults:")
    for r in result.get("results", []):
        print(f"  - {r.get('question_id')}: {r.get('result').upper()}")
        if r.get("selected_value"):
            print(f"    Value: {r.get('selected_value')}")
        print(f"    Rationale: {r.get('rationale')[:100]}...")
    
    return {
        "test_name": "Common Name Agent",
        "en_candidates_count": len(en_candidates),
        "fr_candidates_count": len(fr_candidates),
        "guardrail_should_trigger": guardrail_should_trigger,
        "guardrail_triggered": guardrail_triggered,
        "guardrail_logic_correct": guardrail_should_trigger == guardrail_triggered,
        "results": result.get("results", [])
    }


def test_nft_audit(label_facts: dict) -> dict:
    """
    Test Nutrition Facts Table (NFT Auditor):
    - Tests rounding rules compliance
    - Tests cross-field validations
    """
    orchestrator = ComplianceOrchestrator()
    
    # Get questions for NFT section
    from compliance.agents_orchestrator import QUESTIONS
    section_questions = QUESTIONS.get("nutrition_facts_table", {}).get("questions", [])
    
    print("\n" + "="*60)
    print("TESTING NFT AUDITOR")
    print("="*60)
    
    # Run NFT audit
    print("\nRunning NFT audit...")
    result = orchestrator.run_nft_audit(label_facts, section_questions)
    
    print(f"\nSection: {result.get('section')}")
    
    # Display audit details
    audit_details = result.get("audit_details")
    if audit_details:
        print("\nNutrient Audits:")
        for audit in audit_details.get("nutrient_audits", []):
            status_icon = "✓" if audit["status"] == "pass" else "✗" if audit["status"] == "fail" else "?"
            print(f"  {status_icon} {audit['nutrient_name']}: {audit['original_value']} {audit['unit']} -> {audit['expected_value']} ({audit['status'].upper()})")
            if audit.get("rule_applied"):
                print(f"      Rule: {audit['rule_applied']}")
        
        print("\nCross-Field Audits:")
        for check in audit_details.get("cross_field_audits", []):
            status_icon = "✓" if check["status"] == "pass" else "✗" if check["status"] == "fail" else "?"
            print(f"  {status_icon} {check['check_name']}: {check['status'].upper()}")
            print(f"      {check['message']}")
    
    # Summary
    print("\nResults Summary:")
    for r in result.get("results", []):
        print(f"  - {r.get('question_id')}: {r.get('result').upper()}")
        print(f"    {r.get('rationale')}")
    
    return {
        "test_name": "NFT Auditor",
        "section": result.get("section"),
        "audit_details": audit_details,
        "results": result.get("results", [])
    }


async def run_all_tests():
    """Run all tests and save output to JSON."""
    # Load DocAI output
    json_path = Path(__file__).parent / "ex1_doc_ai_output.json"
    print(f"Loading DocAI output from: {json_path}")
    label_facts = load_docai_output(json_path)
    
    test_results = {
        "timestamp": datetime.now().isoformat(),
        "input_file": str(json_path),
        "tests": []
    }
    
    # Test 1: Common Name Agent
    try:
        common_name_result = await test_common_name_agent(label_facts)
        test_results["tests"].append(common_name_result)
    except Exception as e:
        print(f"❌ Common Name Agent test failed: {e}")
        test_results["tests"].append({
            "test_name": "Common Name Agent",
            "error": str(e)
        })
    
    # Test 2: NFT Auditor
    try:
        nft_result = test_nft_audit(label_facts)
        test_results["tests"].append(nft_result)
    except Exception as e:
        print(f"❌ NFT Auditor test failed: {e}")
        test_results["tests"].append({
            "test_name": "NFT Auditor",
            "error": str(e)
        })
    
    # Summary assertions
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    
    all_passed = True
    for test in test_results["tests"]:
        if "error" in test:
            print(f"❌ {test['test_name']}: FAILED - {test['error']}")
            all_passed = False
        else:
            results = test.get("results", [])
            pass_count = sum(1 for r in results if r.get("result") == "pass")
            fail_count = sum(1 for r in results if r.get("result") == "fail")
            review_count = sum(1 for r in results if r.get("result") == "needs_review")
            
            print(f"\n{test['test_name']}:")
            print(f"  PASS: {pass_count}, FAIL: {fail_count}, NEEDS_REVIEW: {review_count}")
            
            # Add to test results
            test["summary"] = {
                "pass_count": pass_count,
                "fail_count": fail_count,
                "needs_review_count": review_count,
                "total": len(results)
            }
    
    # Save output to JSON
    output_path = Path(__file__).parent / "test_attributes_output.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(test_results, f, indent=2, ensure_ascii=False)
    
    print(f"\n✓ Results saved to: {output_path}")
    
    return test_results


if __name__ == "__main__":
    asyncio.run(run_all_tests())
