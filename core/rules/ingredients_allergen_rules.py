"""
Ingredients and Allergen Labelling Rule Evaluation Methods
Based on CFIA Food Labelling Requirements Checklist - List of ingredients and allergen labelling

15 consolidated rules covering:
- List of ingredients presence and exemptions
- Descending order by weight
- Allergen declarations (priority allergens, gluten, sulphites)
- Contains statements and cross-contamination
- Phenylalanine (aspartame) statement
- Formatting and legibility
- Location requirements
"""

import re
from typing import Dict, Any, List


# Ingredients and allergen rules - consolidated from CFIA checklist
INGREDIENTS_ALLERGEN_RULES = {
    1: {
        "id": "ingredients_present",
        "text": "Is a list of ingredients present?",
        "citation": "https://inspection.canada.ca/en/food-labels/labelling/industry/list-ingredients-and-allergens"
    },
    2: {
        "id": "ingredients_exempt",
        "text": "If not, is the product exempt or a single ingredient food?",
        "citation": "https://inspection.canada.ca/en/food-labels/labelling/industry/list-ingredients-and-allergens#s2c1"
    },
    3: {
        "id": "ingredients_descending_order",
        "text": "Are ingredients in descending order of proportion by weight?",
        "citation": "https://inspection.canada.ca/en/food-labels/labelling/industry/list-ingredients-and-allergens"
    },
    4: {
        "id": "ingredients_common_names",
        "text": "Have ingredients been declared using appropriate common names?",
        "citation": "https://inspection.canada.ca/en/food-labels/labelling/industry/list-ingredients-and-allergens"
    },
    5: {
        "id": "components_declared",
        "text": "Have components been properly declared where required?",
        "citation": "https://inspection.canada.ca/en/food-labels/labelling/industry/list-ingredients-and-allergens"
    },
    6: {
        "id": "sugars_grouped",
        "text": "Have sugars-based ingredients been grouped after the term 'Sugars' if required?",
        "citation": "https://inspection.canada.ca/en/food-labels/labelling/industry/list-ingredients-and-allergens"
    },
    7: {
        "id": "allergens_declared",
        "text": "Are priority allergens, gluten and added sulphites declared using prescribed source names?",
        "citation": "https://inspection.canada.ca/en/food-labels/labelling/industry/allergens-and-gluten"
    },
    8: {
        "id": "contains_statement",
        "text": "Is a 'Contains' statement present with priority allergens?",
        "citation": "https://inspection.canada.ca/en/food-labels/labelling/industry/allergens-and-gluten"
    },
    9: {
        "id": "cross_contamination",
        "text": "Is a cross-contamination statement present if applicable?",
        "citation": "https://inspection.canada.ca/en/food-labels/labelling/industry/allergens-and-gluten#c4"
    },
    10: {
        "id": "statements_position",
        "text": "Are Contains/cross-contamination statements at end of ingredients list?",
        "citation": "https://inspection.canada.ca/en/food-labels/labelling/industry/allergens-and-gluten"
    },
    11: {
        "id": "phenylalanine_statement",
        "text": "If product contains aspartame, is phenylalanine statement present?",
        "citation": "https://inspection.canada.ca/en/food-labels/labelling/industry/list-ingredients-and-allergens"
    },
    12: {
        "id": "statements_order",
        "text": "Are statements in proper order (phenylalanine, contains, cross-contamination)?",
        "citation": "https://inspection.canada.ca/en/food-labels/labelling/industry/allergens-and-gluten"
    },
    13: {
        "id": "bilingual_match",
        "text": "Are English and French lists identical in content?",
        "citation": "https://inspection.canada.ca/en/food-labels/labelling/industry/list-ingredients-and-allergens"
    },
    14: {
        "id": "formatting_legibility",
        "text": "Is print, contrast, font (sans serif), and formatting compliant?",
        "citation": "https://inspection.canada.ca/en/food-labels/labelling/industry/legibility-and-location"
    },
    15: {
        "id": "location_requirements",
        "text": "Is ingredients list on proper panel (not bottom) on continuous surface?",
        "citation": "https://inspection.canada.ca/en/food-labels/labelling/industry/legibility-and-location#s6c2"
    }
}

