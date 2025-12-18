"""
Front-of-Package (FOP) Nutrition Symbol Rule Evaluation Methods
Based on CFIA Food Labelling Requirements Checklist - FOP nutrition symbol section

8 consolidated rules covering:
- Symbol presence and exemptions
- Nutrient threshold requirements
- Symbol specifications and legibility
- Location requirements (PDP)
- Multi-pack/assortment requirements
"""

import re
from typing import Dict, Any, List


# FOP Symbol rules
FOP_RULES = {
    1: {
        "id": "fop_present",
        "text": "Is a FOP nutrition symbol present on the label?",
        "citation": "https://www.canada.ca/en/health-canada/services/food-nutrition/legislation-guidelines/guidance-documents/front-package-nutrition-symbol-labelling-industry.html"
    },
    2: {
        "id": "fop_exempt",
        "text": "Is the product prohibited or exempt from displaying a nutrition symbol?",
        "citation": "https://www.canada.ca/en/health-canada/services/food-nutrition/legislation-guidelines/guidance-documents/front-package-nutrition-symbol-labelling-industry.html#a5"
    },
    3: {
        "id": "fop_thresholds",
        "text": "Are saturated fat, sugars and/or sodium below threshold levels?",
        "citation": "https://www.canada.ca/en/health-canada/services/food-nutrition/legislation-guidelines/guidance-documents/front-package-nutrition-symbol-labelling-industry.html#a4"
    },
    4: {
        "id": "fop_legibility",
        "text": "Does the symbol meet legibility, language and orientation requirements?",
        "citation": "https://www.canada.ca/en/health-canada/services/food-nutrition/legislation-guidelines/guidance-documents/front-package-nutrition-symbol-labelling-industry.html#a6.2"
    },
    5: {
        "id": "fop_specifications",
        "text": "Does the symbol meet required technical specifications?",
        "citation": "https://www.canada.ca/en/health-canada/services/technical-documents-labelling-requirements/nutrition-symbol-specifications/nutrition-labelling.html"
    },
    6: {
        "id": "fop_proportional",
        "text": "Is the symbol proportional to the principal display surface (PDS)?",
        "citation": "https://www.canada.ca/en/health-canada/services/food-nutrition/legislation-guidelines/guidance-documents/front-package-nutrition-symbol-labelling-industry.html"
    },
    7: {
        "id": "fop_location",
        "text": "Is the symbol located on the principal display panel (PDP)?",
        "citation": "https://www.canada.ca/en/health-canada/services/food-nutrition/legislation-guidelines/guidance-documents/front-package-nutrition-symbol-labelling-industry.html"
    },
    8: {
        "id": "fop_multipack",
        "text": "For multi-packs/assortments, is the symbol correctly applied?",
        "citation": "https://www.canada.ca/en/health-canada/services/food-nutrition/legislation-guidelines/guidance-documents/front-package-nutrition-symbol-labelling-industry.html#a7"
    }
}

# Products exempt from FOP symbol
EXEMPT_PRODUCTS = [
    'raw meat', 'raw poultry', 'raw fish', 'seafood', 'ground meat',
    'fresh fruit', 'fresh vegetable', 'milk', 'cream', 'eggs',
    'maple syrup', 'honey', 'single ingredient',
    'small package', 'infant formula', 'meal replacement'
]

# Products prohibited from FOP symbol
PROHIBITED_PRODUCTS = [
    'alcoholic beverage', 'wine', 'beer', 'spirits',
    'food for special dietary use', 'infant formula'
]


