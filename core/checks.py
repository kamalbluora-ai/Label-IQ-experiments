"""
CFIA Compliance Checks Module.

This module runs compliance checks using GPT-based evaluation against
CFIA checklist questions from JSON files.

Two modes available:
- GPT Mode (default): Uses gpt_compliance.py for dynamic evaluation
- Legacy Mode: Uses hardcoded logic (for fallback/comparison)

For common_name and net_quantity, hardcoded checks are used instead of pure GPT.
"""

import os
import sys
from pathlib import Path
from typing import Dict, Any, List, Optional

# Add parent directory to path for checklist_questions imports
_core_dir = Path(__file__).parent
_project_dir = _core_dir.parent
if str(_project_dir) not in sys.path:
    sys.path.insert(0, str(_project_dir))

from gpt_compliance import evaluate_all_attributes, evaluate_attribute
# Commented out - module doesn't exist, using multi-agent checks instead
# from checklist_questions.common_name_hardcoded import evaluate_common_name
# from checklist_questions.net_quantity_hardcoded import evaluate_net_quantity


def run_checks(
    label_facts: Dict[str, Any], 
    cfia_evidence: Dict[str, Any], 
    product_metadata: Dict[str, Any],
    use_gpt: bool = True,
    tags: Optional[List[str]] = None
) -> Dict[str, Any]:
    """
    Run compliance checks against extracted label facts.
    
    Args:
        label_facts: DocAI extracted fields
        cfia_evidence: Evidence snippets (for references)
        product_metadata: Product metadata including mode
        use_gpt: If True, use GPT-based evaluation; else use legacy hardcoded logic
        tags: Image tags from frontend (e.g., ["front", "back"])
    
    Returns:
        Compliance results with verdict, issues, and scores
    """
    if use_gpt:
        return run_gpt_checks(label_facts, cfia_evidence, product_metadata, tags=tags)
    else:
        return run_legacy_checks(label_facts, cfia_evidence, product_metadata)




# ============================================================
# OLD CODE (COMMENTED OUT - DO NOT DELETE)
# ============================================================
# def run_gpt_checks(
#     label_facts: Dict[str, Any], 
#     cfia_evidence: Dict[str, Any], 
#     product_metadata: Dict[str, Any],
#     tags: Optional[List[str]] = None
# ) -> Dict[str, Any]:
#     """
#     Run GPT-based compliance checks using CFIA checklist questions.
#     
#     For common_name and net_quantity, uses hardcoded checks (more reliable).
#     For other attributes, uses GPT-based evaluation.
#     
#     Args:
#         label_facts: DocAI extracted fields
#         cfia_evidence: Evidence snippets
#         product_metadata: Product metadata including mode
#         tags: Image tags from frontend (e.g., ["front", "back"])
#     """
#     mode = (product_metadata.get("mode") or "AS_IS").upper()
#     
#     # Run GPT evaluation on all attributes (will override some below)
#     gpt_results = evaluate_all_attributes(label_facts)
#     
#     # Override common_name with hardcoded evaluation (more reliable)
#     common_name_result = evaluate_common_name(label_facts, tags=tags)
#     gpt_results["common_name"] = common_name_result
#     
#     # Override net_quantity with hardcoded evaluation (more reliable)
#     net_quantity_result = evaluate_net_quantity(label_facts, tags=tags)
#     gpt_results["net_quantity"] = net_quantity_result
#     
#     # Convert GPT results to issues and check_results
#     issues: List[Dict[str, Any]] = []
#     check_results: Dict[str, str] = {}
#     
#     # Process each attribute's results
#     for attr_name, attr_result in gpt_results.items():
#         overall_status = attr_result.get("overall_status", "needs_review")
#         check_results[attr_name] = overall_status
#         
#         # Create issues for failed/needs_review items
#         if overall_status in ["fail", "needs_review"]:
#             # Collect failed question details
#             failed_questions = []
#             for r in attr_result.get("results", []):
#                 if r.get("answer") in ["fail", "needs_review"]:
#                     failed_questions.append(f"Q{r.get('question_id')}: {r.get('reason', 'No reason')}")
#             
#             issue_code = f"{attr_name.upper()}_{'FAIL' if overall_status == 'fail' else 'REVIEW'}"
#             issue_message = f"{attr_name.replace('_', ' ').title()}: {'; '.join(failed_questions[:3])}"
#             
#             issues.append({
#                 "code": issue_code,
#                 "message": issue_message,
#                 "severity": overall_status,
#                 "references": (cfia_evidence.get(attr_name.upper()) or [])[:5],
#                 "gpt_details": attr_result.get("results", [])
#             })
#     
#     # Calculate compliance score
#     total_checks = len(check_results)
#     passed_checks = sum(1 for result in check_results.values() if result == "pass")
#     compliance_score = round((passed_checks / total_checks) * 100) if total_checks > 0 else 0
#     
#     # Determine verdict
#     verdict = _verdict(issues)
#     
#     # Build relabel plan if RELABEL mode
#     relabel_plan = None
#     if mode == "RELABEL":
#         relabel_plan = _build_relabel_plan(label_facts)
#     
#     result = {
#         "verdict": verdict,
#         "issues": issues,
#         "mode": mode,
#         "compliance_score": compliance_score,
#         "checks_passed": passed_checks,
#         "checks_total": total_checks,
#         "check_results": check_results,
#         "evaluation_method": "gpt+hardcoded",
#         "gpt_results": gpt_results,
#     }
#     
#     if relabel_plan:
#         result["relabel_plan"] = relabel_plan
#         result["translation_note"] = "Machine-generated translations. Human review required for high-risk fields."
#     
#     return result


