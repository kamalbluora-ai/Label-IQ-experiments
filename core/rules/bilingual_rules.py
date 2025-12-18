"""
Bilingual Requirements Rule Evaluation Methods
Based on CFIA Food Labelling Requirements Checklist - Bilingual Requirements section

Rules:
1. Is all mandatory information in English and French?
2. If not, does a bilingual exemption apply?
"""

import json
from typing import Dict, Any, List
from pathlib import Path


# Bilingual rules from CFIA checklist
BILINGUAL_RULES = {
    1: {
        "id": "bilingual_all_mandatory_info",
        "text": "Is all mandatory information referred to in this checklist in English and French, except the responsible person's name and address which may be in either French or English?",
        "citation": "https://inspection.canada.ca/en/food-labels/labelling/industry/bilingual-food-labelling"
    },
    2: {
        "id": "bilingual_exemption",
        "text": "If not, does a bilingual exemption apply (prepackaged other than consumer prepackaged container destined to a commercial or industrial enterprise, specialty food, local food, test market food)?",
        "citation": "https://inspection.canada.ca/en/food-labels/labelling/industry/bilingual-food-labelling#s2c1"
    }
}

# Bilingual exemption categories
BILINGUAL_EXEMPTIONS = [
    "commercial or industrial enterprise",
    "specialty food",
    "local food", 
    "test market food",
    "prepackaged product other than consumer prepackaged"
]


def evaluate_bilingual_rule_1(label_data: Dict, client) -> Dict[str, Any]:
    """
    Rule 1: Is all mandatory information in English and French?
    
    Checks:
    - Common name in both languages
    - Ingredients list in both languages
    - Net quantity in both languages
    - Nutrition facts in both languages (if applicable)
    """
    
    # Extract relevant fields
    bilingual_flag = label_data.get('bilingual_compliance', 'unknown')
    
    # Look for French indicators in OCR text
    french_indicators = []
    english_indicators = []
    
    # Check common name
    common_name = label_data.get('common_name', '')
    
    # Check ingredients
    ingredients = label_data.get('ingredients_list', '')
    has_french_ingredients = any(word in str(ingredients).lower() for word in 
        ['ingrédients', 'sucre', 'sel', 'farine', 'huile', 'eau', 'lait'])
    has_english_ingredients = any(word in str(ingredients).lower() for word in 
        ['ingredients', 'sugar', 'salt', 'flour', 'oil', 'water', 'milk'])
    
    # Check nutrition facts
    nutrition = label_data.get('nutrition_facts', '')
    has_french_nutrition = any(word in str(nutrition).lower() for word in 
        ['valeur nutritive', 'lipides', 'glucides', 'protéines', 'calories'])
    has_english_nutrition = any(word in str(nutrition).lower() for word in 
        ['nutrition facts', 'fat', 'carbohydrate', 'protein', 'calories'])
    
    # Aggregate findings
    findings = []
    compliant = True
    
    if has_french_ingredients and has_english_ingredients:
        findings.append("Ingredients list present in both English and French")
    elif has_english_ingredients and not has_french_ingredients:
        findings.append("Ingredients list appears to be English only - French may be missing")
        compliant = False
    elif has_french_ingredients and not has_english_ingredients:
        findings.append("Ingredients list appears to be French only - English may be missing")
        compliant = False
    
    if has_french_nutrition and has_english_nutrition:
        findings.append("Nutrition facts present in both languages")
    elif nutrition and (has_english_nutrition or has_french_nutrition):
        if not has_french_nutrition:
            findings.append("Nutrition facts may be missing French")
        if not has_english_nutrition:
            findings.append("Nutrition facts may be missing English")
    
    # Use AI-reported bilingual status
    if bilingual_flag == True or bilingual_flag == 'true':
        findings.append("AI extraction detected bilingual content")
        confidence = 0.85
    elif bilingual_flag == False or bilingual_flag == 'false':
        findings.append("AI extraction did not detect bilingual content")
        compliant = False
        confidence = 0.75
    else:
        confidence = 0.6
        findings.append("Bilingual status could not be fully determined")
    
    return {
        "rule_id": "bilingual_all_mandatory_info",
        "rule_number": 1,
        "rule_text": BILINGUAL_RULES[1]["text"],
        "compliant": compliant,
        "confidence": confidence,
        "finding": "; ".join(findings) if findings else "Unable to determine bilingual compliance",
        "reasoning": f"Evaluated presence of French and English in mandatory label elements. French ingredients: {has_french_ingredients}, English ingredients: {has_english_ingredients}",
        "recommendations": [] if compliant else [
            "Ensure all mandatory information appears in both English and French",
            "Common name, ingredients, net quantity, and nutrition facts must be bilingual"
        ],
        "regulatory_references": [BILINGUAL_RULES[1]["citation"]],
        "analysis": {
            "french_ingredients": has_french_ingredients,
            "english_ingredients": has_english_ingredients,
            "french_nutrition": has_french_nutrition,
            "english_nutrition": has_english_nutrition,
            "bilingual_flag": bilingual_flag
        }
    }


