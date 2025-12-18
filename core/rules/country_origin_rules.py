"""
Country of Origin Rule Evaluation Methods
Based on CFIA Food Labelling Requirements Checklist - Country of origin section

5 consolidated rules covering:
- Whether product requires country of origin
- Presence of origin declaration
- Correct format "Product of [Country]"
- Bilingual requirements
- Location and legibility
"""

import re
from typing import Dict, Any, List


# Country of origin rules
COUNTRY_ORIGIN_RULES = {
    1: {
        "id": "origin_required",
        "text": "Does the product require a country of origin declaration?",
        "citation": "https://inspection.canada.ca/en/food-labels/labelling/industry/origin"
    },
    2: {
        "id": "origin_present",
        "text": "Is a country of origin declaration present if required?",
        "citation": "https://inspection.canada.ca/en/food-labels/labelling/industry/origin"
    },
    3: {
        "id": "origin_format",
        "text": "Is the correct format 'Product of [Country]' / 'Produit du/de [Pays]' used?",
        "citation": "https://inspection.canada.ca/en/food-labels/labelling/industry/origin"
    },
    4: {
        "id": "origin_bilingual",
        "text": "Is the origin declaration bilingual (English and French)?",
        "citation": "https://inspection.canada.ca/en/food-labels/labelling/industry/origin"
    },
    5: {
        "id": "origin_legibility",
        "text": "Is the origin declaration legible and prominently displayed?",
        "citation": "https://inspection.canada.ca/en/food-labels/labelling/industry/origin"
    }
}

# Products that require country of origin declaration
ORIGIN_REQUIRED_PRODUCTS = [
    # Wine and brandy
    'wine', 'brandy', 'vin', 'eau-de-vie',
    # Dairy products
    'milk', 'cheese', 'butter', 'cream', 'yogurt', 'yogourt',
    'lait', 'fromage', 'beurre', 'crème',
    # Honey
    'honey', 'miel',
    # Fish and fish products
    'fish', 'salmon', 'tuna', 'cod', 'shrimp', 'lobster', 'crab',
    'poisson', 'saumon', 'thon', 'morue', 'crevette', 'homard', 'crabe',
    'seafood', 'fruits de mer',
    # Fresh fruits and vegetables
    'apple', 'banana', 'orange', 'grape', 'strawberry', 'tomato', 'potato',
    'pomme', 'banane', 'raisin', 'fraise', 'tomate', 'patate',
    'fresh produce', 'fruit', 'vegetable', 'légume',
    # Shell eggs and processed egg products
    'egg', 'oeuf', 'shell egg',
    # Meat and poultry
    'beef', 'pork', 'chicken', 'turkey', 'lamb', 'meat',
    'boeuf', 'porc', 'poulet', 'dinde', 'agneau', 'viande',
    'poultry', 'volaille',
    # Maple products
    'maple', 'érable', 'maple syrup', 'sirop d\'érable',
    # Processed fruits and vegetables
    'canned', 'frozen vegetable', 'frozen fruit'
]

# Country keywords
COUNTRIES = [
    'canada', 'usa', 'united states', 'mexico', 'china', 'india',
    'italy', 'france', 'spain', 'germany', 'brazil', 'argentina',
    'australia', 'new zealand', 'thailand', 'vietnam', 'chile',
    'peru', 'ecuador', 'colombia', 'japan', 'korea', 'philippines'
]


def extract_origin_info(label_data: Dict) -> Dict[str, Any]:
    """Extract country of origin information from label data"""
    
    # Get all relevant text
    origin = str(label_data.get('country_of_origin', '') or '')
    product_type = str(label_data.get('product_type', '') or '')
    common_name = str(label_data.get('common_name', '') or '')
    all_text = (origin + ' ' + product_type + ' ' + common_name).lower()
    
    # Check if product requires origin
    requires_origin = any(prod in all_text for prod in ORIGIN_REQUIRED_PRODUCTS)
    
    # Check for origin declaration
    has_origin = bool(origin.strip())
    
    # Check for "Product of" format
    has_product_of = any(fmt in all_text for fmt in [
        'product of', 'produit de', 'produit du', 'made in', 'fabriqué',
        'imported from', 'importé de'
    ])
    
    # Check for country name
    country_found = None
    for country in COUNTRIES:
        if country in all_text:
            country_found = country.title()
            break
    
    # Check for bilingual
    has_english = 'product of' in all_text or 'made in' in all_text
    has_french = 'produit de' in all_text or 'produit du' in all_text or 'fabriqué' in all_text
    
    return {
        'requires_origin': requires_origin,
        'has_origin': has_origin,
        'has_product_of': has_product_of,
        'country_found': country_found,
        'has_english': has_english,
        'has_french': has_french,
        'origin_text': origin,
        'product_type': product_type
    }