def extract_fop_info(label_data: Dict) -> Dict[str, Any]:
    """Extract FOP nutrition symbol information from label data"""
    
    # Get relevant fields
    fop_symbol = str(label_data.get('fop_symbol', '') or '')
    nutrition_symbol = str(label_data.get('nutrition_symbol', '') or '')
    product_type = str(label_data.get('product_type', '') or '').lower()
    
    all_text = (fop_symbol + ' ' + nutrition_symbol).lower()
    
    # Check for FOP symbol
    has_fop = bool(fop_symbol.strip() or nutrition_symbol.strip())
    
    # Check for "high in" indicators
    has_high_in = any(indicator in all_text for indicator in [
        'high in', 'élevé en', 'saturated fat', 'sodium', 'sugars',
        'gras saturés', 'sucres'
    ])
    
    # Check if exempt product
    is_exempt = any(exempt in product_type for exempt in EXEMPT_PRODUCTS)
    
    # Check if prohibited product
    is_prohibited = any(prohibited in product_type for prohibited in PROHIBITED_PRODUCTS)
    
    # Check for multi-pack indicators
    is_multipack = any(mp in product_type for mp in ['pack', 'assortment', 'variety', 'multi'])
    
    return {
        'has_fop': has_fop,
        'has_high_in': has_high_in,
        'is_exempt': is_exempt,
        'is_prohibited': is_prohibited,
        'is_multipack': is_multipack,
        'fop_text': fop_symbol or nutrition_symbol,
        'product_type': product_type
    }


def evaluate_fop_rule_1(label_data: Dict, info: Dict) -> Dict[str, Any]:
    """Rule 1: Is FOP symbol present?"""
    
    has_fop = info['has_fop']
    
    if has_fop:
        return {
            "rule_id": "fop_present",
            "rule_number": 1,
            "rule_text": FOP_RULES[1]["text"],
            "compliant": True,
            "confidence": 0.85,
            "finding": "FOP nutrition symbol detected on label",
            "reasoning": "Found front-of-package nutrition symbol declaration",
            "recommendations": [],
            "regulatory_references": [FOP_RULES[1]["citation"]]
        }
    
    return {
        "rule_id": "fop_present",
        "rule_number": 1,
        "rule_text": FOP_RULES[1]["text"],
        "compliant": None,
        "confidence": 0.5,
        "finding": "FOP symbol not detected - verify if required based on nutrient thresholds",
        "reasoning": "May be exempt or meet threshold requirements",
        "recommendations": ["Verify if FOP symbol is required based on nutrient thresholds"],
        "regulatory_references": [FOP_RULES[1]["citation"]]
    }


def evaluate_fop_rule_2(label_data: Dict, info: Dict) -> Dict[str, Any]:
    """Rule 2: Is product exempt/prohibited?"""
    
    is_exempt = info['is_exempt']
    is_prohibited = info['is_prohibited']
    product = info['product_type']
    
    if is_prohibited:
        return {
            "rule_id": "fop_exempt",
            "rule_number": 2,
            "rule_text": FOP_RULES[2]["text"],
            "compliant": True,
            "confidence": 0.7,
            "finding": f"Product type '{product}' appears prohibited from FOP symbol",
            "reasoning": "Certain products (alcohol, infant formula) cannot display FOP symbol",
            "recommendations": [],
            "regulatory_references": [FOP_RULES[2]["citation"]]
        }
    
    if is_exempt:
        return {
            "rule_id": "fop_exempt",
            "rule_number": 2,
            "rule_text": FOP_RULES[2]["text"],
            "compliant": True,
            "confidence": 0.7,
            "finding": f"Product type '{product}' may be exempt from FOP symbol",
            "reasoning": "Single-ingredient foods and certain categories are exempt",
            "recommendations": [],
            "regulatory_references": [FOP_RULES[2]["citation"]]
        }
    
    return {
        "rule_id": "fop_exempt",
        "rule_number": 2,
        "rule_text": FOP_RULES[2]["text"],
        "compliant": None,
        "confidence": 0.5,
        "finding": "Product does not appear to be exempt - verify FOP symbol requirements",
        "reasoning": "Product may require FOP symbol if above nutrient thresholds",
        "recommendations": ["Verify product exemption status for FOP symbol"],
        "regulatory_references": [FOP_RULES[2]["citation"]]
    }


