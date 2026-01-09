"""
Net Quantity Hardcoded Compliance Checks.

This module implements hardcoded logic for the Net Quantity compliance checklist:
1. Is a net quantity declaration present?
2. Is the net quantity declared on the PDP?
3. Is the appropriate manner (volume, weight, count) used?
4. Is it rounded to 3 figures (unless below 100)?
5. Are correct bilingual symbols used?

Architecture: Frontend (uploads + tags) → FastAPI → GCS IN → DocAI → this module → GCS OUT
"""

import re
from typing import Any, Dict, List, Optional, Tuple

from dotenv import load_dotenv
load_dotenv()


# Valid metric symbols (bilingual by default)
VOLUME_SYMBOLS = {"ml", "mL", "mℓ", "L", "l", "ℓ", "cl", "cL"}
WEIGHT_SYMBOLS = {"g", "kg", "mg"}
US_SYMBOLS = {"oz", "fl oz", "lb", "lbs"}

# Spelled-out units that require bilingual declaration
SPELLED_UNITS_EN = {"millilitre", "millilitres", "litre", "litres", "gram", "grams", "kilogram", "kilograms"}
SPELLED_UNITS_FR = {"millilitre", "millilitres", "litre", "litres", "gramme", "grammes", "kilogramme", "kilogrammes"}


def get_net_quantity(label_facts: Dict[str, Any]) -> Tuple[Optional[str], float]:
    """
    Extract net quantity from DocAI extracted fields.
    
    Returns:
        Tuple of (net_quantity_text, confidence)
    """
    fields = label_facts.get("fields", {}) or {}
    fields_all = label_facts.get("fields_all", {}) or {}
    
    # Try fields_all first for multiple candidates
    candidates = []
    for key in ["net_quantity_full_text", "net_quantity_value"]:
        for item in fields_all.get(key, []):
            text = item.get("text", "").strip()
            conf = item.get("confidence", 0.0) or 0.0
            if text:
                candidates.append({"text": text, "confidence": conf, "key": key})
    
    # Fallback to fields
    if not candidates:
        for key in ["net_quantity_full_text", "net_quantity_value"]:
            if key in fields:
                item = fields[key]
                text = item.get("text", "").strip() if isinstance(item, dict) else str(item)
                conf = item.get("confidence", 0.0) if isinstance(item, dict) else 0.5
                if text:
                    candidates.append({"text": text, "confidence": conf, "key": key})
    
    if not candidates:
        return (None, 0.0)
    
    # Pick highest confidence
    candidates.sort(key=lambda x: x["confidence"], reverse=True)
    best = candidates[0]
    return (best["text"], best["confidence"])


def parse_net_quantity(text: str) -> Dict[str, Any]:
    """
    Parse net quantity text to extract value, unit, and manner.
    
    Returns:
        Dict with: value (float), unit (str), manner (volume/weight/count), raw_text
    """
    if not text:
        return {"value": None, "unit": None, "manner": None, "raw_text": text}
    
    # Clean up text
    clean_text = text.strip().replace("\n", " ")
    
    # Pattern to match number + unit
    # Examples: "200g", "500 mL", "1.5 kg", "20 Bars"
    pattern = r'(\d+(?:[.,]\d+)?)\s*([a-zA-Zℓ]+)?'
    match = re.search(pattern, clean_text)
    
    if not match:
        return {"value": None, "unit": None, "manner": None, "raw_text": text}
    
    value_str = match.group(1).replace(",", ".")
    unit = match.group(2) or ""
    
    try:
        value = float(value_str)
    except ValueError:
        value = None
    
    # Determine manner
    unit_lower = unit.lower()
    manner = None
    
    if unit_lower in {s.lower() for s in VOLUME_SYMBOLS}:
        manner = "volume"
    elif unit_lower in {s.lower() for s in WEIGHT_SYMBOLS}:
        manner = "weight"
    elif unit_lower in {"oz", "lb", "lbs"}:
        manner = "weight"
    elif unit_lower in {"fl oz"}:
        manner = "volume"
    elif not unit or unit_lower in {"bars", "pieces", "count", "units", "pack"}:
        manner = "count"
    
    return {
        "value": value,
        "unit": unit,
        "manner": manner,
        "raw_text": text
    }


def fuzzy_contains(needle: str, haystack: str) -> bool:
    """Check if needle appears in haystack (case-insensitive)."""
    if not needle or not haystack:
        return False
    return needle.lower() in haystack.lower()


# ============================================================================
# Question 1: Is a net quantity declaration present?
# ============================================================================
def check_net_quantity_present(label_facts: Dict[str, Any]) -> Dict[str, Any]:
    """
    Question 1: Is a net quantity declaration present?
    
    Logic:
    - Check net_quantity fields from DocAI
    - Confidence >= 50% → pass
    - Confidence < 50% → needs_review
    - Not found → fail
    """
    net_qty, confidence = get_net_quantity(label_facts)
    
    if not net_qty:
        return {
            "question_id": 1,
            "answer": "fail",
            "reason": "No net quantity declaration found in the label"
        }
    
    if confidence >= 0.50:
        return {
            "question_id": 1,
            "answer": "pass",
            "reason": f"Net quantity '{net_qty}' is present (confidence: {confidence:.0%})"
        }
    else:
        return {
            "question_id": 1,
            "answer": "needs_review",
            "reason": f"Net quantity '{net_qty}' detected with low confidence ({confidence:.0%}). Manual verification recommended."
        }


