"""
Nutrition Labelling Rule Evaluation Methods
Based on CFIA Food Labelling Requirements Checklist - Nutrition labelling section

15 consolidated rules covering:
- Nutrition Facts table (NFt) presence and exemptions
- NFt location and format requirements
- Serving size and Reference Amount
- Core nutrients and % Daily Value
- Front-of-package (FOP) nutrition symbol
- Graphical and technical requirements
"""

import re
from typing import Dict, Any, List


# Nutrition labelling rules - consolidated from CFIA checklist
NUTRITION_RULES = {
    1: {
        "id": "nft_present",
        "text": "Is a Nutrition Facts table (NFt) present?",
        "citation": "https://inspection.canada.ca/en/food-labels/labelling/industry/nutrition-labelling"
    },
    2: {
        "id": "nft_exempt_prohibited",
        "text": "If no NFt, is the product prohibited, exempt, or has ADS < 15 cm²?",
        "citation": "https://inspection.canada.ca/en/food-labels/labelling/industry/nutrition-labelling/exemptions"
    },
    3: {
        "id": "nft_location",
        "text": "Is the NFt on outer package, on continuous ADS surface, not destroyed when opened?",
        "citation": "https://inspection.canada.ca/en/food-labels/labelling/industry/nutrition-labelling"
    },
    4: {
        "id": "serving_size",
        "text": "Is serving size aligned with Reference Amount (RA) and in household/metric measures?",
        "citation": "https://inspection.canada.ca/en/food-labels/labelling/industry/nutrition-labelling"
    },
    5: {
        "id": "core_nutrients",
        "text": "Are energy (calories) and 12 core nutrients declared?",
        "citation": "https://inspection.canada.ca/en/food-labels/labelling/industry/nutrition-labelling"
    },
    6: {
        "id": "units_dv",
        "text": "Are correct units and % Daily Value (DV) used and properly rounded?",
        "citation": "https://inspection.canada.ca/en/food-labels/labelling/industry/nutrition-labelling"
    },
    7: {
        "id": "dv_statement",
        "text": "Is the % Daily Value interpretive statement included?",
        "citation": "https://inspection.canada.ca/en/food-labels/labelling/industry/nutrition-labelling"
    },
    8: {
        "id": "format_appropriate",
        "text": "Is appropriate NFt format used (standard, simplified, dual, aggregate)?",
        "citation": "https://inspection.canada.ca/en/food-labels/labelling/industry/nutrition-labelling"
    },
    9: {
        "id": "format_version_size",
        "text": "Is appropriate format version/size chosen within format family?",
        "citation": "https://inspection.canada.ca/en/food-labels/labelling/industry/nutrition-labelling"
    },
    10: {
        "id": "graphical_colours",
        "text": "Is NFt background and print in appropriate colours/contrast?",
        "citation": "https://inspection.canada.ca/en/food-labels/labelling/industry/nutrition-labelling"
    },
    11: {
        "id": "graphical_font",
        "text": "Is font sans serif, regular/bold as required, proper case and spacing?",
        "citation": "https://inspection.canada.ca/en/food-labels/labelling/industry/nutrition-labelling"
    },
    12: {
        "id": "fop_symbol_present",
        "text": "Is a Front-of-Package (FOP) nutrition symbol present if required?",
        "citation": "https://www.canada.ca/en/health-canada/services/food-nutrition/legislation-guidelines/guidance-documents/front-package-nutrition-symbol-labelling-industry.html"
    },
    13: {
        "id": "fop_thresholds",
        "text": "If no FOP symbol, are saturated fat/sugars/sodium below thresholds?",
        "citation": "https://www.canada.ca/en/health-canada/services/food-nutrition/legislation-guidelines/guidance-documents/front-package-nutrition-symbol-labelling-industry.html#a4"
    },
    14: {
        "id": "fop_specifications",
        "text": "Does FOP symbol meet legibility, language, orientation, and size requirements?",
        "citation": "https://www.canada.ca/en/health-canada/services/food-nutrition/legislation-guidelines/guidance-documents/front-package-nutrition-symbol-labelling-industry.html#a6.2"
    },
    15: {
        "id": "fop_location",
        "text": "Is FOP symbol located on Principal Display Panel (PDP)?",
        "citation": "https://www.canada.ca/en/health-canada/services/food-nutrition/legislation-guidelines/guidance-documents/front-package-nutrition-symbol-labelling-industry.html"
    }
}

