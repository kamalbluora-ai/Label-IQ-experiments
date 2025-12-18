"""
Irradiation Rule Evaluation Methods
Based on CFIA Food Labelling Requirements Checklist - Irradiation section

6 rules covering:
- Permitted to be irradiated
- Written statement present
- Statement legibility
- International symbol on PDP
- Symbol size requirements
- Irradiated ingredients >10% identified
"""

import re
from typing import Dict, Any, List


# Irradiation rules
IRRADIATION_RULES = {
    1: {
        "id": "irrad_permitted",
        "text": "Is the food permitted to be irradiated?",
        "citation": "https://inspection.canada.ca/en/food-labels/labelling/industry/irradiated-foods#tc_req1"
    },
    2: {
        "id": "irrad_statement",
        "text": "Is written statement present ('irradiated', 'treated with radiation', etc.)?",
        "citation": "https://inspection.canada.ca/en/food-labels/labelling/industry/irradiated-foods"
    },
    3: {
        "id": "irrad_discernible",
        "text": "Is the irradiation statement readily discernible?",
        "citation": "https://inspection.canada.ca/en/food-labels/labelling/industry/irradiated-foods"
    },
    4: {
        "id": "irrad_symbol_pdp",
        "text": "Is the international irradiation symbol on the principal display panel?",
        "citation": "https://inspection.canada.ca/en/food-labels/labelling/industry/irradiated-foods"
    },
    5: {
        "id": "irrad_symbol_size",
        "text": "Does the international symbol meet minimum size requirements?",
        "citation": "https://inspection.canada.ca/en/food-labels/labelling/industry/irradiated-foods"
    },
    6: {
        "id": "irrad_ingredients",
        "text": "Are irradiated ingredients (>10% of product) identified in ingredients list?",
        "citation": "https://inspection.canada.ca/en/food-labels/labelling/industry/irradiated-foods"
    }
}

# Foods permitted to be irradiated in Canada
PERMITTED_IRRADIATED_FOODS = [
    'potato', 'onion', 'wheat', 'flour', 'whole wheat flour',
    'spice', 'dehydrated seasoning', 'ground beef', 'beef',
    'poultry', 'shrimp', 'prawns', 'mangoes'
]


def extract_irradiation_info(label_data: Dict) -> Dict[str, Any]:
    """Extract irradiation information from label data"""
    
    # Get relevant fields
    product_type = str(label_data.get('product_type', '') or '').lower()
    irradiation = str(label_data.get('irradiation', '') or '').lower()
    ingredients = str(label_data.get('ingredients', '') or '').lower()
    all_text = str(label_data.get('extracted_text', '') or '').lower()
    
    combined = irradiation + ' ' + ingredients + ' ' + all_text
    
    # Check for irradiation indicators
    has_irrad_statement = any(stmt in combined for stmt in [
        'irradiated', 'treated with radiation', 'treated by irradiation',
        'irradié', 'traité par irradiation', 'traité aux rayonnements'
    ])
    
    # Check for radura symbol mention
    has_symbol = 'radura' in combined or 'irradiation symbol' in combined
    
    # Check if product is type that can be irradiated
    is_permitted_type = any(food in product_type for food in PERMITTED_IRRADIATED_FOODS)
    
    # Check for irradiated ingredients in list
    has_irrad_ingredient = 'irradiated' in ingredients or 'irradié' in ingredients
    
    return {
        'has_irrad_statement': has_irrad_statement,
        'has_symbol': has_symbol,
        'is_permitted_type': is_permitted_type,
        'has_irrad_ingredient': has_irrad_ingredient,
        'product_type': product_type,
        'irradiation_text': irradiation
    }


