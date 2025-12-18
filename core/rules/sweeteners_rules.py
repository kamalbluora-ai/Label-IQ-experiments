"""
Sweeteners Rule Evaluation Methods
Based on CFIA Food Labelling Requirements Checklist - Sweeteners section

6 rules covering:
- Aspartame presence
- Phenylalanine statement
- Statement location and formatting
- Table-top sweetener requirements
- Sweetness equivalence declaration
"""

import re
from typing import Dict, Any, List


# Sweeteners rules
SWEETENER_RULES = {
    1: {
        "id": "sweet_aspartame",
        "text": "Is aspartame added to the prepackaged food?",
        "citation": "https://inspection.canada.ca/en/food-labels/labelling/industry/sweeteners"
    },
    2: {
        "id": "sweet_phenylalanine",
        "text": "If aspartame present, is phenylalanine statement present?",
        "citation": "https://inspection.canada.ca/en/food-labels/labelling/industry/sweeteners"
    },
    3: {
        "id": "sweet_statement_location",
        "text": "Does phenylalanine statement appear at end of ingredients list?",
        "citation": "https://inspection.canada.ca/en/food-labels/labelling/industry/sweeteners"
    },
    4: {
        "id": "sweet_statement_bold",
        "text": "Is the phenylalanine statement in bold type?",
        "citation": "https://inspection.canada.ca/en/food-labels/labelling/industry/sweeteners"
    },
    5: {
        "id": "sweet_tabletop",
        "text": "Is the product a table-top sweetener?",
        "citation": "https://inspection.canada.ca/en/food-labels/labelling/industry/sweeteners"
    },
    6: {
        "id": "sweet_equivalence",
        "text": "For table-top sweeteners, is sweetness equivalence statement present?",
        "citation": "https://inspection.canada.ca/en/food-labels/labelling/industry/sweeteners"
    }
}

# Artificial sweeteners
ARTIFICIAL_SWEETENERS = [
    'aspartame', 'sucralose', 'acesulfame-potassium', 'acesulfame potassium',
    'acesulfame-k', 'acesulfame k', 'neotame', 'saccharin', 'stevia',
    'steviol glycosides', 'monk fruit', 'erythritol', 'xylitol', 'sorbitol'
]


def extract_sweetener_info(label_data: Dict) -> Dict[str, Any]:
    """Extract sweetener information from label data"""
    
    # Get relevant fields
    ingredients = str(label_data.get('ingredients', '') or '').lower()
    product_type = str(label_data.get('product_type', '') or '').lower()
    all_text = str(label_data.get('extracted_text', '') or '').lower()
    
    combined = ingredients + ' ' + all_text
    
    # Check for aspartame
    has_aspartame = 'aspartame' in combined
    
    # Check for phenylalanine statement
    has_phenylalanine = any(stmt in combined for stmt in [
        'phenylalanine', 'phenylketonurics', 'contains phenylalanine',
        'source of phenylalanine', 'phénylalanine'
    ])
    
    # Check for other artificial sweeteners
    has_sweeteners = any(sweet in combined for sweet in ARTIFICIAL_SWEETENERS)
    
    # Check if table-top sweetener
    is_tabletop = any(tt in product_type for tt in [
        'sweetener', 'sugar substitute', 'tabletop', 'table-top',
        'édulcorant', 'sucre'
    ])
    
    # Check for sweetness equivalence statement
    has_equivalence = any(eq in combined for eq in [
        'equivalent to', 'equals', 'sweetness of', 'teaspoons of sugar',
        'équivalent', 'cuillères à thé de sucre'
    ])
    
    return {
        'has_aspartame': has_aspartame,
        'has_phenylalanine': has_phenylalanine,
        'has_sweeteners': has_sweeteners,
        'is_tabletop': is_tabletop,
        'has_equivalence': has_equivalence,
        'ingredients': ingredients,
        'product_type': product_type
    }