# Core nutrients required in NFt
CORE_NUTRIENTS = [
    'fat', 'saturated', 'trans', 'cholesterol', 'sodium',
    'carbohydrate', 'fibre', 'fiber', 'sugars', 'protein',
    'vitamin a', 'vitamin c', 'calcium', 'iron', 'potassium'
]


def extract_nutrition_info(label_data: Dict) -> Dict[str, Any]:
    """Extract nutrition labelling information from label data"""
    
    nutrition = str(label_data.get('nutrition_facts', '') or '')
    all_text = nutrition.lower()
    
    # Check for NFt presence
    has_nft = bool(nutrition.strip())
    
    # Check for "Nutrition Facts" header
    has_nft_header = any(h in all_text for h in [
        'nutrition facts', 'valeur nutritive', 'nutrition information'
    ])
    
    # Check for calories
    has_calories = 'calories' in all_text or 'cal' in all_text
    
    # Check for serving size
    has_serving = any(s in all_text for s in ['serving', 'portion', 'per'])
    
    # Check for % Daily Value
    has_dv = '% daily value' in all_text or '% valeur quotidienne' in all_text or '%dv' in all_text
    
    # Count core nutrients found
    nutrients_found = []
    for nutrient in CORE_NUTRIENTS:
        if nutrient in all_text:
            nutrients_found.append(nutrient)
    
    # Check for FOP symbol indicators
    has_fop = any(f in all_text for f in [
        'high in', 'élevé en', 'saturated fat', 'sodium', 'sugars'
    ]) and 'symbol' in all_text
    
    # Check for high nutrient warnings
    high_nutrients = []
    if 'high in saturated fat' in all_text or 'élevé en gras saturés' in all_text:
        high_nutrients.append('saturated fat')
    if 'high in sodium' in all_text or 'élevé en sodium' in all_text:
        high_nutrients.append('sodium')
    if 'high in sugars' in all_text or 'élevé en sucres' in all_text:
        high_nutrients.append('sugars')
    
    return {
        'has_nft': has_nft,
        'has_nft_header': has_nft_header,
        'has_calories': has_calories,
        'has_serving': has_serving,
        'has_dv': has_dv,
        'nutrients_found': nutrients_found,
        'has_fop': has_fop,
        'high_nutrients': high_nutrients,
        'nutrition_text': nutrition
    }


def evaluate_nutrition_rule_1(label_data: Dict, info: Dict) -> Dict[str, Any]:
    """Rule 1: Is an NFt present?"""
    
    compliant = info['has_nft'] and info['has_nft_header']
    
    return {
        "rule_id": "nft_present",
        "rule_number": 1,
        "rule_text": NUTRITION_RULES[1]["text"],
        "compliant": compliant,
        "confidence": 0.85 if compliant else 0.7,
        "finding": "Nutrition Facts table detected" if compliant else "Nutrition Facts table not detected",
        "reasoning": f"NFt header present: {info['has_nft_header']}, nutrition content: {info['has_nft']}",
        "recommendations": [] if compliant else ["Add Nutrition Facts table to label"],
        "regulatory_references": [NUTRITION_RULES[1]["citation"]]
    }


def evaluate_nutrition_rule_2(label_data: Dict, info: Dict, rule_1: Dict) -> Dict[str, Any]:
    """Rule 2: Exemption/prohibition check if no NFt"""
    
    if rule_1.get('compliant'):
        return {
            "rule_id": "nft_exempt_prohibited",
            "rule_number": 2,
            "rule_text": NUTRITION_RULES[2]["text"],
            "compliant": True,
            "confidence": 0.95,
            "finding": "Not applicable - NFt is present",
            "reasoning": "Rule 1 passed",
            "recommendations": [],
            "regulatory_references": [NUTRITION_RULES[2]["citation"]]
        }
    
    # Check for exemption indicators
    product_type = str(label_data.get('product_type', '')).lower()
    exemptions = ['fresh produce', 'raw meat', 'alcoholic beverage', 'coffee', 'tea', 'spice', 'herb']
    
    exempt = any(e in product_type for e in exemptions)
    
    return {
        "rule_id": "nft_exempt_prohibited",
        "rule_number": 2,
        "rule_text": NUTRITION_RULES[2]["text"],
        "compliant": exempt,
        "confidence": 0.6,
        "finding": "Product may be NFt exempt" if exempt else "NFt appears to be required",
        "reasoning": f"Checked product type '{product_type}' against exemption categories",
        "recommendations": [] if exempt else ["Add NFt or verify exemption eligibility"],
        "regulatory_references": [NUTRITION_RULES[2]["citation"]]
    }