def evaluate_origin_rule_1(label_data: Dict, info: Dict) -> Dict[str, Any]:
    """Rule 1: Does product require country of origin?"""
    
    requires = info['requires_origin']
    product = info['product_type']
    
    return {
        "rule_id": "origin_required",
        "rule_number": 1,
        "rule_text": COUNTRY_ORIGIN_RULES[1]["text"],
        "compliant": True,  # This is informational, not compliance
        "confidence": 0.7,
        "finding": f"Product type '{product}' {'requires' if requires else 'may not require'} origin declaration",
        "reasoning": "Checked product against categories requiring origin (wine, dairy, honey, fish, produce, eggs, meat, maple)",
        "recommendations": ["Verify product category for origin requirements"] if requires else [],
        "regulatory_references": [COUNTRY_ORIGIN_RULES[1]["citation"]]
    }


def evaluate_origin_rule_2(label_data: Dict, info: Dict) -> Dict[str, Any]:
    """Rule 2: Is origin declaration present if required?"""
    
    requires = info['requires_origin']
    has_origin = info['has_origin'] or info['has_product_of'] or info['country_found']
    
    if not requires:
        return {
            "rule_id": "origin_present",
            "rule_number": 2,
            "rule_text": COUNTRY_ORIGIN_RULES[2]["text"],
            "compliant": True,
            "confidence": 0.7,
            "finding": "Origin declaration may not be required for this product type",
            "reasoning": "Product does not appear to fall into mandatory origin categories",
            "recommendations": [],
            "regulatory_references": [COUNTRY_ORIGIN_RULES[2]["citation"]]
        }
    
    return {
        "rule_id": "origin_present",
        "rule_number": 2,
        "rule_text": COUNTRY_ORIGIN_RULES[2]["text"],
        "compliant": has_origin,
        "confidence": 0.8 if has_origin else 0.6,
        "finding": f"Origin declaration {'found' if has_origin else 'not detected'}" + 
                  (f": {info['country_found']}" if info['country_found'] else ""),
        "reasoning": "Product appears to require origin declaration based on category",
        "recommendations": [] if has_origin else ["Add country of origin declaration"],
        "regulatory_references": [COUNTRY_ORIGIN_RULES[2]["citation"]]
    }


def evaluate_origin_rule_3(label_data: Dict, info: Dict) -> Dict[str, Any]:
    """Rule 3: Is correct format used?"""
    
    has_origin = info['has_origin'] or info['has_product_of'] or info['country_found']
    
    if not has_origin:
        return {
            "rule_id": "origin_format",
            "rule_number": 3,
            "rule_text": COUNTRY_ORIGIN_RULES[3]["text"],
            "compliant": None,
            "confidence": 0.0,
            "finding": "Not applicable - no origin declaration detected",
            "reasoning": "No origin to evaluate format",
            "recommendations": [],
            "regulatory_references": [COUNTRY_ORIGIN_RULES[3]["citation"]]
        }
    
    has_correct_format = info['has_product_of']
    
    return {
        "rule_id": "origin_format",
        "rule_number": 3,
        "rule_text": COUNTRY_ORIGIN_RULES[3]["text"],
        "compliant": has_correct_format,
        "confidence": 0.75 if has_correct_format else 0.5,
        "finding": "'Product of' format detected" if has_correct_format else "Verify 'Product of [Country]' format",
        "reasoning": "Checked for prescribed 'Product of' / 'Produit de' wording",
        "recommendations": [] if has_correct_format else ["Use 'Product of [Country]' / 'Produit du/de [Pays]' format"],
        "regulatory_references": [COUNTRY_ORIGIN_RULES[3]["citation"]]
    }