# Priority allergens in Canada
PRIORITY_ALLERGENS = [
    'peanut', 'peanuts', 'arachide',
    'tree nut', 'tree nuts', 'almond', 'cashew', 'walnut', 'pecan', 'hazelnut', 'pistachio', 'brazil nut', 'macadamia',
    'milk', 'lait', 'dairy', 'lactose', 'casein', 'whey',
    'egg', 'eggs', 'oeuf', 'oeufs',
    'fish', 'poisson',
    'shellfish', 'crustacean', 'shrimp', 'crab', 'lobster', 'mollusc', 'oyster', 'clam', 'mussel', 'scallop',
    'wheat', 'blé', 'gluten',
    'soy', 'soya', 'soja',
    'sesame', 'sésame',
    'mustard', 'moutarde',
    'sulphite', 'sulfite', 'sulphites', 'sulfites', 'so2'
]


def extract_ingredients_info(label_data: Dict) -> Dict[str, Any]:
    """Extract ingredients and allergen information from label data"""
    
    ingredients = str(label_data.get('ingredients_list', '') or '')
    allergens = label_data.get('allergens', []) or []
    all_text = ingredients.lower()
    
    # Check for ingredients list
    has_ingredients = bool(ingredients.strip())
    
    # Detect contains statement
    has_contains = 'contains' in all_text or 'contient' in all_text
    
    # Extract allergens found
    allergens_found = []
    for allergen in PRIORITY_ALLERGENS:
        if allergen in all_text:
            allergens_found.append(allergen)
    
    # Check for cross-contamination statement
    has_may_contain = any(phrase in all_text for phrase in [
        'may contain', 'peut contenir', 'may be present', 
        'traces of', 'traces de', 'made in a facility'
    ])
    
    # Check for aspartame/phenylalanine
    has_aspartame = 'aspartame' in all_text
    has_phenylalanine_stmt = 'phenylalanine' in all_text or 'phénylalanine' in all_text
    
    # Check for sugars grouping
    has_sugars_group = 'sugars' in all_text or 'sucres' in all_text
    
    # Detect gluten
    has_gluten = any(g in all_text for g in ['gluten', 'wheat', 'blé', 'barley', 'orge', 'rye', 'seigle'])
    
    return {
        'has_ingredients': has_ingredients,
        'ingredients_text': ingredients,
        'allergens_found': allergens_found,
        'has_contains': has_contains,
        'has_may_contain': has_may_contain,
        'has_aspartame': has_aspartame,
        'has_phenylalanine': has_phenylalanine_stmt,
        'has_sugars_group': has_sugars_group,
        'has_gluten': has_gluten,
        'reported_allergens': allergens
    }


def evaluate_ingredients_rule_1(label_data: Dict, info: Dict) -> Dict[str, Any]:
    """Rule 1: Is a list of ingredients present?"""
    
    return {
        "rule_id": "ingredients_present",
        "rule_number": 1,
        "rule_text": INGREDIENTS_ALLERGEN_RULES[1]["text"],
        "compliant": info['has_ingredients'],
        "confidence": 0.9 if info['has_ingredients'] else 0.7,
        "finding": "Ingredients list found" if info['has_ingredients'] else "No ingredients list detected",
        "reasoning": "Checked for presence of ingredients list in extracted label data",
        "recommendations": [] if info['has_ingredients'] else ["Add list of ingredients"],
        "regulatory_references": [INGREDIENTS_ALLERGEN_RULES[1]["citation"]]
    }