def evaluate_nutrition_rule_3(label_data: Dict, info: Dict) -> Dict[str, Any]:
    """Rule 3: NFt location requirements"""
    
    if not info['has_nft']:
        return {
            "rule_id": "nft_location",
            "rule_number": 3,
            "rule_text": NUTRITION_RULES[3]["text"],
            "compliant": None,
            "confidence": 0.0,
            "finding": "Cannot evaluate - no NFt present",
            "reasoning": "NFt not detected",
            "recommendations": [],
            "regulatory_references": [NUTRITION_RULES[3]["citation"]]
        }
    
    return {
        "rule_id": "nft_location",
        "rule_number": 3,
        "rule_text": NUTRITION_RULES[3]["text"],
        "compliant": None,
        "confidence": 0.4,
        "finding": "NFt location requires visual verification",
        "reasoning": "Cannot verify outer package/continuous surface from OCR",
        "recommendations": ["Verify NFt is on outer package on continuous ADS surface"],
        "regulatory_references": [NUTRITION_RULES[3]["citation"]]
    }


def evaluate_nutrition_rule_4(label_data: Dict, info: Dict) -> Dict[str, Any]:
    """Rule 4: Serving size requirements"""
    
    if not info['has_nft']:
        return {
            "rule_id": "serving_size",
            "rule_number": 4,
            "rule_text": NUTRITION_RULES[4]["text"],
            "compliant": None,
            "confidence": 0.0,
            "finding": "Cannot evaluate - no NFt present",
            "reasoning": "NFt not detected",
            "recommendations": [],
            "regulatory_references": [NUTRITION_RULES[4]["citation"]]
        }
    
    has_serving = info['has_serving']
    
    return {
        "rule_id": "serving_size",
        "rule_number": 4,
        "rule_text": NUTRITION_RULES[4]["text"],
        "compliant": has_serving,
        "confidence": 0.75 if has_serving else 0.6,
        "finding": "Serving size declaration detected" if has_serving else "Serving size not detected",
        "reasoning": "Checked for serving/portion size in NFt",
        "recommendations": [] if has_serving else ["Add serving size with household and metric measures"],
        "regulatory_references": [NUTRITION_RULES[4]["citation"]]
    }


def evaluate_nutrition_rule_5(label_data: Dict, info: Dict) -> Dict[str, Any]:
    """Rule 5: Core nutrients declared"""
    
    if not info['has_nft']:
        return {
            "rule_id": "core_nutrients",
            "rule_number": 5,
            "rule_text": NUTRITION_RULES[5]["text"],
            "compliant": None,
            "confidence": 0.0,
            "finding": "Cannot evaluate - no NFt present",
            "reasoning": "NFt not detected",
            "recommendations": [],
            "regulatory_references": [NUTRITION_RULES[5]["citation"]]
        }
    
    has_calories = info['has_calories']
    nutrients = info['nutrients_found']
    nutrient_count = len(nutrients)
    
    # Need calories + at least 8 core nutrients for good compliance
    compliant = has_calories and nutrient_count >= 8
    
    return {
        "rule_id": "core_nutrients",
        "rule_number": 5,
        "rule_text": NUTRITION_RULES[5]["text"],
        "compliant": compliant,
        "confidence": 0.8 if compliant else 0.6,
        "finding": f"Calories: {'Yes' if has_calories else 'No'}, {nutrient_count} core nutrients found: {', '.join(nutrients[:5])}",
        "reasoning": "Checked for calories and core nutrients in NFt",
        "recommendations": [] if compliant else ["Ensure all 12 core nutrients are declared"],
        "regulatory_references": [NUTRITION_RULES[5]["citation"]]
    }


