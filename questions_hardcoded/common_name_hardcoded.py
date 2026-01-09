"""
Common Name Hardcoded Compliance Checks.

This module implements hardcoded logic for the Common Name compliance checklist:
1. Is a common name present?
2. Is the common name on the principal display panel (PDP)?
3. Is it an appropriate common name?

These checks run after DocAI extraction and use rule-based logic + GPT validation.
"""

import json
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from dotenv import load_dotenv
load_dotenv()

from openai import OpenAI


# Paths to common names databases
NODE_APP_DIR = Path(__file__).parent.parent / "node_app"
CFIA_COMMON_NAMES_PATH = NODE_APP_DIR / "cfia_common_names_complete.json"
CFCS_COMMON_NAMES_PATH = NODE_APP_DIR / "cfcs_common_names.json"
CSI_COMMON_NAMES_PATH = NODE_APP_DIR / "csi_common_names.json"

# Caches for common names databases
_cfia_common_names_cache: Optional[List[str]] = None
_cfcs_common_names_cache: Optional[List[str]] = None
_csi_common_names_cache: Optional[List[str]] = None


def load_cfia_common_names() -> List[str]:
    """Load all common names from the CFIA database."""
    global _cfia_common_names_cache
    
    if _cfia_common_names_cache is not None:
        return _cfia_common_names_cache
    
    if not CFIA_COMMON_NAMES_PATH.exists():
        return []
    
    try:
        with open(CFIA_COMMON_NAMES_PATH, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        items = data.get("items", [])
        _cfia_common_names_cache = [
            item.get("common_name", "").lower().strip()
            for item in items
            if item.get("common_name")
        ]
        return _cfia_common_names_cache
    except Exception:
        return []


def load_cfcs_common_names() -> List[str]:
    """Load common names from CFCS (Canadian Food Commodity Standards)."""
    global _cfcs_common_names_cache
    
    if _cfcs_common_names_cache is not None:
        return _cfcs_common_names_cache
    
    if not CFCS_COMMON_NAMES_PATH.exists():
        return []
    
    try:
        with open(CFCS_COMMON_NAMES_PATH, 'r', encoding='utf-16') as f:
            data = json.load(f)
        
        _cfcs_common_names_cache = [
            item.get("common_name_with_def", "").lower().strip()
            for item in data
            if item.get("common_name_with_def")
        ]
        return _cfcs_common_names_cache
    except Exception:
        return []


def load_csi_common_names() -> List[str]:
    """Load common names from CSI (Canadian Standards of Identity)."""
    global _csi_common_names_cache
    
    if _csi_common_names_cache is not None:
        return _csi_common_names_cache
    
    if not CSI_COMMON_NAMES_PATH.exists():
        return []
    
    try:
        with open(CSI_COMMON_NAMES_PATH, 'r', encoding='utf-16') as f:
            data = json.load(f)
        
        _csi_common_names_cache = [
            item.get("common_name_with_def", "").lower().strip()
            for item in data
            if item.get("common_name_with_def")
        ]
        return _csi_common_names_cache
    except Exception:
        return []


def is_standard_common_name(name: str) -> Tuple[bool, Optional[str]]:
    """
    Check if a common name is a standard name in CFCS or CSI.
    
    Returns:
        Tuple of (is_standard, source) where source is "CFCS", "CSI", or None
    """
    if not name:
        return (False, None)
    
    name_lower = name.lower().strip()
    
    # Check CFCS
    cfcs_names = load_cfcs_common_names()
    for cfcs_name in cfcs_names:
        if name_lower in cfcs_name or cfcs_name in name_lower:
            return (True, "CFCS")
    
    # Check CSI
    csi_names = load_csi_common_names()
    for csi_name in csi_names:
        if name_lower in csi_name or csi_name in name_lower:
            return (True, "CSI")
    
    return (False, None)


def extract_first_ingredient(ingredients_text: str) -> Optional[str]:
    """
    Extract the first ingredient from an ingredients list.
    
    Handles formats like:
    - "Ingredients: Rolled Oats, Sugar, ..."
    - "(Whole Grain Rolled Oats, Sugar, ...)"
    """
    if not ingredients_text:
        return None
    
    text = ingredients_text.strip()
    
    # Remove common prefixes
    prefixes = ["ingredients:", "ingrédients:", "édients:"]
    for prefix in prefixes:
        if text.lower().startswith(prefix):
            text = text[len(prefix):].strip()
    
    # Handle parenthetical grouping at the start
    if text.startswith("("):
        # Find matching close paren or just take content inside
        paren_end = text.find(")")
        if paren_end > 1:
            text = text[1:paren_end]
    
    # Split by comma and get first item
    parts = text.split(",")
    if parts:
        first = parts[0].strip()
        # Remove any leading parenthesis that might remain
        first = first.lstrip("(").strip()
        return first if first else None
    
    return None


def fuzzy_match(text1: str, text2: str, threshold: float = 0.7) -> bool:
    """
    Simple fuzzy match between two strings.
    Returns True if one contains the other or they share significant overlap.
    """
    if not text1 or not text2:
        return False
    
    t1 = text1.lower().strip()
    t2 = text2.lower().strip()
    
    # Exact match
    if t1 == t2:
        return True
    
    # Containment check
    if t1 in t2 or t2 in t1:
        return True
    
    # Word-level overlap
    words1 = set(re.split(r'\W+', t1))
    words2 = set(re.split(r'\W+', t2))
    
    # Remove empty strings
    words1.discard('')
    words2.discard('')
    
    if not words1 or not words2:
        return False
    
    intersection = words1 & words2
    union = words1 | words2
    
    # Jaccard similarity
    similarity = len(intersection) / len(union) if union else 0
    
    return similarity >= threshold


def get_best_common_name(
    label_facts: Dict[str, Any]
) -> Tuple[Optional[str], float, str]:
    """
    Get the best common name from extracted facts.
    
    Logic (Updated for 4-step process):
    1. Sort candidates (highest conf first).
    2. If top candidate >= 0.80 and matches ingredient -> PASS.
    3. Else if second candidate matches ingredient -> NEEDS_REVIEW.
    4. Else -> FAIL (fallback to top candidate).
    
    Returns:
        Tuple of (common_name_text, confidence, status)
        status is 'pass', 'needs_review', or 'fail'
    """
    fields = label_facts.get("fields", {}) or {}
    fields_all = label_facts.get("fields_all", {}) or {}
    
    # Collect all common name candidates
    candidates = []
    for key in ["common_name_en", "common_name_fr", "common_name"]:
        for item in fields_all.get(key, []):
            text = item.get("text", "").strip()
            conf = item.get("confidence", 0.0) or 0.0
            if text:
                candidates.append({"text": text, "confidence": conf, "key": key})
    
    # If no candidates from fields_all, try fields directly
    if not candidates:
        for key in ["common_name_en", "common_name_fr", "common_name"]:
            if key in fields:
                item = fields[key]
                text = item.get("text", "").strip() if isinstance(item, dict) else str(item)
                conf = item.get("confidence", 0.0) if isinstance(item, dict) else 0.5
                if text:
                    candidates.append({"text": text, "confidence": conf, "key": key})
    
    if not candidates:
        return (None, 0.0, False)
    
    # Sort by confidence (highest first)
    candidates.sort(key=lambda x: x["confidence"], reverse=True)
    best = candidates[0]
    
    # Get first ingredient for verification
    first_ingredient = None
    for key in ["ingredients_list_en", "ingredients_list_fr", "ingredients_list"]:
        ing_data = fields.get(key)
        if ing_data:
            ing_text = ing_data.get("text", "") if isinstance(ing_data, dict) else str(ing_data)
            first_ingredient = extract_first_ingredient(ing_text)
            if first_ingredient:
                break
    
    # Selection Logic (Specific 4-Step):
    # Step 1 & 2: Check Top Candidate
    # Condition: Confidence >= 0.80 AND Matches First Ingredient
    best = candidates[0]
    top_matches = False
    if first_ingredient:
        top_matches = fuzzy_match(best["text"], first_ingredient)
    
    if (best["confidence"] >= 0.80) and top_matches:
        return (best["text"], best["confidence"], "pass")
        
    # Step 3: If Step 1/2 fails, check Second Best
    # Condition: Matches First Ingredient -> "needs_review"
    if len(candidates) > 1:
        second = candidates[1]
        second_matches = False
        if first_ingredient:
            second_matches = fuzzy_match(second["text"], first_ingredient)
            
        if second_matches:
            return (second["text"], second["confidence"], "needs_review")

    # Step 4: If both fail
    # Return best candidate for display, but status is "fail"
    return (best["text"], best["confidence"], "fail")


def check_common_name_present(
    label_facts: Dict[str, Any],
    cfia_names: List[str]
) -> Dict[str, Any]:
    """
    Question 1: Is a common name present?
    
    Logic:
    - Uses get_best_common_name status ('pass', 'needs_review', 'fail')
    """
    common_name, confidence, status = get_best_common_name(label_facts)
    
    if not common_name:
        return {
            "question_id": 1,
            "answer": "fail",
            "reason": "No common name found in the label"
        }
    
    if status == "pass":
        return {
            "question_id": 1,
            "answer": "pass",
            "reason": f"Common name '{common_name}' is present (confidence: {confidence:.0%}) and matches first ingredient criteria."
        }
    elif status == "needs_review":
        return {
            "question_id": 1,
            "answer": "needs_review",
            "reason": f"Common name '{common_name}' found via secondary match logic. Manual verification recommended."
        }
    else:
        # Fail case
        return {
            "question_id": 1,
            "answer": "fail",
            "reason": f"Common name '{common_name}' detected but did not meet confidence/matching criteria. (Confidence: {confidence:.0%})"
        }


def check_common_name_on_pdp(
    label_facts: Dict[str, Any],
    tags: Optional[List[str]] = None
) -> Dict[str, Any]:
    """
    Question 2: Is the common name on the principal display panel (PDP)?
    
    Logic:
    - Get the common name
    - Check if tags include "front" -> use that image's text
    - Otherwise, use panels.panel_pdp text
    - Verify common name appears in PDP text
    """
    common_name, _, _ = get_best_common_name(label_facts)
    
    if not common_name:
        return {
            "question_id": 2,
            "answer": "needs_review",
            "reason": "Cannot check PDP placement - no common name identified"
        }
    
    # Get PDP text
    pdp_text = ""
    panels = label_facts.get("panels", {}) or {}
    
    # If "front" tag was provided, we trust DocAI's panel_pdp detection
    # In the future, this could be enhanced to use per-image text based on tags
    if panels.get("panel_pdp"):
        pdp_data = panels["panel_pdp"]
        pdp_text = pdp_data.get("text", "") if isinstance(pdp_data, dict) else str(pdp_data)
    
    # Also check the main OCR text if no specific panel
    if not pdp_text:
        pdp_text = label_facts.get("text", "")[:5000]  # Use first portion of full text
    
    if not pdp_text:
        return {
            "question_id": 2,
            "answer": "needs_review",
            "reason": "No PDP/front panel text available for verification"
        }
    
    # Check if common name appears in PDP
    if fuzzy_match(common_name, pdp_text, threshold=0.5):
        return {
            "question_id": 2,
            "answer": "pass",
            "reason": f"Common name '{common_name}' found on the principal display panel"
        }
    else:
        return {
            "question_id": 2,
            "answer": "fail",
            "reason": f"Common name '{common_name}' not found on the principal display panel"
        }


def check_appropriate_common_name(
    label_facts: Dict[str, Any],
    api_key: Optional[str] = None
) -> Dict[str, Any]:
    """
    Question 3: Is it an appropriate common name?
    
    Logic:
    1. First check if the common name is in CFCS or CSI (standard name)
    2. If found in CFCS/CSI -> automatically pass (it's a standard name)
    3. If not found -> use GPT to evaluate appropriateness
    """
    common_name, _, _ = get_best_common_name(label_facts)
    
    if not common_name:
        return {
            "question_id": 3,
            "answer": "needs_review",
            "reason": "Cannot evaluate appropriateness - no common name identified"
        }
    
    # First check if it's a standard common name in CFCS/CSI
    is_standard, source = is_standard_common_name(common_name)
    if is_standard:
        return {
            "question_id": 3,
            "answer": "pass",
            "reason": f"Common name '{common_name}' is a standard name found in {source} database."
        }
    
    # Not a standard name - use GPT to evaluate appropriateness
    fields = label_facts.get("fields", {}) or {}
    first_ingredient = None
    for key in ["ingredients_list_en", "ingredients_list_fr"]:
        if key in fields:
            ing_data = fields[key]
            ing_text = ing_data.get("text", "") if isinstance(ing_data, dict) else str(ing_data)
            first_ingredient = extract_first_ingredient(ing_text)
            if first_ingredient:
                break
    
    try:
        client = OpenAI(api_key=api_key)
        
        system_prompt = """You are a CFIA (Canadian Food Inspection Agency) food labelling expert.
        
Evaluate if the given common name is appropriate for a food product according to CFIA guidelines.

An appropriate common name is:
- As prescribed by any regulation
- The name by which the food is generally known
- A name that is not generic and that describes the food
- If the food is likely to be mistaken for another food, includes words that describe the food's true nature

Respond with ONLY one of:
- "yes" if the common name is appropriate
- "no" if the common name is not appropriate  
- "uncertain" if you cannot determine appropriateness

Then provide a brief rationale on the next line."""

        user_prompt = f"""Common Name: {common_name}
First Ingredient: {first_ingredient or 'Unknown'}

Is this an appropriate common name for this food product?"""

        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0,
            max_tokens=200
        )
        
        response_text = response.choices[0].message.content.strip()
        lines = response_text.split("\n", 1)
        answer_line = lines[0].lower().strip()
        rationale = lines[1].strip() if len(lines) > 1 else "No rationale provided"
        
        if "yes" in answer_line:
            return {
                "question_id": 3,
                "answer": "pass",
                "reason": f"Common name '{common_name}' is appropriate. {rationale}"
            }
        elif "no" in answer_line:
            return {
                "question_id": 3,
                "answer": "fail",
                "reason": f"Common name '{common_name}' may not be appropriate. {rationale}"
            }
        else:
            return {
                "question_id": 3,
                "answer": "needs_review",
                "reason": f"Cannot determine if '{common_name}' is appropriate. {rationale}"
            }
            
    except Exception as e:
        return {
            "question_id": 3,
            "answer": "needs_review",
            "reason": f"Could not evaluate common name appropriateness: {str(e)}"
        }


