from typing import Dict, Any, List, Optional

def run_checks(label_facts: Dict[str, Any], cfia_evidence: Dict[str, Any], product_metadata: Dict[str, Any]) -> Dict[str, Any]:
    """Checklist-driven checks with compliance score calculation.
    
    Score Formula: (passed_checks / total_checks) * 100
    - Pass = counts toward passed
    - Fail / Needs Review = does not count toward passed
    
    Modes:
      - AS_IS: strict on-pack bilingual checks (EN/FR)
      - RELABEL: also returns relabel_plan built from *_generated translations
    """
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

    def gen(base_key: str) -> Dict[str, Optional[str]]:
        en = (fields.get(f"{base_key}_en_generated", {}) or {}).get("text", "").strip()
        fr = (fields.get(f"{base_key}_fr_generated", {}) or {}).get("text", "").strip()
        return {"en": en or None, "fr": fr or None}

    issues: List[Dict[str, Any]] = []
    
    # Track all checks for scoring
    # Format: {"check_id": "result"}  where result is "pass", "fail", or "needs_review"
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
        # Sub-check for bilingual unit words
        has_unit_words = present_any("net_quantity_unit_words_en", "net_quantity_unit_words_fr")
        if has_unit_words and not bilingual_exempt and mode == "AS_IS":
            msg = bilingual_pair_ok_onpack("net_quantity_unit_words_en", "net_quantity_unit_words_fr", exempt=bilingual_exempt)
            if msg:
                issues.append(_issue("NET_QUANTITY_UNIT_WORDS_BILINGUAL", msg, "needs_review", cfia_evidence, "NET_QUANTITY"))
                check_results["net_quantity"] = "needs_review"
            else:
                check_results["net_quantity"] = "pass"
        else:
            check_results["net_quantity"] = "pass"

    # --- Check 3: Ingredients list ---
    if not present_any("ingredients_list_en", "ingredients_list_fr", "ingredients_list_foreign"):
        severity = "needs_review" if not product_metadata.get("must_have_ingredients", False) else "fail"
        issues.append(_issue("INGREDIENTS_LIST_MISSING",
                             "List of ingredients not detected (may be exempt/single-ingredient).",
                             severity, cfia_evidence, "INGREDIENTS_ALLERGENS"))
        check_results["ingredients_list"] = severity
    else:
        if mode == "AS_IS":
            msg = bilingual_pair_ok_onpack("ingredients_list_en", "ingredients_list_fr", exempt=bilingual_exempt)
            if msg:
                issues.append(_issue("INGREDIENTS_BILINGUAL", msg, "fail", cfia_evidence, "BILINGUAL"))
                check_results["ingredients_list"] = "fail"
            else:
                check_results["ingredients_list"] = "pass"
        else:
            check_results["ingredients_list"] = "pass"

    # --- Check 4: Allergen / contains statements ---
    if present_any("contains_statement_en", "contains_statement_fr"):
        if mode == "AS_IS":
            msg = bilingual_pair_ok_onpack("contains_statement_en", "contains_statement_fr", exempt=bilingual_exempt)
            if msg:
                issues.append(_issue("CONTAINS_BILINGUAL", msg, "fail", cfia_evidence, "INGREDIENTS_ALLERGENS"))
                check_results["contains_statement"] = "fail"
            else:
                check_results["contains_statement"] = "pass"
        else:
            check_results["contains_statement"] = "pass"
    else:
        # No statement present - not an issue, mark as pass (N/A counts as pass)
        check_results["contains_statement"] = "pass"

    # --- Check 5: Cross contamination statement ---
    if present_any("cross_contamination_statement_en", "cross_contamination_statement_fr"):
        if mode == "AS_IS":
            msg = bilingual_pair_ok_onpack("cross_contamination_statement_en", "cross_contamination_statement_fr", exempt=bilingual_exempt)
            if msg:
                issues.append(_issue("CROSS_CONTAM_BILINGUAL", msg, "fail", cfia_evidence, "INGREDIENTS_ALLERGENS"))
                check_results["cross_contamination"] = "fail"
            else:
                check_results["cross_contamination"] = "pass"
        else:
            check_results["cross_contamination"] = "pass"
    else:
        check_results["cross_contamination"] = "pass"

    # --- Check 6: Dealer name/address ---
    if not present_any("dealer_name", "dealer_address"):
        issues.append(_issue("DEALER_INFO_MISSING",
                             "Dealer name and/or principal place of business address not detected.",
                             "fail", cfia_evidence, "BILINGUAL"))
        check_results["dealer_info"] = "fail"
    else:
        check_results["dealer_info"] = "pass"

    # --- Check 7: Importer statement (only if imported) ---
    if product_metadata.get("imported", False):
        if not present_any("importer_statement_en", "importer_statement_fr", "importer_statement_foreign"):
            issues.append(_issue("IMPORTED_BY_MISSING",
                                 "Product flagged as imported but importer statement not detected.",
                                 "needs_review", cfia_evidence, "ORIGIN"))
            check_results["importer_statement"] = "needs_review"
        else:
            check_results["importer_statement"] = "pass"
    else:
        # Not imported, N/A counts as pass
        check_results["importer_statement"] = "pass"

    # --- Check 8: Date markings (Best Before) ---
    if product_metadata.get("durable_life_days") is not None:
        d = int(product_metadata["durable_life_days"])
        if d <= 90 and not present_any("best_before_en", "best_before_fr", "best_before_foreign"):
            issues.append(_issue("BEST_BEFORE_MISSING",
                                 "Durable life <= 90 days: Best before date not detected.",
                                 "fail", cfia_evidence, "DATES"))
            check_results["best_before"] = "fail"
        elif mode == "AS_IS" and present_any("best_before_en", "best_before_fr"):
            msg = bilingual_pair_ok_onpack("best_before_en", "best_before_fr", exempt=bilingual_exempt)
            if msg:
                issues.append(_issue("BEST_BEFORE_BILINGUAL", msg, "fail", cfia_evidence, "DATES"))
                check_results["best_before"] = "fail"
            else:
                check_results["best_before"] = "pass"
        else:
            check_results["best_before"] = "pass"
    else:
        # No durable life specified, assume pass
        check_results["best_before"] = "pass"

    # --- Check 9: Nutrition facts table ---
    nft_present = present_any("nft_title_en", "nft_title_fr", "nft_text_block", "nft_table", "nft_title_foreign", "nft_text_block_foreign")
    if product_metadata.get("nft_required", False) and not nft_present:
        issues.append(_issue("NFT_MISSING",
                             "Nutrition Facts table required but not detected.",
                             "fail", cfia_evidence, "NUTRITION_FACTS"))
        check_results["nutrition_facts"] = "fail"
    elif not product_metadata.get("nft_required", False) and not nft_present:
        issues.append(_issue("NFT_NOT_DETECTED",
                             "Nutrition Facts table not detected (may be exempt depending on product and available display surface).",
                             "needs_review", cfia_evidence, "NUTRITION_FACTS"))
        check_results["nutrition_facts"] = "needs_review"
    else:
        check_results["nutrition_facts"] = "pass"

    # --- Check 10: FOP symbol ---
    if not present_any("fop_symbol_present"):
        issues.append(_issue("FOP_NOT_EVALUATED",
                             "Front-of-package symbol not detected or not evaluated (threshold-based requirement).",
                             "needs_review", cfia_evidence, "FOP"))
        check_results["fop_symbol"] = "needs_review"
    else:
        check_results["fop_symbol"] = "pass"

    # --- Calculate Compliance Score ---
    total_checks = len(check_results)
    passed_checks = sum(1 for result in check_results.values() if result == "pass")
    compliance_score = round((passed_checks / total_checks) * 100) if total_checks > 0 else 0

    # --- Verdict ---
    verdict = _verdict(issues)

    # RELABEL mode: build proposed EN/FR content from translated outputs
    relabel_plan = None
    if mode == "RELABEL":
        relabel_plan = {
            "common_name": gen("common_name"),
            "ingredients_list": gen("ingredients_list"),
            "contains_statement": gen("contains_statement"),
            "cross_contamination_statement": gen("cross_contamination_statement"),
            "phenylalanine_statement": gen("phenylalanine_statement"),
            "best_before": gen("best_before"),
            "packaged_on": gen("packaged_on"),
            "storage_instructions": gen("storage_instructions"),
            "expiration_date": gen("expiration_date"),
            "nft_title": gen("nft_title"),
            "nft_serving_size": gen("nft_serving_size"),
            "nft_text_block": gen("nft_text_block"),
            "country_of_origin_statement": gen("country_of_origin_statement"),
            "importer_statement": gen("importer_statement"),
            "irradiation_statement": gen("irradiation_statement"),
            "sweetener_equivalence_statement": gen("sweetener_equivalence_statement"),
        }

    out = {
        "verdict": verdict,
        "issues": issues,
        "mode": mode,
        "compliance_score": compliance_score,
        "checks_passed": passed_checks,
        "checks_total": total_checks,
        "check_results": check_results,  # Detailed breakdown
    }
    if relabel_plan is not None:
        out["relabel_plan"] = relabel_plan
        out["translation_note"] = "Machine-generated translations (Cloud Translation). Human review required for high-risk fields (e.g., allergens)."
    return out


def _verdict(issues: List[Dict[str, Any]]) -> str:
    if any(i["severity"] == "fail" for i in issues):
        return "FAIL"
    if any(i["severity"] == "needs_review" for i in issues):
        return "NEEDS_REVIEW"
    return "PASS"


def _issue(code: str, message: str, severity: str, cfia_evidence: Dict[str, Any], evidence_key: str) -> Dict[str, Any]:
    refs = (cfia_evidence.get(evidence_key) or [])[:5]
    return {"code": code, "message": message, "severity": severity, "references": refs}