def evaluate_nutrition_rule_6(label_data: Dict, info: Dict) -> Dict[str, Any]:
    """Rule 6: Units and % DV"""
    
    if not info['has_nft']:
        return {
            "rule_id": "units_dv",
            "rule_number": 6,
            "rule_text": NUTRITION_RULES[6]["text"],
            "compliant": None,
            "confidence": 0.0,
            "finding": "Cannot evaluate - no NFt present",
            "reasoning": "NFt not detected",
            "recommendations": [],
            "regulatory_references": [NUTRITION_RULES[6]["citation"]]
        }
    
    has_dv = info['has_dv']
    
    return {
        "rule_id": "units_dv",
        "rule_number": 6,
        "rule_text": NUTRITION_RULES[6]["text"],
        "compliant": has_dv,
        "confidence": 0.75 if has_dv else 0.5,
        "finding": "% Daily Value declarations detected" if has_dv else "% Daily Value not detected",
        "reasoning": "Checked for %DV declarations",
        "recommendations": [] if has_dv else ["Include % Daily Value for applicable nutrients"],
        "regulatory_references": [NUTRITION_RULES[6]["citation"]]
    }


def evaluate_nutrition_rule_7(label_data: Dict, info: Dict) -> Dict[str, Any]:
    """Rule 7: % DV interpretive statement"""
    
    if not info['has_nft']:
        return {
            "rule_id": "dv_statement",
            "rule_number": 7,
            "rule_text": NUTRITION_RULES[7]["text"],
            "compliant": None,
            "confidence": 0.0,
            "finding": "Cannot evaluate - no NFt present",
            "reasoning": "NFt not detected",
            "recommendations": [],
            "regulatory_references": [NUTRITION_RULES[7]["citation"]]
        }
    
    text = info['nutrition_text'].lower()
    has_statement = any(s in text for s in [
        '5% or less is a little', '15% or more is a lot',
        '5 % ou moins c\'est peu', '15 % ou plus c\'est beaucoup'
    ])
    
    return {
        "rule_id": "dv_statement",
        "rule_number": 7,
        "rule_text": NUTRITION_RULES[7]["text"],
        "compliant": has_statement if info['has_dv'] else None,
        "confidence": 0.7 if has_statement else 0.4,
        "finding": "% DV interpretive statement found" if has_statement else "% DV statement requires verification",
        "reasoning": "Checked for DV interpretive statement",
        "recommendations": [] if has_statement else ["Include '5% or less is a little, 15% or more is a lot' statement"],
        "regulatory_references": [NUTRITION_RULES[7]["citation"]]
    }


def evaluate_nutrition_rule_8(label_data: Dict, info: Dict) -> Dict[str, Any]:
    """Rule 8: Appropriate NFt format"""
    
    if not info['has_nft']:
        return {
            "rule_id": "format_appropriate",
            "rule_number": 8,
            "rule_text": NUTRITION_RULES[8]["text"],
            "compliant": None,
            "confidence": 0.0,
            "finding": "Cannot evaluate - no NFt present",
            "reasoning": "NFt not detected",
            "recommendations": [],
            "regulatory_references": [NUTRITION_RULES[8]["citation"]]
        }
    
    return {
        "rule_id": "format_appropriate",
        "rule_number": 8,
        "rule_text": NUTRITION_RULES[8]["text"],
        "compliant": None,
        "confidence": 0.4,
        "finding": "NFt format verification requires manual review",
        "reasoning": "Cannot determine standard/simplified/dual/aggregate format from OCR",
        "recommendations": ["Verify appropriate NFt format is used for product type"],
        "regulatory_references": [NUTRITION_RULES[8]["citation"]]
    }