def evaluate_common_name(
    label_facts: Dict[str, Any],
    tags: Optional[List[str]] = None,
    api_key: Optional[str] = None
) -> Dict[str, Any]:
    """
    Evaluate all common name compliance questions.
    
    Args:
        label_facts: DocAI extracted label facts
        tags: List of image tags (e.g., ["front", "back"])
        api_key: OpenAI API key (optional, uses env var if not provided)
    
    Returns:
        Dictionary with evaluation results
    """
    # Load CFIA common names database
    cfia_names = load_cfia_common_names()
    
    # Run all checks
    results = []
    
    # Q1: Is common name present?
    q1_result = check_common_name_present(label_facts, cfia_names)
    results.append(q1_result)
    
    # Q2: Is common name on PDP?
    q2_result = check_common_name_on_pdp(label_facts, tags)
    results.append(q2_result)
    
    # Q3: Is it appropriate? (GPT check)
    q3_result = check_appropriate_common_name(label_facts, api_key)
    results.append(q3_result)
    
    # Calculate overall status
    overall_status = "pass"
    for r in results:
        if r["answer"] == "fail":
            overall_status = "fail"
            break
        elif r["answer"] == "needs_review" and overall_status != "fail":
            overall_status = "needs_review"
    
    # Get the common name for reference
    common_name, confidence, is_flagged = get_best_common_name(label_facts)
    
    return {
        "attribute": "common_name",
        "extracted_value": common_name or "",
        "extraction_confidence": confidence,
        "flagged": is_flagged,
        "results": results,
        "overall_status": overall_status,
        "questions_count": len(results)
    }


if __name__ == "__main__":
    # Test with sample data
    import sys
    
    print("=" * 60)
    print("Common Name Hardcoded Compliance Test")
    print("=" * 60)
    
    # Check for API key
    if not os.environ.get("OPENAI_API_KEY"):
        print("WARNING: OPENAI_API_KEY not set - Q3 will fail")
    
    # Try to load extracted_facts.json for testing
    test_file = Path(__file__).parent.parent / "extracted_facts.json"
    if test_file.exists():
        with open(test_file, 'r', encoding='utf-8') as f:
            label_facts = json.load(f)
        
        print(f"Loaded test data from: {test_file}")
        print("-" * 60)
        
        result = evaluate_common_name(label_facts, tags=["front"])
        print(json.dumps(result, indent=2))
    else:
        print(f"Test file not found: {test_file}")
        sys.exit(1)