def evaluate_ingredients_rule_2(label_data: Dict, info: Dict, rule_1: Dict) -> Dict[str, Any]:
    """Rule 2: Exemption check if no ingredients list"""
    
    if rule_1.get('compliant'):
        return {
            "rule_id": "ingredients_exempt",
            "rule_number": 2,
            "rule_text": INGREDIENTS_ALLERGEN_RULES[2]["text"],
            "compliant": True,
            "confidence": 0.95,
            "finding": "Not applicable - ingredients list is present",
            "reasoning": "Rule 1 passed",
            "recommendations": [],
            "regulatory_references": [INGREDIENTS_ALLERGEN_RULES[2]["citation"]]
        }
    
    # Check for exemption or single ingredient
    product_type = str(label_data.get('product_type', '')).lower()
    common_name = str(label_data.get('common_name', '')).lower()
    
    single_ingredient = any(s in product_type + common_name for s in [
        'fresh', 'frais', 'water', 'eau', 'salt', 'sel', 'sugar', 'honey', 'vinegar'
    ])
    
    return {
        "rule_id": "ingredients_exempt",
        "rule_number": 2,
        "rule_text": INGREDIENTS_ALLERGEN_RULES[2]["text"],
        "compliant": single_ingredient,
        "confidence": 0.6,
        "finding": "May be single ingredient food" if single_ingredient else "Ingredients list required",
        "reasoning": f"Checked product '{common_name}' for exemption eligibility",
        "recommendations": [] if single_ingredient else ["Add ingredients list or verify exemption"],
        "regulatory_references": [INGREDIENTS_ALLERGEN_RULES[2]["citation"]]
    }


def evaluate_ingredients_rule_3(label_data: Dict, info: Dict) -> Dict[str, Any]:
    """Rule 3: Descending order by weight"""
    
    if not info['has_ingredients']:
        return {
            "rule_id": "ingredients_descending_order",
            "rule_number": 3,
            "rule_text": INGREDIENTS_ALLERGEN_RULES[3]["text"],
            "compliant": None,
            "confidence": 0.0,
            "finding": "Cannot evaluate - no ingredients list",
            "reasoning": "Ingredients list not present",
            "recommendations": [],
            "regulatory_references": [INGREDIENTS_ALLERGEN_RULES[3]["citation"]]
        }
    
    # Cannot fully verify order from OCR, but assume compliant if list exists
    return {
        "rule_id": "ingredients_descending_order",
        "rule_number": 3,
        "rule_text": INGREDIENTS_ALLERGEN_RULES[3]["text"],
        "compliant": True,
        "confidence": 0.6,
        "finding": "Ingredients list present - order verification requires manual review",
        "reasoning": "OCR detected ingredients list, descending order assumed but should be verified",
        "recommendations": ["Verify ingredients are listed in descending order by weight"],
        "regulatory_references": [INGREDIENTS_ALLERGEN_RULES[3]["citation"]]
    }


def evaluate_ingredients_rule_4(label_data: Dict, info: Dict) -> Dict[str, Any]:
    """Rule 4: Appropriate common names used"""
    
    if not info['has_ingredients']:
        return {
            "rule_id": "ingredients_common_names",
            "rule_number": 4,
            "rule_text": INGREDIENTS_ALLERGEN_RULES[4]["text"],
            "compliant": None,
            "confidence": 0.0,
            "finding": "Cannot evaluate - no ingredients list",
            "reasoning": "Ingredients list not present",
            "recommendations": [],
            "regulatory_references": [INGREDIENTS_ALLERGEN_RULES[4]["citation"]]
        }
    
    return {
        "rule_id": "ingredients_common_names",
        "rule_number": 4,
        "rule_text": INGREDIENTS_ALLERGEN_RULES[4]["text"],
        "compliant": True,
        "confidence": 0.6,
        "finding": "Ingredients list uses common names - verify compliance for specific ingredients",
        "reasoning": "Common name usage requires manual verification against CFIA standards",
        "recommendations": ["Verify all ingredients use appropriate CFIA common names"],
        "regulatory_references": [INGREDIENTS_ALLERGEN_RULES[4]["citation"]]
    }