def evaluate_irrad_rule_1(label_data: Dict, info: Dict) -> Dict[str, Any]:
    """Rule 1: Is food permitted to be irradiated?"""
    
    has_irrad = info['has_irrad_statement']
    is_permitted = info['is_permitted_type']
    
    if not has_irrad:
        return {
            "rule_id": "irrad_permitted",
            "rule_number": 1,
            "rule_text": IRRADIATION_RULES[1]["text"],
            "compliant": True,
            "confidence": 0.7,
            "finding": "No irradiation indicators detected - appears non-irradiated",
            "reasoning": "Product does not appear to be irradiated",
            "recommendations": [],
            "regulatory_references": [IRRADIATION_RULES[1]["citation"]]
        }
    
    return {
        "rule_id": "irrad_permitted",
        "rule_number": 1,
        "rule_text": IRRADIATION_RULES[1]["text"],
        "compliant": is_permitted if is_permitted else None,
        "confidence": 0.7 if is_permitted else 0.5,
        "finding": f"Irradiated product - type {'appears permitted' if is_permitted else 'verify if permitted'}",
        "reasoning": f"Product type: {info['product_type']}. Only certain foods can be irradiated in Canada.",
        "recommendations": [] if is_permitted else ["Verify product is on permitted irradiation list"],
        "regulatory_references": [IRRADIATION_RULES[1]["citation"]]
    }


def evaluate_irrad_rule_2(label_data: Dict, info: Dict) -> Dict[str, Any]:
    """Rule 2: Is written statement present?"""
    
    has_irrad = info['has_irrad_statement']
    
    # If no irradiation indicators, rule doesn't apply
    if not has_irrad and not info['is_permitted_type']:
        return {
            "rule_id": "irrad_statement",
            "rule_number": 2,
            "rule_text": IRRADIATION_RULES[2]["text"],
            "compliant": True,
            "confidence": 0.7,
            "finding": "Not applicable - product does not appear to be irradiated",
            "reasoning": "No irradiation labeling required for non-irradiated foods",
            "recommendations": [],
            "regulatory_references": [IRRADIATION_RULES[2]["citation"]]
        }
    
    return {
        "rule_id": "irrad_statement",
        "rule_number": 2,
        "rule_text": IRRADIATION_RULES[2]["text"],
        "compliant": has_irrad,
        "confidence": 0.8 if has_irrad else 0.5,
        "finding": "Irradiation statement found" if has_irrad else "Verify irradiation statement present if applicable",
        "reasoning": "Must state 'irradiated', 'treated with radiation', or 'treated by irradiation'",
        "recommendations": [] if has_irrad else ["Add required irradiation statement if food is irradiated"],
        "regulatory_references": [IRRADIATION_RULES[2]["citation"]]
    }


def evaluate_irrad_rule_3(label_data: Dict, info: Dict) -> Dict[str, Any]:
    """Rule 3: Is statement discernible?"""
    
    has_irrad = info['has_irrad_statement']
    
    if not has_irrad:
        return {
            "rule_id": "irrad_discernible",
            "rule_number": 3,
            "rule_text": IRRADIATION_RULES[3]["text"],
            "compliant": None,
            "confidence": 0.0,
            "finding": "Not applicable - no irradiation statement detected",
            "reasoning": "No statement to evaluate",
            "recommendations": [],
            "regulatory_references": [IRRADIATION_RULES[3]["citation"]]
        }
    
    return {
        "rule_id": "irrad_discernible",
        "rule_number": 3,
        "rule_text": IRRADIATION_RULES[3]["text"],
        "compliant": True,
        "confidence": 0.7,
        "finding": "Irradiation statement was readable by OCR - appears discernible",
        "reasoning": "OCR successfully extracted irradiation statement",
        "recommendations": [],
        "regulatory_references": [IRRADIATION_RULES[3]["citation"]]
    }