def evaluate_sweet_rule_1(label_data: Dict, info: Dict) -> Dict[str, Any]:
    """Rule 1: Is aspartame present?"""
    
    has_aspartame = info['has_aspartame']
    
    return {
        "rule_id": "sweet_aspartame",
        "rule_number": 1,
        "rule_text": SWEETENER_RULES[1]["text"],
        "compliant": True,  # Informational
        "confidence": 0.8 if has_aspartame else 0.7,
        "finding": "Aspartame detected in ingredients" if has_aspartame else "Aspartame not detected",
        "reasoning": "Checked ingredients for aspartame",
        "recommendations": [],
        "regulatory_references": [SWEETENER_RULES[1]["citation"]]
    }


def evaluate_sweet_rule_2(label_data: Dict, info: Dict) -> Dict[str, Any]:
    """Rule 2: Phenylalanine statement if aspartame present"""
    
    has_aspartame = info['has_aspartame']
    has_phenylalanine = info['has_phenylalanine']
    
    if not has_aspartame:
        return {
            "rule_id": "sweet_phenylalanine",
            "rule_number": 2,
            "rule_text": SWEETENER_RULES[2]["text"],
            "compliant": True,
            "confidence": 0.7,
            "finding": "Not applicable - no aspartame detected",
            "reasoning": "Phenylalanine statement only required when aspartame is present",
            "recommendations": [],
            "regulatory_references": [SWEETENER_RULES[2]["citation"]]
        }
    
    return {
        "rule_id": "sweet_phenylalanine",
        "rule_number": 2,
        "rule_text": SWEETENER_RULES[2]["text"],
        "compliant": has_phenylalanine,
        "confidence": 0.8 if has_phenylalanine else 0.6,
        "finding": "Phenylalanine statement found" if has_phenylalanine else "Phenylalanine statement not detected",
        "reasoning": "Aspartame requires 'Contains phenylalanine' statement",
        "recommendations": [] if has_phenylalanine else ["Add 'Contains phenylalanine' statement"],
        "regulatory_references": [SWEETENER_RULES[2]["citation"]]
    }


def evaluate_sweet_rule_3(label_data: Dict, info: Dict) -> Dict[str, Any]:
    """Rule 3: Statement at end of ingredients"""
    
    has_aspartame = info['has_aspartame']
    has_phenylalanine = info['has_phenylalanine']
    
    if not has_aspartame or not has_phenylalanine:
        return {
            "rule_id": "sweet_statement_location",
            "rule_number": 3,
            "rule_text": SWEETENER_RULES[3]["text"],
            "compliant": None,
            "confidence": 0.0,
            "finding": "Not applicable - no phenylalanine statement to evaluate",
            "reasoning": "Location check requires phenylalanine statement",
            "recommendations": [],
            "regulatory_references": [SWEETENER_RULES[3]["citation"]]
        }
    
    return {
        "rule_id": "sweet_statement_location",
        "rule_number": 3,
        "rule_text": SWEETENER_RULES[3]["text"],
        "compliant": None,
        "confidence": 0.4,
        "finding": "Statement location requires visual verification",
        "reasoning": "Cannot verify exact placement from OCR",
        "recommendations": ["Verify phenylalanine statement appears at end of ingredients list"],
        "regulatory_references": [SWEETENER_RULES[3]["citation"]]
    }


def evaluate_sweet_rule_4(label_data: Dict, info: Dict) -> Dict[str, Any]:
    """Rule 4: Statement in bold"""
    
    has_aspartame = info['has_aspartame']
    has_phenylalanine = info['has_phenylalanine']
    
    if not has_aspartame or not has_phenylalanine:
        return {
            "rule_id": "sweet_statement_bold",
            "rule_number": 4,
            "rule_text": SWEETENER_RULES[4]["text"],
            "compliant": None,
            "confidence": 0.0,
            "finding": "Not applicable - no phenylalanine statement to evaluate",
            "reasoning": "Bold check requires phenylalanine statement",
            "recommendations": [],
            "regulatory_references": [SWEETENER_RULES[4]["citation"]]
        }
    
    return {
        "rule_id": "sweet_statement_bold",
        "rule_number": 4,
        "rule_text": SWEETENER_RULES[4]["text"],
        "compliant": None,
        "confidence": 0.4,
        "finding": "Bold formatting requires visual verification",
        "reasoning": "Cannot verify bold type from OCR",
        "recommendations": ["Verify phenylalanine statement is in bold type"],
        "regulatory_references": [SWEETENER_RULES[4]["citation"]]
    }