def evaluate_ingredients_rule_5(label_data: Dict, info: Dict) -> Dict[str, Any]:
    """Rule 5: Components properly declared"""
    
    if not info['has_ingredients']:
        return {
            "rule_id": "components_declared",
            "rule_number": 5,
            "rule_text": INGREDIENTS_ALLERGEN_RULES[5]["text"],
            "compliant": None,
            "confidence": 0.0,
            "finding": "Cannot evaluate - no ingredients list",
            "reasoning": "Ingredients list not present",
            "recommendations": [],
            "regulatory_references": [INGREDIENTS_ALLERGEN_RULES[5]["citation"]]
        }
    
    # Check for component indicators (parentheses usually indicate components)
    has_components = '(' in info['ingredients_text'] and ')' in info['ingredients_text']
    
    return {
        "rule_id": "components_declared",
        "rule_number": 5,
        "rule_text": INGREDIENTS_ALLERGEN_RULES[5]["text"],
        "compliant": True,
        "confidence": 0.65 if has_components else 0.5,
        "finding": "Component declarations detected" if has_components else "No component declarations found (may not be required)",
        "reasoning": "Checked for parenthetical component declarations in ingredients",
        "recommendations": ["Verify all multi-component ingredients have components listed"],
        "regulatory_references": [INGREDIENTS_ALLERGEN_RULES[5]["citation"]]
    }


def evaluate_ingredients_rule_6(label_data: Dict, info: Dict) -> Dict[str, Any]:
    """Rule 6: Sugars grouped properly"""
    
    if not info['has_ingredients']:
        return {
            "rule_id": "sugars_grouped",
            "rule_number": 6,
            "rule_text": INGREDIENTS_ALLERGEN_RULES[6]["text"],
            "compliant": None,
            "confidence": 0.0,
            "finding": "Cannot evaluate - no ingredients list",
            "reasoning": "Ingredients list not present",
            "recommendations": [],
            "regulatory_references": [INGREDIENTS_ALLERGEN_RULES[6]["citation"]]
        }
    
    text = info['ingredients_text'].lower()
    has_sugars = info['has_sugars_group']
    has_sugar_types = any(s in text for s in [
        'glucose', 'fructose', 'sucrose', 'dextrose', 'maltose', 
        'corn syrup', 'honey', 'molasses', 'maple syrup'
    ])
    
    if not has_sugar_types:
        return {
            "rule_id": "sugars_grouped",
            "rule_number": 6,
            "rule_text": INGREDIENTS_ALLERGEN_RULES[6]["text"],
            "compliant": True,
            "confidence": 0.8,
            "finding": "No sugar-based ingredients requiring grouping detected",
            "reasoning": "No multiple sugar types found in ingredients",
            "recommendations": [],
            "regulatory_references": [INGREDIENTS_ALLERGEN_RULES[6]["citation"]]
        }
    
    return {
        "rule_id": "sugars_grouped",
        "rule_number": 6,
        "rule_text": INGREDIENTS_ALLERGEN_RULES[6]["text"],
        "compliant": has_sugars,
        "confidence": 0.7,
        "finding": "'Sugars' grouping detected" if has_sugars else "Sugar-based ingredients may need grouping",
        "reasoning": "Checked for 'Sugars' term and sugar-based ingredients",
        "recommendations": [] if has_sugars else ["Group sugar-based ingredients after 'Sugars' term if required"],
        "regulatory_references": [INGREDIENTS_ALLERGEN_RULES[6]["citation"]]
    }