def evaluate_irrad_rule_4(label_data: Dict, info: Dict) -> Dict[str, Any]:
    """Rule 4: International symbol on PDP"""
    
    has_irrad = info['has_irrad_statement']
    has_symbol = info['has_symbol']
    
    if not has_irrad:
        return {
            "rule_id": "irrad_symbol_pdp",
            "rule_number": 4,
            "rule_text": IRRADIATION_RULES[4]["text"],
            "compliant": None,
            "confidence": 0.0,
            "finding": "Not applicable - product does not appear to be irradiated",
            "reasoning": "Symbol not required for non-irradiated foods",
            "recommendations": [],
            "regulatory_references": [IRRADIATION_RULES[4]["citation"]]
        }
    
    return {
        "rule_id": "irrad_symbol_pdp",
        "rule_number": 4,
        "rule_text": IRRADIATION_RULES[4]["text"],
        "compliant": None,
        "confidence": 0.4,
        "finding": "Symbol location requires visual verification",
        "reasoning": "Cannot verify PDP placement from OCR",
        "recommendations": ["Verify Radura symbol is on principal display panel"],
        "regulatory_references": [IRRADIATION_RULES[4]["citation"]]
    }


def evaluate_irrad_rule_5(label_data: Dict, info: Dict) -> Dict[str, Any]:
    """Rule 5: Symbol size requirements"""
    
    has_irrad = info['has_irrad_statement']
    
    if not has_irrad:
        return {
            "rule_id": "irrad_symbol_size",
            "rule_number": 5,
            "rule_text": IRRADIATION_RULES[5]["text"],
            "compliant": None,
            "confidence": 0.0,
            "finding": "Not applicable - product does not appear to be irradiated",
            "reasoning": "Symbol not required for non-irradiated foods",
            "recommendations": [],
            "regulatory_references": [IRRADIATION_RULES[5]["citation"]]
        }
    
    return {
        "rule_id": "irrad_symbol_size",
        "rule_number": 5,
        "rule_text": IRRADIATION_RULES[5]["text"],
        "compliant": None,
        "confidence": 0.4,
        "finding": "Symbol size requires visual verification",
        "reasoning": "Cannot verify outer diameter from OCR",
        "recommendations": ["Verify Radura symbol meets minimum size requirements"],
        "regulatory_references": [IRRADIATION_RULES[5]["citation"]]
    }


def evaluate_irrad_rule_6(label_data: Dict, info: Dict) -> Dict[str, Any]:
    """Rule 6: Irradiated ingredients identified"""
    
    has_irrad_ingredient = info['has_irrad_ingredient']
    
    return {
        "rule_id": "irrad_ingredients",
        "rule_number": 6,
        "rule_text": IRRADIATION_RULES[6]["text"],
        "compliant": has_irrad_ingredient if has_irrad_ingredient else None,
        "confidence": 0.7 if has_irrad_ingredient else 0.5,
        "finding": "Irradiated ingredient identified" if has_irrad_ingredient else "Verify if any ingredients >10% are irradiated",
        "reasoning": "Irradiated ingredients constituting >10% must be labeled",
        "recommendations": [] if has_irrad_ingredient else ["Verify irradiated ingredients (>10%) are identified"],
        "regulatory_references": [IRRADIATION_RULES[6]["citation"]]
    }


def evaluate_all_irradiation_rules(label_data: Dict, client=None) -> Dict[str, Any]:
    """Evaluate all irradiation rules."""
    
    info = extract_irradiation_info(label_data)
    results = {}
    
    results['irrad_rule_1'] = evaluate_irrad_rule_1(label_data, info)
    results['irrad_rule_2'] = evaluate_irrad_rule_2(label_data, info)
    results['irrad_rule_3'] = evaluate_irrad_rule_3(label_data, info)
    results['irrad_rule_4'] = evaluate_irrad_rule_4(label_data, info)
    results['irrad_rule_5'] = evaluate_irrad_rule_5(label_data, info)
    results['irrad_rule_6'] = evaluate_irrad_rule_6(label_data, info)
    
    evaluated = [r for r in results.values() if r.get('compliant') is not None]
    compliant_count = sum(1 for r in evaluated if r.get('compliant'))
    
    results['irrad_overall'] = {
        "compliant": all(r.get('compliant', True) for r in evaluated),
        "rules_passed": compliant_count,
        "rules_evaluated": len(evaluated),
        "total_rules": 6,
        "summary": f"Irradiation: {compliant_count}/{len(evaluated)} rules passed"
    }
    
    return results