def evaluate_fop_rule_3(label_data: Dict, info: Dict) -> Dict[str, Any]:
    """Rule 3: Nutrient thresholds"""
    
    has_fop = info['has_fop']
    has_high_in = info['has_high_in']
    
    if not has_fop and not has_high_in:
        return {
            "rule_id": "fop_thresholds",
            "rule_number": 3,
            "rule_text": FOP_RULES[3]["text"],
            "compliant": None,
            "confidence": 0.4,
            "finding": "Cannot verify nutrient thresholds from label text",
            "reasoning": "Thresholds: Sat fat ≥15% DV, Sugars ≥15% DV, Sodium ≥15% DV",
            "recommendations": ["Verify saturated fat, sugars, and sodium against 15% DV thresholds"],
            "regulatory_references": [FOP_RULES[3]["citation"]]
        }
    
    if has_high_in:
        return {
            "rule_id": "fop_thresholds",
            "rule_number": 3,
            "rule_text": FOP_RULES[3]["text"],
            "compliant": True,
            "confidence": 0.7,
            "finding": "'High in' nutrient indicator detected - FOP symbol correctly present",
            "reasoning": "Product exceeds threshold for one or more nutrients",
            "recommendations": [],
            "regulatory_references": [FOP_RULES[3]["citation"]]
        }
    
    return {
        "rule_id": "fop_thresholds",
        "rule_number": 3,
        "rule_text": FOP_RULES[3]["text"],
        "compliant": None,
        "confidence": 0.5,
        "finding": "Verify nutrient levels against thresholds",
        "reasoning": "FOP symbol required if sat fat, sugars, or sodium ≥15% DV",
        "recommendations": [],
        "regulatory_references": [FOP_RULES[3]["citation"]]
    }


def evaluate_fop_rule_4(label_data: Dict, info: Dict) -> Dict[str, Any]:
    """Rule 4: Legibility requirements"""
    
    has_fop = info['has_fop']
    
    if not has_fop:
        return {
            "rule_id": "fop_legibility",
            "rule_number": 4,
            "rule_text": FOP_RULES[4]["text"],
            "compliant": None,
            "confidence": 0.0,
            "finding": "Not applicable - no FOP symbol detected",
            "reasoning": "No symbol to evaluate",
            "recommendations": [],
            "regulatory_references": [FOP_RULES[4]["citation"]]
        }
    
    return {
        "rule_id": "fop_legibility",
        "rule_number": 4,
        "rule_text": FOP_RULES[4]["text"],
        "compliant": True,
        "confidence": 0.7,
        "finding": "FOP symbol was readable by OCR - appears legible",
        "reasoning": "OCR successfully extracted symbol text",
        "recommendations": [],
        "regulatory_references": [FOP_RULES[4]["citation"]]
    }


def evaluate_fop_rule_5(label_data: Dict, info: Dict) -> Dict[str, Any]:
    """Rule 5: Technical specifications"""
    
    has_fop = info['has_fop']
    
    if not has_fop:
        return {
            "rule_id": "fop_specifications",
            "rule_number": 5,
            "rule_text": FOP_RULES[5]["text"],
            "compliant": None,
            "confidence": 0.0,
            "finding": "Not applicable - no FOP symbol detected",
            "reasoning": "No symbol to evaluate",
            "recommendations": [],
            "regulatory_references": [FOP_RULES[5]["citation"]]
        }
    
    return {
        "rule_id": "fop_specifications",
        "rule_number": 5,
        "rule_text": FOP_RULES[5]["text"],
        "compliant": None,
        "confidence": 0.4,
        "finding": "Technical specifications require visual verification",
        "reasoning": "Cannot verify exact dimensions and colors from OCR",
        "recommendations": ["Verify symbol meets Health Canada specifications"],
        "regulatory_references": [FOP_RULES[5]["citation"]]
    }


def evaluate_fop_rule_6(label_data: Dict, info: Dict) -> Dict[str, Any]:
    """Rule 6: Symbol proportional to PDS"""
    
    has_fop = info['has_fop']
    
    if not has_fop:
        return {
            "rule_id": "fop_proportional",
            "rule_number": 6,
            "rule_text": FOP_RULES[6]["text"],
            "compliant": None,
            "confidence": 0.0,
            "finding": "Not applicable - no FOP symbol detected",
            "reasoning": "No symbol to evaluate",
            "recommendations": [],
            "regulatory_references": [FOP_RULES[6]["citation"]]
        }
    
    return {
        "rule_id": "fop_proportional",
        "rule_number": 6,
        "rule_text": FOP_RULES[6]["text"],
        "compliant": None,
        "confidence": 0.4,
        "finding": "Symbol proportionality requires visual verification",
        "reasoning": "Cannot verify PDS ratio from OCR",
        "recommendations": ["Verify symbol size is proportional to principal display surface"],
        "regulatory_references": [FOP_RULES[6]["citation"]]
    }