def evaluate_bilingual_rule_2(label_data: Dict, rule_1_result: Dict, client) -> Dict[str, Any]:
    """
    Rule 2: If not bilingual, does an exemption apply?
    
    Exemptions include:
    - Prepackaged product destined for commercial/industrial enterprise
    - Specialty food
    - Local food
    - Test market food
    """
    
    # This rule only applies if Rule 1 failed
    if rule_1_result.get('compliant', True):
        return {
            "rule_id": "bilingual_exemption",
            "rule_number": 2,
            "rule_text": BILINGUAL_RULES[2]["text"],
            "compliant": True,
            "confidence": 0.95,
            "finding": "Not applicable - product appears to have bilingual labelling",
            "reasoning": "Rule 1 passed, so exemption evaluation is not required",
            "recommendations": [],
            "regulatory_references": [BILINGUAL_RULES[2]["citation"]],
            "exemption_applicable": False,
            "exemption_type": None
        }
    
    # Check for exemption indicators in label data
    product_type = label_data.get('product_type', '').lower()
    claims = label_data.get('other_claims', [])
    claims_text = ' '.join([str(c).lower() for c in claims])
    
    # Check for exemption categories
    exemption_found = None
    
    if any(term in product_type for term in ['specialty', 'artisan', 'craft']):
        exemption_found = "specialty food"
    elif any(term in product_type for term in ['local', 'farm', 'farmers market']):
        exemption_found = "local food"
    elif 'test' in product_type or 'sample' in product_type:
        exemption_found = "test market food"
    elif 'industrial' in product_type or 'commercial' in product_type:
        exemption_found = "commercial/industrial enterprise"
    
    if exemption_found:
        return {
            "rule_id": "bilingual_exemption",
            "rule_number": 2,
            "rule_text": BILINGUAL_RULES[2]["text"],
            "compliant": True,
            "confidence": 0.7,
            "finding": f"Bilingual exemption may apply: {exemption_found}",
            "reasoning": f"Product type '{product_type}' suggests exemption category",
            "recommendations": [
                "Verify exemption eligibility with CFIA guidelines",
                "Document exemption basis for regulatory compliance"
            ],
            "regulatory_references": [BILINGUAL_RULES[2]["citation"]],
            "exemption_applicable": True,
            "exemption_type": exemption_found
        }
    else:
        return {
            "rule_id": "bilingual_exemption",
            "rule_number": 2,
            "rule_text": BILINGUAL_RULES[2]["text"],
            "compliant": False,
            "confidence": 0.75,
            "finding": "No bilingual exemption appears to apply - product requires bilingual labelling",
            "reasoning": "Product does not appear to fall under any bilingual exemption category",
            "recommendations": [
                "Add French translations for all mandatory label elements",
                "Consult CFIA bilingual labelling requirements",
                "Consider if product qualifies for specialty/local food exemption"
            ],
            "regulatory_references": [BILINGUAL_RULES[2]["citation"]],
            "exemption_applicable": False,
            "exemption_type": None
        }


def evaluate_all_bilingual_rules(label_data: Dict, client=None) -> Dict[str, Any]:
    """
    Evaluate all bilingual requirements rules.
    
    Returns a dictionary with results for each rule.
    """
    
    results = {}
    
    # Evaluate Rule 1
    rule_1 = evaluate_bilingual_rule_1(label_data, client)
    results['bilingual_rule_1'] = rule_1
    
    # Evaluate Rule 2 (depends on Rule 1 result)
    rule_2 = evaluate_bilingual_rule_2(label_data, rule_1, client)
    results['bilingual_rule_2'] = rule_2
    
    # Calculate overall bilingual compliance
    all_compliant = all(r.get('compliant', False) for r in results.values())
    
    results['bilingual_overall'] = {
        "compliant": all_compliant,
        "rules_passed": sum(1 for r in results.values() if r.get('compliant', False)),
        "total_rules": 2,
        "summary": "Bilingual requirements met" if all_compliant else "Bilingual requirements not fully met"
    }
    
    return results