# ============================================================
# NEW CODE: Multi-Agent Checks (only Common Name + Net Quantity)
# ============================================================
import asyncio
import json
sys.path.insert(0, str(_project_dir / "compliance"))
from compliance.agents.common_name import CommonNameAgent
from compliance.agents.net_quantity import NetQuantityAgent


def run_multi_agent_checks(
    label_facts: Dict[str, Any],
    user_context: Dict[str, Any] = None
) -> Dict[str, Any]:
    """
    Run multi-agent compliance checks.
    Currently only Common Name and Net Quantity agents.
    
    Args:
        label_facts: DocAI extracted fields
        user_context: User context including food_type, tags, etc.
    
    Returns:
        Compliance results with scores and check details
    """
    # Load questions
    questions_path = _project_dir / "questions" / "questions.json"
    with open(questions_path, "r", encoding="utf-8") as f:
        questions = json.load(f).get("sections", {})
    
    # Initialize agents
    common_name_agent = CommonNameAgent()
    net_quantity_agent = NetQuantityAgent()
    
    # Run agents in parallel
    async def run_agents():
        cn_result = await common_name_agent.evaluate(
            label_facts, 
            questions.get("common_name", {}).get("questions", []),
            user_context
        )
        nq_result = await net_quantity_agent.evaluate(
            label_facts,
            questions.get("net_quantity", {}).get("questions", []),
            user_context
        )
        return [cn_result, nq_result]
    
    results = asyncio.run(run_agents())
    
    # Aggregate results
    all_checks = []
    for r in results:
        all_checks.extend(r.get("results", []))
    
    passed = sum(1 for c in all_checks if c.get("result") == "pass")
    total = len(all_checks)
    
    return {
        "verdict": "PASS" if passed == total else ("FAIL" if any(c.get("result") == "fail" for c in all_checks) else "NEEDS_REVIEW"),
        "compliance_score": round((passed / total) * 100, 2) if total > 0 else 0,
        "checks_passed": passed,
        "checks_total": total,
        "check_results": {c["question_id"]: c["result"] for c in all_checks},
        "evaluation_method": "multi-agent",
        "agent_details": all_checks,
    }


def run_gpt_checks(
    label_facts: Dict[str, Any], 
    cfia_evidence: Dict[str, Any], 
    product_metadata: Dict[str, Any],
    tags: Optional[List[str]] = None
) -> Dict[str, Any]:
    """
    NEW: Wrapper that calls multi-agent checks.
    Maintains backward compatibility with existing code.
    """
    user_context = {
        "tags": tags or [],
        "food_type": product_metadata.get("food_type", "ready-to-eat"),
    }
    return run_multi_agent_checks(label_facts, user_context)