def evaluate_nutrition_rule_9(label_data: Dict, info: Dict) -> Dict[str, Any]:
    """Rule 9: Format version/size"""
    
    return {
        "rule_id": "format_version_size",
        "rule_number": 9,
        "rule_text": NUTRITION_RULES[9]["text"],
        "compliant": None,
        "confidence": 0.3,
        "finding": "Format size verification requires visual inspection",
        "reasoning": "Cannot verify NFt size from OCR",
        "recommendations": ["Verify NFt size is proportional to available display surface"],
        "regulatory_references": [NUTRITION_RULES[9]["citation"]]
    }


def evaluate_nutrition_rule_10(label_data: Dict, info: Dict) -> Dict[str, Any]:
    """Rule 10: Graphical colours/contrast"""
    
    return {
        "rule_id": "graphical_colours",
        "rule_number": 10,
        "rule_text": NUTRITION_RULES[10]["text"],
        "compliant": None,
        "confidence": 0.3,
        "finding": "Colour and contrast require visual verification",
        "reasoning": "Cannot verify colours from OCR text",
        "recommendations": ["Verify NFt uses black text on white/light background"],
        "regulatory_references": [NUTRITION_RULES[10]["citation"]]
    }


def evaluate_nutrition_rule_11(label_data: Dict, info: Dict) -> Dict[str, Any]:
    """Rule 11: Font requirements"""
    
    return {
        "rule_id": "graphical_font",
        "rule_number": 11,
        "rule_text": NUTRITION_RULES[11]["text"],
        "compliant": None,
        "confidence": 0.3,
        "finding": "Font requirements require visual verification",
        "reasoning": "Cannot verify font type from OCR",
        "recommendations": ["Verify sans serif font, proper case, bold where required"],
        "regulatory_references": [NUTRITION_RULES[11]["citation"]]
    }


def evaluate_nutrition_rule_12(label_data: Dict, info: Dict) -> Dict[str, Any]:
    """Rule 12: FOP symbol present if required"""
    
    high_nutrients = info['high_nutrients']
    
    if not high_nutrients:
        return {
            "rule_id": "fop_symbol_present",
            "rule_number": 12,
            "rule_text": NUTRITION_RULES[12]["text"],
            "compliant": True,
            "confidence": 0.7,
            "finding": "No high nutrient warnings detected - FOP symbol may not be required",
            "reasoning": "Product does not appear to exceed nutrient thresholds",
            "recommendations": [],
            "regulatory_references": [NUTRITION_RULES[12]["citation"]]
        }
    
    has_fop = info['has_fop']
    
    return {
        "rule_id": "fop_symbol_present",
        "rule_number": 12,
        "rule_text": NUTRITION_RULES[12]["text"],
        "compliant": has_fop,
        "confidence": 0.6,
        "finding": f"High in: {', '.join(high_nutrients)}. FOP symbol: {'detected' if has_fop else 'not detected'}",
        "reasoning": "Product may require FOP symbol based on nutrient content",
        "recommendations": [] if has_fop else ["Verify FOP nutrition symbol requirement"],
        "regulatory_references": [NUTRITION_RULES[12]["citation"]]
    }


def evaluate_nutrition_rule_13(label_data: Dict, info: Dict) -> Dict[str, Any]:
    """Rule 13: FOP thresholds check"""
    
    if info['has_fop']:
        return {
            "rule_id": "fop_thresholds",
            "rule_number": 13,
            "rule_text": NUTRITION_RULES[13]["text"],
            "compliant": True,
            "confidence": 0.9,
            "finding": "FOP symbol present - threshold check not applicable",
            "reasoning": "Product displays FOP symbol",
            "recommendations": [],
            "regulatory_references": [NUTRITION_RULES[13]["citation"]]
        }
    
    return {
        "rule_id": "fop_thresholds",
        "rule_number": 13,
        "rule_text": NUTRITION_RULES[13]["text"],
        "compliant": None,
        "confidence": 0.4,
        "finding": "Nutrient thresholds require verification against NFt values",
        "reasoning": "Cannot calculate exact threshold comparison from OCR",
        "recommendations": ["Verify saturated fat, sugars, sodium are below FOP thresholds if no symbol"],
        "regulatory_references": [NUTRITION_RULES[13]["citation"]]
    }