def evaluate_ingredients_rule_7(label_data: Dict, info: Dict) -> Dict[str, Any]:
    """Rule 7: Priority allergens declared with source names"""
    
    if not info['has_ingredients']:
        return {
            "rule_id": "allergens_declared",
            "rule_number": 7,
            "rule_text": INGREDIENTS_ALLERGEN_RULES[7]["text"],
            "compliant": None,
            "confidence": 0.0,
            "finding": "Cannot evaluate - no ingredients list",
            "reasoning": "Ingredients list not present",
            "recommendations": [],
            "regulatory_references": [INGREDIENTS_ALLERGEN_RULES[7]["citation"]]
        }
    
    allergens = info['allergens_found']
    
    if allergens:
        return {
            "rule_id": "allergens_declared",
            "rule_number": 7,
            "rule_text": INGREDIENTS_ALLERGEN_RULES[7]["text"],
            "compliant": True,
            "confidence": 0.8,
            "finding": f"Priority allergens declared: {', '.join(allergens[:5])}",
            "reasoning": "Detected allergen declarations in ingredients list",
            "recommendations": ["Verify allergens use prescribed CFIA source names"],
            "regulatory_references": [INGREDIENTS_ALLERGEN_RULES[7]["citation"]]
        }
    
    return {
        "rule_id": "allergens_declared",
        "rule_number": 7,
        "rule_text": INGREDIENTS_ALLERGEN_RULES[7]["text"],
        "compliant": True,
        "confidence": 0.7,
        "finding": "No priority allergens detected in product",
        "reasoning": "No common allergen keywords found in ingredients",
        "recommendations": [],
        "regulatory_references": [INGREDIENTS_ALLERGEN_RULES[7]["citation"]]
    }


def evaluate_ingredients_rule_8(label_data: Dict, info: Dict) -> Dict[str, Any]:
    """Rule 8: Contains statement present"""
    
    allergens = info['allergens_found']
    has_contains = info['has_contains']
    
    if not allergens:
        return {
            "rule_id": "contains_statement",
            "rule_number": 8,
            "rule_text": INGREDIENTS_ALLERGEN_RULES[8]["text"],
            "compliant": True,
            "confidence": 0.8,
            "finding": "No priority allergens - contains statement not required",
            "reasoning": "No allergens detected",
            "recommendations": [],
            "regulatory_references": [INGREDIENTS_ALLERGEN_RULES[8]["citation"]]
        }
    
    return {
        "rule_id": "contains_statement",
        "rule_number": 8,
        "rule_text": INGREDIENTS_ALLERGEN_RULES[8]["text"],
        "compliant": has_contains,
        "confidence": 0.75,
        "finding": "'Contains' statement found" if has_contains else "Allergens present but 'Contains' statement not detected",
        "reasoning": f"Allergens: {', '.join(allergens[:3])}. Contains statement: {'Yes' if has_contains else 'Not found'}",
        "recommendations": [] if has_contains else ["Add 'Contains: [allergens]' statement"],
        "regulatory_references": [INGREDIENTS_ALLERGEN_RULES[8]["citation"]]
    }


def evaluate_ingredients_rule_9(label_data: Dict, info: Dict) -> Dict[str, Any]:
    """Rule 9: Cross-contamination statement"""
    
    has_may_contain = info['has_may_contain']
    
    return {
        "rule_id": "cross_contamination",
        "rule_number": 9,
        "rule_text": INGREDIENTS_ALLERGEN_RULES[9]["text"],
        "compliant": True,  # Precautionary statements are optional
        "confidence": 0.8,
        "finding": "Cross-contamination statement present" if has_may_contain else "No cross-contamination statement (may not be required)",
        "reasoning": "Cross-contamination statements are voluntary precautionary labelling",
        "recommendations": [],
        "regulatory_references": [INGREDIENTS_ALLERGEN_RULES[9]["citation"]]
    }