def evaluate_origin_rule_4(label_data: Dict, info: Dict) -> Dict[str, Any]:
    """Rule 4: Is origin bilingual?"""
    
    has_origin = info['has_origin'] or info['has_product_of'] or info['country_found']
    
    if not has_origin:
        return {
            "rule_id": "origin_bilingual",
            "rule_number": 4,
            "rule_text": COUNTRY_ORIGIN_RULES[4]["text"],
            "compliant": None,
            "confidence": 0.0,
            "finding": "Not applicable - no origin declaration detected",
            "reasoning": "No origin to evaluate",
            "recommendations": [],
            "regulatory_references": [COUNTRY_ORIGIN_RULES[4]["citation"]]
        }
    
    is_bilingual = info['has_english'] and info['has_french']
    
    return {
        "rule_id": "origin_bilingual",
        "rule_number": 4,
        "rule_text": COUNTRY_ORIGIN_RULES[4]["text"],
        "compliant": is_bilingual,
        "confidence": 0.7 if is_bilingual else 0.5,
        "finding": "Bilingual origin declaration detected" if is_bilingual else "Verify bilingual origin declaration",
        "reasoning": f"English: {'Yes' if info['has_english'] else 'Not detected'}, French: {'Yes' if info['has_french'] else 'Not detected'}",
        "recommendations": [] if is_bilingual else ["Include both 'Product of' and 'Produit de/du'"],
        "regulatory_references": [COUNTRY_ORIGIN_RULES[4]["citation"]]
    }


def evaluate_origin_rule_5(label_data: Dict, info: Dict) -> Dict[str, Any]:
    """Rule 5: Is origin legible and prominent?"""
    
    has_origin = info['has_origin'] or info['has_product_of'] or info['country_found']
    
    if not has_origin:
        return {
            "rule_id": "origin_legibility",
            "rule_number": 5,
            "rule_text": COUNTRY_ORIGIN_RULES[5]["text"],
            "compliant": None,
            "confidence": 0.0,
            "finding": "Not applicable - no origin declaration detected",
            "reasoning": "No origin to evaluate",
            "recommendations": [],
            "regulatory_references": [COUNTRY_ORIGIN_RULES[5]["citation"]]
        }
    
    # If OCR detected it, it's likely legible
    return {
        "rule_id": "origin_legibility",
        "rule_number": 5,
        "rule_text": COUNTRY_ORIGIN_RULES[5]["text"],
        "compliant": True,
        "confidence": 0.7,
        "finding": "Origin declaration was readable by OCR - appears legible",
        "reasoning": "OCR successfully extracted origin information",
        "recommendations": [],
        "regulatory_references": [COUNTRY_ORIGIN_RULES[5]["citation"]]
    }


def evaluate_all_origin_rules(label_data: Dict, client=None) -> Dict[str, Any]:
    """Evaluate all country of origin rules."""
    
    info = extract_origin_info(label_data)
    results = {}
    
    results['origin_rule_1'] = evaluate_origin_rule_1(label_data, info)
    results['origin_rule_2'] = evaluate_origin_rule_2(label_data, info)
    results['origin_rule_3'] = evaluate_origin_rule_3(label_data, info)
    results['origin_rule_4'] = evaluate_origin_rule_4(label_data, info)
    results['origin_rule_5'] = evaluate_origin_rule_5(label_data, info)
    
    evaluated = [r for r in results.values() if r.get('compliant') is not None]
    compliant_count = sum(1 for r in evaluated if r.get('compliant'))
    
    results['origin_overall'] = {
        "compliant": all(r.get('compliant', True) for r in evaluated),
        "rules_passed": compliant_count,
        "rules_evaluated": len(evaluated),
        "total_rules": 5,
        "summary": f"Country of origin: {compliant_count}/{len(evaluated)} rules passed"
    }
    
    return results