def evaluate_nutrition_rule_14(label_data: Dict, info: Dict) -> Dict[str, Any]:
    """Rule 14: FOP specifications"""
    
    if not info['has_fop']:
        return {
            "rule_id": "fop_specifications",
            "rule_number": 14,
            "rule_text": NUTRITION_RULES[14]["text"],
            "compliant": True,
            "confidence": 0.9,
            "finding": "No FOP symbol - specifications not applicable",
            "reasoning": "FOP symbol not detected",
            "recommendations": [],
            "regulatory_references": [NUTRITION_RULES[14]["citation"]]
        }
    
    return {
        "rule_id": "fop_specifications",
        "rule_number": 14,
        "rule_text": NUTRITION_RULES[14]["text"],
        "compliant": None,
        "confidence": 0.4,
        "finding": "FOP symbol specifications require visual verification",
        "reasoning": "Cannot verify size, orientation, legibility from OCR",
        "recommendations": ["Verify FOP symbol meets technical specifications"],
        "regulatory_references": [NUTRITION_RULES[14]["citation"]]
    }


def evaluate_nutrition_rule_15(label_data: Dict, info: Dict) -> Dict[str, Any]:
    """Rule 15: FOP location on PDP"""
    
    if not info['has_fop']:
        return {
            "rule_id": "fop_location",
            "rule_number": 15,
            "rule_text": NUTRITION_RULES[15]["text"],
            "compliant": True,
            "confidence": 0.9,
            "finding": "No FOP symbol - location not applicable",
            "reasoning": "FOP symbol not detected",
            "recommendations": [],
            "regulatory_references": [NUTRITION_RULES[15]["citation"]]
        }
    
    return {
        "rule_id": "fop_location",
        "rule_number": 15,
        "rule_text": NUTRITION_RULES[15]["text"],
        "compliant": None,
        "confidence": 0.4,
        "finding": "FOP symbol location requires visual verification",
        "reasoning": "Cannot verify PDP placement from OCR",
        "recommendations": ["Verify FOP symbol is on Principal Display Panel"],
        "regulatory_references": [NUTRITION_RULES[15]["citation"]]
    }


def evaluate_all_nutrition_rules(label_data: Dict, client=None) -> Dict[str, Any]:
    """Evaluate all nutrition labelling rules."""
    
    info = extract_nutrition_info(label_data)
    results = {}
    
    rule_1 = evaluate_nutrition_rule_1(label_data, info)
    results['nutrition_rule_1'] = rule_1
    
    results['nutrition_rule_2'] = evaluate_nutrition_rule_2(label_data, info, rule_1)
    results['nutrition_rule_3'] = evaluate_nutrition_rule_3(label_data, info)
    results['nutrition_rule_4'] = evaluate_nutrition_rule_4(label_data, info)
    results['nutrition_rule_5'] = evaluate_nutrition_rule_5(label_data, info)
    results['nutrition_rule_6'] = evaluate_nutrition_rule_6(label_data, info)
    results['nutrition_rule_7'] = evaluate_nutrition_rule_7(label_data, info)
    results['nutrition_rule_8'] = evaluate_nutrition_rule_8(label_data, info)
    results['nutrition_rule_9'] = evaluate_nutrition_rule_9(label_data, info)
    results['nutrition_rule_10'] = evaluate_nutrition_rule_10(label_data, info)
    results['nutrition_rule_11'] = evaluate_nutrition_rule_11(label_data, info)
    results['nutrition_rule_12'] = evaluate_nutrition_rule_12(label_data, info)
    results['nutrition_rule_13'] = evaluate_nutrition_rule_13(label_data, info)
    results['nutrition_rule_14'] = evaluate_nutrition_rule_14(label_data, info)
    results['nutrition_rule_15'] = evaluate_nutrition_rule_15(label_data, info)
    
    evaluated = [r for r in results.values() if r.get('compliant') is not None]
    compliant_count = sum(1 for r in evaluated if r.get('compliant'))
    
    results['nutrition_overall'] = {
        "compliant": all(r.get('compliant', True) for r in evaluated),
        "rules_passed": compliant_count,
        "rules_evaluated": len(evaluated),
        "total_rules": 15,
        "summary": f"Nutrition labelling: {compliant_count}/{len(evaluated)} rules passed"
    }
    
    return results