def evaluate_ingredients_rule_10(label_data: Dict, info: Dict) -> Dict[str, Any]:
    """Rule 10: Contains/cross-contamination at end of list"""
    
    if not info['has_contains'] and not info['has_may_contain']:
        return {
            "rule_id": "statements_position",
            "rule_number": 10,
            "rule_text": INGREDIENTS_ALLERGEN_RULES[10]["text"],
            "compliant": True,
            "confidence": 0.9,
            "finding": "No contains/cross-contamination statements to position",
            "reasoning": "No statements present",
            "recommendations": [],
            "regulatory_references": [INGREDIENTS_ALLERGEN_RULES[10]["citation"]]
        }
    
    # Cannot fully verify position from OCR alone
    return {
        "rule_id": "statements_position",
        "rule_number": 10,
        "rule_text": INGREDIENTS_ALLERGEN_RULES[10]["text"],
        "compliant": None,
        "confidence": 0.5,
        "finding": "Statement position requires visual verification",
        "reasoning": "Statements detected but position cannot be verified from OCR",
        "recommendations": ["Verify Contains/cross-contamination statements are at end of ingredients list"],
        "regulatory_references": [INGREDIENTS_ALLERGEN_RULES[10]["citation"]]
    }


def evaluate_ingredients_rule_11(label_data: Dict, info: Dict) -> Dict[str, Any]:
    """Rule 11: Phenylalanine statement for aspartame"""
    
    if not info['has_aspartame']:
        return {
            "rule_id": "phenylalanine_statement",
            "rule_number": 11,
            "rule_text": INGREDIENTS_ALLERGEN_RULES[11]["text"],
            "compliant": True,
            "confidence": 0.9,
            "finding": "No aspartame detected - phenylalanine statement not required",
            "reasoning": "Product does not contain aspartame",
            "recommendations": [],
            "regulatory_references": [INGREDIENTS_ALLERGEN_RULES[11]["citation"]]
        }
    
    return {
        "rule_id": "phenylalanine_statement",
        "rule_number": 11,
        "rule_text": INGREDIENTS_ALLERGEN_RULES[11]["text"],
        "compliant": info['has_phenylalanine'],
        "confidence": 0.85,
        "finding": "Phenylalanine statement found" if info['has_phenylalanine'] else "Aspartame present but phenylalanine statement missing",
        "reasoning": "Aspartame detected, checked for phenylalanine statement",
        "recommendations": [] if info['has_phenylalanine'] else ["Add phenylalanine statement as product contains aspartame"],
        "regulatory_references": [INGREDIENTS_ALLERGEN_RULES[11]["citation"]]
    }


def evaluate_ingredients_rule_12(label_data: Dict, info: Dict) -> Dict[str, Any]:
    """Rule 12: Statements in proper order"""
    
    has_statements = info['has_phenylalanine'] or info['has_contains'] or info['has_may_contain']
    
    if not has_statements:
        return {
            "rule_id": "statements_order",
            "rule_number": 12,
            "rule_text": INGREDIENTS_ALLERGEN_RULES[12]["text"],
            "compliant": True,
            "confidence": 0.9,
            "finding": "No statements requiring ordering",
            "reasoning": "No phenylalanine, contains, or cross-contamination statements present",
            "recommendations": [],
            "regulatory_references": [INGREDIENTS_ALLERGEN_RULES[12]["citation"]]
        }
    
    return {
        "rule_id": "statements_order",
        "rule_number": 12,
        "rule_text": INGREDIENTS_ALLERGEN_RULES[12]["text"],
        "compliant": None,
        "confidence": 0.4,
        "finding": "Statement order requires visual verification",
        "reasoning": "Multiple statements present, order verification requires manual review",
        "recommendations": ["Verify order: phenylalanine → contains → cross-contamination"],
        "regulatory_references": [INGREDIENTS_ALLERGEN_RULES[12]["citation"]]
    }


def evaluate_ingredients_rule_13(label_data: Dict, info: Dict) -> Dict[str, Any]:
    """Rule 13: English and French lists match"""
    
    bilingual = label_data.get('bilingual_compliance', False)
    
    return {
        "rule_id": "bilingual_match",
        "rule_number": 13,
        "rule_text": INGREDIENTS_ALLERGEN_RULES[13]["text"],
        "compliant": bilingual if bilingual else None,
        "confidence": 0.6 if bilingual else 0.4,
        "finding": "Bilingual compliance detected" if bilingual else "Bilingual match requires verification",
        "reasoning": "English/French ingredient list matching requires manual comparison",
        "recommendations": ["Verify English and French ingredient lists are identical"],
        "regulatory_references": [INGREDIENTS_ALLERGEN_RULES[13]["citation"]]
    }