def evaluate_fop_rule_7(label_data: Dict, info: Dict) -> Dict[str, Any]:
    """Rule 7: Location on PDP"""
    
    has_fop = info['has_fop']
    
    if not has_fop:
        return {
            "rule_id": "fop_location",
            "rule_number": 7,
            "rule_text": FOP_RULES[7]["text"],
            "compliant": None,
            "confidence": 0.0,
            "finding": "Not applicable - no FOP symbol detected",
            "reasoning": "No symbol to evaluate location",
            "recommendations": [],
            "regulatory_references": [FOP_RULES[7]["citation"]]
        }
    
    return {
        "rule_id": "fop_location",
        "rule_number": 7,
        "rule_text": FOP_RULES[7]["text"],
        "compliant": None,
        "confidence": 0.4,
        "finding": "Symbol location requires visual verification",
        "reasoning": "Cannot verify PDP placement from OCR",
        "recommendations": ["Verify symbol is on principal display panel"],
        "regulatory_references": [FOP_RULES[7]["citation"]]
    }


def evaluate_fop_rule_8(label_data: Dict, info: Dict) -> Dict[str, Any]:
    """Rule 8: Multi-pack requirements"""
    
    is_multipack = info['is_multipack']
    has_fop = info['has_fop']
    
    if not is_multipack:
        return {
            "rule_id": "fop_multipack",
            "rule_number": 8,
            "rule_text": FOP_RULES[8]["text"],
            "compliant": True,
            "confidence": 0.7,
            "finding": "Not a multi-pack/assortment - rule not applicable",
            "reasoning": "Product does not appear to be multi-pack or assortment",
            "recommendations": [],
            "regulatory_references": [FOP_RULES[8]["citation"]]
        }
    
    return {
        "rule_id": "fop_multipack",
        "rule_number": 8,
        "rule_text": FOP_RULES[8]["text"],
        "compliant": None,
        "confidence": 0.5,
        "finding": f"Multi-pack detected - verify FOP symbol application per section 7",
        "reasoning": "Multi-packs have special FOP symbol requirements",
        "recommendations": ["Verify FOP symbol on each unit if nutrients exceed thresholds"],
        "regulatory_references": [FOP_RULES[8]["citation"]]
    }


def evaluate_all_fop_rules(label_data: Dict, client=None) -> Dict[str, Any]:
    """Evaluate all FOP nutrition symbol rules."""
    
    info = extract_fop_info(label_data)
    results = {}
    
    results['fop_rule_1'] = evaluate_fop_rule_1(label_data, info)
    results['fop_rule_2'] = evaluate_fop_rule_2(label_data, info)
    results['fop_rule_3'] = evaluate_fop_rule_3(label_data, info)
    results['fop_rule_4'] = evaluate_fop_rule_4(label_data, info)
    results['fop_rule_5'] = evaluate_fop_rule_5(label_data, info)
    results['fop_rule_6'] = evaluate_fop_rule_6(label_data, info)
    results['fop_rule_7'] = evaluate_fop_rule_7(label_data, info)
    results['fop_rule_8'] = evaluate_fop_rule_8(label_data, info)
    
    evaluated = [r for r in results.values() if r.get('compliant') is not None]
    compliant_count = sum(1 for r in evaluated if r.get('compliant'))
    
    results['fop_overall'] = {
        "compliant": all(r.get('compliant', True) for r in evaluated),
        "rules_passed": compliant_count,
        "rules_evaluated": len(evaluated),
        "total_rules": 8,
        "summary": f"FOP nutrition symbol: {compliant_count}/{len(evaluated)} rules passed"
    }
    
    return results