# ============================================================================
# Question 2: Is the net quantity declared on the PDP?
# ============================================================================
def check_net_quantity_on_pdp(
    label_facts: Dict[str, Any],
    tags: Optional[List[str]] = None
) -> Dict[str, Any]:
    """
    Question 2: Is the net quantity declared on the PDP?
    
    Logic:
    - Uses frontend tags (same as common_name)
    - Tags passed from frontend → API → manifest → orchestrator
    - Check if net quantity appears in PDP panel text
    """
    net_qty, _ = get_net_quantity(label_facts)
    
    if not net_qty:
        return {
            "question_id": 2,
            "answer": "needs_review",
            "reason": "Cannot check PDP placement - no net quantity identified"
        }
    
    # Get PDP text (same approach as common_name)
    pdp_text = ""
    panels = label_facts.get("panels", {}) or {}
    
    if panels.get("panel_pdp"):
        pdp_data = panels["panel_pdp"]
        pdp_text = pdp_data.get("text", "") if isinstance(pdp_data, dict) else str(pdp_data)
    
    # Fallback to main OCR text
    if not pdp_text:
        pdp_text = label_facts.get("text", "")[:5000]
    
    if not pdp_text:
        return {
            "question_id": 2,
            "answer": "needs_review",
            "reason": "No PDP/front panel text available for verification"
        }
    
    # Parse to get just the numeric value for matching
    parsed = parse_net_quantity(net_qty)
    value_str = str(int(parsed["value"])) if parsed["value"] and parsed["value"] == int(parsed["value"]) else (str(parsed["value"]) if parsed["value"] else "")
    
    # Check if net quantity appears in PDP
    if fuzzy_contains(net_qty, pdp_text) or (value_str and fuzzy_contains(value_str, pdp_text)):
        return {
            "question_id": 2,
            "answer": "pass",
            "reason": f"Net quantity '{net_qty}' found on the principal display panel"
        }
    else:
        return {
            "question_id": 2,
            "answer": "fail",
            "reason": f"Net quantity '{net_qty}' not found on the principal display panel"
        }


# ============================================================================
# Question 3: Is the appropriate manner (volume, weight, count) used?
# ============================================================================
def check_appropriate_manner(label_facts: Dict[str, Any]) -> Dict[str, Any]:
    """
    Question 3: Is the appropriate manner (volume, weight, count) used?
    
    Logic:
    - Parse net quantity for units
    - Detect manner: volume (ml, L), weight (g, kg), count
    - Valid manner detected → pass
    """
    net_qty, _ = get_net_quantity(label_facts)
    
    if not net_qty:
        return {
            "question_id": 3,
            "answer": "needs_review",
            "reason": "Cannot check manner - no net quantity identified"
        }
    
    parsed = parse_net_quantity(net_qty)
    
    if parsed["manner"]:
        return {
            "question_id": 3, 
            "answer": "pass",
            "reason": f"Net quantity uses '{parsed['manner']}' manner (unit: {parsed['unit'] or 'count'})"
        }
    elif parsed["unit"]:
        return {
            "question_id": 3,
            "answer": "needs_review",
            "reason": f"Unit '{parsed['unit']}' detected but manner unclear. Manual verification recommended."
        }
    else:
        return {
            "question_id": 3,
            "answer": "needs_review",
            "reason": "No unit detected. Could be count-based declaration. Manual verification recommended."
        }


# ============================================================================
# Question 4: Is it rounded to 3 figures (unless below 100)?
# ============================================================================
def check_rounding(label_facts: Dict[str, Any]) -> Dict[str, Any]:
    """
    Question 4: Is it rounded to 3 figures (unless below 100)?
    
    Logic:
    - Parse numeric value
    - If < 100 → pass (no requirement)
    - If >= 100 → check for max 3 significant figures
    """
    net_qty, _ = get_net_quantity(label_facts)
    
    if not net_qty:
        return {
            "question_id": 4,
            "answer": "needs_review",
            "reason": "Cannot check rounding - no net quantity identified"
        }
    
    parsed = parse_net_quantity(net_qty)
    
    if parsed["value"] is None:
        return {
            "question_id": 4,
            "answer": "needs_review",
            "reason": "Cannot parse numeric value for rounding check"
        }
    
    value = parsed["value"]
    
    if value < 100:
        return {
            "question_id": 4,
            "answer": "pass",
            "reason": f"Value {value} is below 100 - no 3-figure rounding requirement"
        }
    
    # Check if rounded to 3 significant figures
    # For values >= 100, we expect whole numbers like 100, 250, 500, 1000
    if value == int(value):
        # Count significant figures (non-trailing-zero digits counting from left)
        value_str = str(int(value))
        sig_figs = len(value_str.rstrip('0')) if value_str != '0' else 1
        
        if sig_figs <= 3:
            return {
                "question_id": 4,
                "answer": "pass",
                "reason": f"Value {int(value)} has {sig_figs} significant figures (≤3)"
            }
        else:
            return {
                "question_id": 4,
                "answer": "needs_review",
                "reason": f"Value {int(value)} may have more than 3 significant figures. Verify rounding."
            }
    else:
        return {
            "question_id": 4,
            "answer": "needs_review",
            "reason": f"Value {value} contains decimals. Manual verification of rounding recommended."
        }