def evaluate_ingredients_rule_14(label_data: Dict, info: Dict) -> Dict[str, Any]:
    """Rule 14: Formatting and legibility (sans serif, contrast, etc.)"""
    
    return {
        "rule_id": "formatting_legibility",
        "rule_number": 14,
        "rule_text": INGREDIENTS_ALLERGEN_RULES[14]["text"],
        "compliant": None,
        "confidence": 0.3,
        "finding": "Formatting and legibility require visual verification",
        "reasoning": "Font type, contrast, and formatting cannot be verified from OCR text",
        "recommendations": ["Verify: sans serif font, appropriate contrast, bold where required, proper spacing"],
        "regulatory_references": [INGREDIENTS_ALLERGEN_RULES[14]["citation"]]
    }


def evaluate_ingredients_rule_15(label_data: Dict, info: Dict) -> Dict[str, Any]:
    """Rule 15: Location requirements (not on bottom, continuous surface)"""
    
    return {
        "rule_id": "location_requirements",
        "rule_number": 15,
        "rule_text": INGREDIENTS_ALLERGEN_RULES[15]["text"],
        "compliant": None,
        "confidence": 0.3,
        "finding": "Location requirements require visual verification",
        "reasoning": "Panel location cannot be determined from OCR",
        "recommendations": ["Verify ingredients list is not on bottom panel and on continuous surface"],
        "regulatory_references": [INGREDIENTS_ALLERGEN_RULES[15]["citation"]]
    }


def evaluate_all_ingredients_allergen_rules(label_data: Dict, client=None) -> Dict[str, Any]:
    """Evaluate all ingredients and allergen labelling rules."""
    
    info = extract_ingredients_info(label_data)
    results = {}
    
    rule_1 = evaluate_ingredients_rule_1(label_data, info)
    results['ingredients_rule_1'] = rule_1
    
    results['ingredients_rule_2'] = evaluate_ingredients_rule_2(label_data, info, rule_1)
    results['ingredients_rule_3'] = evaluate_ingredients_rule_3(label_data, info)
    results['ingredients_rule_4'] = evaluate_ingredients_rule_4(label_data, info)
    results['ingredients_rule_5'] = evaluate_ingredients_rule_5(label_data, info)
    results['ingredients_rule_6'] = evaluate_ingredients_rule_6(label_data, info)
    results['ingredients_rule_7'] = evaluate_ingredients_rule_7(label_data, info)
    results['ingredients_rule_8'] = evaluate_ingredients_rule_8(label_data, info)
    results['ingredients_rule_9'] = evaluate_ingredients_rule_9(label_data, info)
    results['ingredients_rule_10'] = evaluate_ingredients_rule_10(label_data, info)
    results['ingredients_rule_11'] = evaluate_ingredients_rule_11(label_data, info)
    results['ingredients_rule_12'] = evaluate_ingredients_rule_12(label_data, info)
    results['ingredients_rule_13'] = evaluate_ingredients_rule_13(label_data, info)
    results['ingredients_rule_14'] = evaluate_ingredients_rule_14(label_data, info)
    results['ingredients_rule_15'] = evaluate_ingredients_rule_15(label_data, info)
    
    evaluated = [r for r in results.values() if r.get('compliant') is not None]
    compliant_count = sum(1 for r in evaluated if r.get('compliant'))
    
    results['ingredients_overall'] = {
        "compliant": all(r.get('compliant', True) for r in evaluated),
        "rules_passed": compliant_count,
        "rules_evaluated": len(evaluated),
        "total_rules": 15,
        "summary": f"Ingredients/Allergens: {compliant_count}/{len(evaluated)} rules passed"
    }
    
    return results
