"""
Test script for NFT Audit Table.
Uses doc_ai_output.json as input.
"""
import json
from pathlib import Path

from compliance.nft_audit_table.integration import map_docai_to_inputs
from compliance.nft_audit_table.audit_orchestrator import NFTAuditor


def main():
    # Load DocAI output
    json_path = Path(__file__).parent / "doc_ai_output.json"
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    # Extract fields (the integration expects the fields dict with text values)
    fields = data.get("fields", {})
    
    # Convert to simple key:value format (integration expects {"nft_fat_en": "8"} not {"nft_fat_en": {"text": "8"}})
    simple_fields = {}
    for key, val in fields.items():
        if isinstance(val, dict) and "text" in val:
            simple_fields[key] = val["text"]
        else:
            simple_fields[key] = val
    
    print(f"Loaded {len(simple_fields)} fields from doc_ai_output.json\n")
    
    # Map to NutrientData objects
    inputs = map_docai_to_inputs(simple_fields)
    print(f"Mapped {len(inputs)} nutrients for auditing\n")
    
    # Audit each
    auditor = NFTAuditor()
    
    print("=" * 60)
    print("NFT AUDIT RESULTS")
    print("=" * 60)
    
    pass_count = 0
    fail_count = 0
    skip_count = 0
    
    for item in inputs:
        result = auditor.audit_nutrient(item)
        
        status_icon = "[PASS]" if result.status.value == "pass" else ("[FAIL]" if result.status.value == "fail" else "[SKIP]")
        
        if result.status.value == "pass":
            pass_count += 1
        elif result.status.value == "fail":
            fail_count += 1
        else:
            skip_count += 1
        
        print(f"{status_icon} {result.nutrient_name} ({item.unit}): {result.original_value}")
        print(f"   Status: {result.status.value}")
        if result.expected_value is not None:
            print(f"   Expected: {result.expected_value}")
        if result.rule_applied:
            print(f"   Rule: {result.rule_applied}")
        print()
    
    print("=" * 60)
    print(f"SUMMARY: {pass_count} PASS | {fail_count} FAIL | {skip_count} SKIP")
    print("=" * 60)
    
    # Cross-field validations
    print("\n" + "=" * 60)
    print("CROSS-FIELD VALIDATIONS")
    print("=" * 60)
    
    # Build nutrient dict for cross-field checks
    nutrients = {}
    for item in inputs:
        nutrients[item.name] = item.value
    
    cross_results = auditor.audit_cross_fields(nutrients)
    
    cross_pass = 0
    cross_fail = 0
    cross_warn = 0
    cross_skip = 0
    
    for result in cross_results:
        status_icon = "[PASS]" if result.status.value == "pass" else (
            "[FAIL]" if result.status.value == "fail" else (
                "[WARN]" if result.status.value == "warning" else "[SKIP]"
            )
        )
        
        if result.status.value == "pass":
            cross_pass += 1
        elif result.status.value == "fail":
            cross_fail += 1
        elif result.status.value == "warning":
            cross_warn += 1
        else:
            cross_skip += 1
        
        print(f"{status_icon} {result.check_name}")
        print(f"   {result.message}")
        if result.tolerance:
            print(f"   Tolerance: {result.tolerance}")
        print()
    
    print("=" * 60)
    print(f"CROSS-FIELD SUMMARY: {cross_pass} PASS | {cross_fail} FAIL | {cross_warn} WARN | {cross_skip} SKIP")
    print("=" * 60)


if __name__ == "__main__":
    main()