# ============================================================================
# Question 5: Are correct bilingual symbols used?
# ============================================================================
def check_bilingual_symbols(label_facts: Dict[str, Any]) -> Dict[str, Any]:
    """
    Question 5: Are correct bilingual symbols used?
    
    Logic:
    - Check for metric symbols: ml, mL, L, g, kg (bilingual by default)
    - If metric symbol → pass
    - If spelled-out units → needs_review (requires bilingual check)
    """
    net_qty, _ = get_net_quantity(label_facts)
    
    if not net_qty:
        return {
            "question_id": 5,
            "answer": "needs_review",
            "reason": "Cannot check symbols - no net quantity identified"
        }
    
    parsed = parse_net_quantity(net_qty)
    unit = parsed.get("unit", "") or ""
    
    if not unit:
        return {
            "question_id": 5,
            "answer": "needs_review",
            "reason": "No unit detected. If count-based, symbols may not apply."
        }
    
    # Check if metric symbol (bilingual by default)
    if unit in VOLUME_SYMBOLS or unit in WEIGHT_SYMBOLS:
        return {
            "question_id": 5,
            "answer": "pass",
            "reason": f"Metric symbol '{unit}' is used (bilingual by default)"
        }
    
    # Check if spelled-out unit
    unit_lower = unit.lower()
    if unit_lower in SPELLED_UNITS_EN or unit_lower in SPELLED_UNITS_FR:
        return {
            "question_id": 5,
            "answer": "needs_review",
            "reason": f"Spelled-out unit '{unit}' detected. Verify bilingual declaration (unless exempt)."
        }
    
    # Unknown unit
    return {
        "question_id": 5,
        "answer": "needs_review",
        "reason": f"Unit '{unit}' type unclear. Manual verification of bilingual requirements recommended."
    }


# ============================================================================
# Main Orchestrator
# ============================================================================
def evaluate_net_quantity(
    label_facts: Dict[str, Any],
    tags: Optional[List[str]] = None
) -> Dict[str, Any]:
    """
    Evaluate all net quantity compliance questions.
    
    Args:
        label_facts: DocAI extracted label facts
        tags: List of image tags from frontend (e.g., ["front", "back"])
    
    Returns:
        Dictionary with evaluation results
    """
    results = []
    
    # Q1: Is net quantity present?
    q1_result = check_net_quantity_present(label_facts)
    results.append(q1_result)
    
    # Q2: Is net quantity on PDP?
    q2_result = check_net_quantity_on_pdp(label_facts, tags)
    results.append(q2_result)
    
    # Q3: Is appropriate manner used?
    q3_result = check_appropriate_manner(label_facts)
    results.append(q3_result)
    
    # Q4: Is it rounded to 3 figures?
    q4_result = check_rounding(label_facts)
    results.append(q4_result)
    
    # Q5: Are bilingual symbols used?
    q5_result = check_bilingual_symbols(label_facts)
    results.append(q5_result)
    
    # Calculate overall status
    overall_status = "pass"
    for r in results:
        if r["answer"] == "fail":
            overall_status = "fail"
            break
        elif r["answer"] == "needs_review" and overall_status != "fail":
            overall_status = "needs_review"
    
    # Get net quantity for reference
    net_qty, confidence = get_net_quantity(label_facts)
    parsed = parse_net_quantity(net_qty) if net_qty else {}
    
    return {
        "attribute": "net_quantity",
        "extracted_value": net_qty or "",
        "extraction_confidence": confidence,
        "parsed": parsed,
        "results": results,
        "overall_status": overall_status,
        "questions_count": len(results)
    }


if __name__ == "__main__":
    import json
    from pathlib import Path
    
    print("=" * 60)
    print("Net Quantity Hardcoded Compliance Test")
    print("=" * 60)
    
    # Try to load sample data
    test_file = Path(__file__).parent.parent / "extracted_facts.json"
    if test_file.exists():
        with open(test_file, 'r', encoding='utf-8') as f:
            label_facts = json.load(f)
        
        print(f"Loaded test data from: {test_file}")
        print("-" * 60)
        
        result = evaluate_net_quantity(label_facts, tags=["front"])
        print(json.dumps(result, indent=2))
    else:
        print(f"Test file not found: {test_file}")