def evaluate_sweet_rule_5(label_data: Dict, info: Dict) -> Dict[str, Any]:
    """Rule 5: Is product a table-top sweetener?"""
    
    is_tabletop = info['is_tabletop']
    
    return {
        "rule_id": "sweet_tabletop",
        "rule_number": 5,
        "rule_text": SWEETENER_RULES[5]["text"],
        "compliant": True,  # Informational
        "confidence": 0.7,
        "finding": f"Product {'appears to be' if is_tabletop else 'does not appear to be'} a table-top sweetener",
        "reasoning": f"Product type: {info['product_type']}",
        "recommendations": [],
        "regulatory_references": [SWEETENER_RULES[5]["citation"]]
    }


def evaluate_sweet_rule_6(label_data: Dict, info: Dict) -> Dict[str, Any]:
    """Rule 6: Sweetness equivalence statement"""
    
    is_tabletop = info['is_tabletop']
    has_sweeteners = info['has_sweeteners']
    has_equivalence = info['has_equivalence']
    
    if not is_tabletop or not has_sweeteners:
        return {
            "rule_id": "sweet_equivalence",
            "rule_number": 6,
            "rule_text": SWEETENER_RULES[6]["text"],
            "compliant": True,
            "confidence": 0.7,
            "finding": "Not applicable - not a table-top sweetener with artificial sweeteners",
            "reasoning": "Equivalence statement only for table-top sweeteners",
            "recommendations": [],
            "regulatory_references": [SWEETENER_RULES[6]["citation"]]
        }
    
    return {
        "rule_id": "sweet_equivalence",
        "rule_number": 6,
        "rule_text": SWEETENER_RULES[6]["text"],
        "compliant": has_equivalence,
        "confidence": 0.7 if has_equivalence else 0.5,
        "finding": "Sweetness equivalence statement found" if has_equivalence else "Verify sweetness equivalence statement present",
        "reasoning": "Table-top sweeteners must declare sugar equivalence",
        "recommendations": [] if has_equivalence else ["Add statement like 'equivalent to X teaspoons of sugar'"],
        "regulatory_references": [SWEETENER_RULES[6]["citation"]]
    }


def evaluate_all_sweetener_rules(label_data: Dict, client=None) -> Dict[str, Any]:
    """Evaluate all sweetener rules."""
    
    info = extract_sweetener_info(label_data)
    results = {}
    
    results['sweet_rule_1'] = evaluate_sweet_rule_1(label_data, info)
    results['sweet_rule_2'] = evaluate_sweet_rule_2(label_data, info)
    results['sweet_rule_3'] = evaluate_sweet_rule_3(label_data, info)
    results['sweet_rule_4'] = evaluate_sweet_rule_4(label_data, info)
    results['sweet_rule_5'] = evaluate_sweet_rule_5(label_data, info)
    results['sweet_rule_6'] = evaluate_sweet_rule_6(label_data, info)
    
    evaluated = [r for r in results.values() if r.get('compliant') is not None]
    compliant_count = sum(1 for r in evaluated if r.get('compliant'))
    
    results['sweet_overall'] = {
        "compliant": all(r.get('compliant', True) for r in evaluated),
        "rules_passed": compliant_count,
        "rules_evaluated": len(evaluated),
        "total_rules": 6,
        "summary": f"Sweeteners: {compliant_count}/{len(evaluated)} rules passed"
    }
    
    return results