def run_legacy_checks(
    label_facts: Dict[str, Any], 
    cfia_evidence: Dict[str, Any], 
    product_metadata: Dict[str, Any]
) -> Dict[str, Any]:
    """Legacy hardcoded compliance checks (original implementation)."""
    fields = label_facts.get("fields", {}) or {}
    mode = (product_metadata.get("mode") or "AS_IS").upper()
    bilingual_exempt = bool(product_metadata.get("bilingual_exempt", False))

    def get_text(key: str) -> str:
        v = fields.get(key)
        return (v.get("text", "") if isinstance(v, dict) else "") or ""

    def present_any(*keys: str) -> bool:
        return any(get_text(k).strip() for k in keys)

    def bilingual_pair_ok_onpack(en_key: str, fr_key: str, exempt: bool = False) -> Optional[str]:
        if exempt:
            return None
        en = get_text(en_key).strip()
        fr = get_text(fr_key).strip()
        if en and fr:
            return None
        if en or fr:
            return f"Missing bilingual counterpart on-pack for {en_key}/{fr_key}."
        return None

    issues: List[Dict[str, Any]] = []
    check_results: Dict[str, str] = {}

    # --- Check 1: Common name ---
    if not present_any("common_name_en", "common_name_fr", "common_name_foreign"):
        issues.append(_issue("COMMON_NAME_MISSING",
                             "Common name not detected (may be exempt in limited cases).",
                             "fail", cfia_evidence, "COMMON_NAME"))
        check_results["common_name"] = "fail"
    else:
        msg = bilingual_pair_ok_onpack("common_name_en", "common_name_fr", exempt=bilingual_exempt)
        if msg and mode == "AS_IS":
            issues.append(_issue("COMMON_NAME_BILINGUAL", msg, "fail", cfia_evidence, "BILINGUAL"))
            check_results["common_name"] = "fail"
        else:
            check_results["common_name"] = "pass"

    # --- Check 2: Net quantity ---
    if not present_any("net_quantity_full_text", "net_quantity_value"):
        issues.append(_issue("NET_QUANTITY_MISSING",
                             "Net quantity not detected (may be exempt in limited cases).",
                             "fail", cfia_evidence, "NET_QUANTITY"))
        check_results["net_quantity"] = "fail"
    else:
        check_results["net_quantity"] = "pass"

    # --- Check 3: Ingredients list ---
    if not present_any("ingredients_list_en", "ingredients_list_fr", "ingredients_list_foreign"):
        severity = "needs_review" if not product_metadata.get("must_have_ingredients", False) else "fail"
        issues.append(_issue("INGREDIENTS_LIST_MISSING",
                             "List of ingredients not detected (may be exempt/single-ingredient).",
                             severity, cfia_evidence, "INGREDIENTS_ALLERGENS"))
        check_results["list_of_ingredients"] = severity
    else:
        check_results["list_of_ingredients"] = "pass"

    # Calculate score
    total_checks = len(check_results)
    passed_checks = sum(1 for result in check_results.values() if result == "pass")
    compliance_score = round((passed_checks / total_checks) * 100) if total_checks > 0 else 0

    verdict = _verdict(issues)

    relabel_plan = None
    if mode == "RELABEL":
        relabel_plan = _build_relabel_plan(label_facts)

    result = {
        "verdict": verdict,
        "issues": issues,
        "mode": mode,
        "compliance_score": compliance_score,
        "checks_passed": passed_checks,
        "checks_total": total_checks,
        "check_results": check_results,
        "evaluation_method": "legacy",
    }
    
    if relabel_plan:
        result["relabel_plan"] = relabel_plan
    
    return result


def _verdict(issues: List[Dict[str, Any]]) -> str:
    if any(i.get("severity") == "fail" for i in issues):
        return "FAIL"
    if any(i.get("severity") == "needs_review" for i in issues):
        return "NEEDS_REVIEW"
    return "PASS"


def _issue(code: str, message: str, severity: str, cfia_evidence: Dict[str, Any], evidence_key: str) -> Dict[str, Any]:
    refs = (cfia_evidence.get(evidence_key) or [])[:5]
    return {"code": code, "message": message, "severity": severity, "references": refs}


def _build_relabel_plan(label_facts: Dict[str, Any]) -> Dict[str, Any]:
    """Build relabel plan from generated translations."""
    fields = label_facts.get("fields", {}) or {}
    
    def gen(base_key: str) -> Dict[str, Optional[str]]:
        en = (fields.get(f"{base_key}_en_generated", {}) or {}).get("text", "").strip()
        fr = (fields.get(f"{base_key}_fr_generated", {}) or {}).get("text", "").strip()
        return {"en": en or None, "fr": fr or None}
    
    return {
        "common_name": gen("common_name"),
        "ingredients_list": gen("ingredients_list"),
        "contains_statement": gen("contains_statement"),
        "net_quantity": gen("net_quantity"),
    }


if __name__ == "__main__":
    # Demo test
    print("=" * 60)
    print("Compliance Checks Demo")
    print("=" * 60)
    
    sample_label_facts = {
        "fields": {
            "common_name_en": {"text": "Granola Bar", "confidence": 0.95},
            "net_quantity_full_text": {"text": "200g", "confidence": 0.90},
            "ingredients_list_en": {"text": "Oats, Sugar, Honey", "confidence": 0.88},
        }
    }
    
    result = run_checks(
        label_facts=sample_label_facts,
        cfia_evidence={},
        product_metadata={"mode": "AS_IS"},
        use_gpt=True
    )
    
    print(f"Verdict: {result['verdict']}")
    print(f"Compliance Score: {result['compliance_score']}%")
    print(f"Checks Passed: {result['checks_passed']}/{result['checks_total']}")
    print(f"Evaluation Method: {result['evaluation_method']}")
    print("\nIssues:")
    for issue in result.get("issues", []):
        print(f"  - [{issue['severity']}] {issue['code']}: {issue['message']}")
