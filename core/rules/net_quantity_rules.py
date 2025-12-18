"""
Net Quantity Declaration Rule Evaluation Methods
Based on CFIA Food Labelling Requirements Checklist - Net quantity declaration section

12 Rules covering:
- Presence and exemption
- Principal Display Panel (PDP) location  
- Metric units and symbols
- Type height requirements
- Optional Canadian/US units
"""

import re
from typing import Dict, Any, List


# Net quantity rules from CFIA checklist
NET_QUANTITY_RULES = {
    1: {
        "id": "net_qty_present",
        "text": "Is a net quantity declaration present?",
        "citation": "https://inspection.canada.ca/en/food-labels/labelling/industry/net-quantity"
    },
    2: {
        "id": "net_qty_exempt", 
        "text": "If not, is the product exempt from net quantity?",
        "citation": "https://inspection.canada.ca/en/food-labels/labelling/industry/net-quantity#s1c1"
    },
    3: {
        "id": "net_qty_on_pdp",
        "text": "Is the net quantity declared on the PDP?",
        "citation": "https://inspection.canada.ca/en/food-labels/labelling/industry/net-quantity"
    },
    4: {
        "id": "net_qty_metric_units",
        "text": "Is it in metric units?",
        "citation": "https://inspection.canada.ca/en/food-labels/labelling/industry/net-quantity#s14c4"
    },
    5: {
        "id": "net_qty_retail_bulk",
        "text": "Or, in metric or Canadian units if it is a consumer prepackaged food packaged from bulk at retail?",
        "citation": "https://inspection.canada.ca/en/food-labels/labelling/industry/net-quantity#s14c4"
    },
    6: {
        "id": "net_qty_manner",
        "text": "Is the appropriate manner (volume, weight, count) for the product used?",
        "citation": "https://inspection.canada.ca/en/food-labels/labelling/industry/net-quantity"
    },
    7: {
        "id": "net_qty_rounding",
        "text": "Is it rounded to 3 figures, unless below 100?",
        "citation": "https://inspection.canada.ca/en/food-labels/labelling/industry/net-quantity"
    },
    8: {
        "id": "net_qty_symbols",
        "text": "Are the correct bilingual symbols used? (ml, mL, L, g, kg)",
        "citation": "https://inspection.canada.ca/en/food-labels/labelling/industry/net-quantity"
    },
    9: {
        "id": "net_qty_written_units",
        "text": "If units are written out, are they declared in both languages?",
        "citation": "https://inspection.canada.ca/en/food-labels/labelling/industry/net-quantity"
    },
    10: {
        "id": "net_qty_type_height",
        "text": "Does the size meet minimum type height requirements? Is it in bold face type?",
        "citation": "https://inspection.canada.ca/en/food-labels/labelling/industry/net-quantity"
    },
    11: {
        "id": "net_qty_canadian_units",
        "text": "If optional Canadian units are present, are they declared properly?",
        "citation": "https://inspection.canada.ca/en/food-labels/labelling/industry/net-quantity"
    },
    12: {
        "id": "net_qty_us_units",
        "text": "If optional U.S. gallons and quarts are present, are they identified properly?",
        "citation": "https://inspection.canada.ca/en/food-labels/labelling/industry/net-quantity"
    }
}

# Valid metric symbols (bilingual)
METRIC_VOLUME_SYMBOLS = ['ml', 'mL', 'l', 'L', 'ℓ', 'mℓ']
METRIC_WEIGHT_SYMBOLS = ['g', 'kg', 'mg']
ALL_METRIC_SYMBOLS = METRIC_VOLUME_SYMBOLS + METRIC_WEIGHT_SYMBOLS

# Patterns for detecting net quantity
NET_QTY_PATTERNS = [
    r'\d+\s*(?:ml|mL|l|L|g|kg|oz|fl\s*oz)',
    r'\d+\.?\d*\s*(?:grams?|kilograms?|litres?|liters?|millilitres?|milliliters?)',
    r'\d+\s*(?:pieces?|count|units?|items?)'
]


def extract_net_quantity_info(label_data: Dict) -> Dict[str, Any]:
    """Extract net quantity information from label data"""
    
    net_qty = label_data.get('net_quantity', '')
    all_text = str(label_data.get('common_name', '')) + ' ' + str(label_data.get('ingredients_list', ''))
    
    # Check for net quantity presence
    has_net_qty = bool(net_qty)
    
    # Detect metric units
    has_metric = False
    metric_units_found = []
    for symbol in ALL_METRIC_SYMBOLS:
        if symbol.lower() in str(net_qty).lower():
            has_metric = True
            metric_units_found.append(symbol)
    
    # Detect volume vs weight vs count
    manner = 'unknown'
    if any(s in str(net_qty).lower() for s in METRIC_VOLUME_SYMBOLS + ['fl oz', 'fluid']):
        manner = 'volume'
    elif any(s in str(net_qty).lower() for s in METRIC_WEIGHT_SYMBOLS + ['oz', 'lb', 'pound']):
        manner = 'weight'
    elif any(s in str(net_qty).lower() for s in ['piece', 'count', 'unit', 'item', 'each']):
        manner = 'count'
    
    # Check for proper symbols (bilingual)
    uses_symbols = any(sym in str(net_qty) for sym in ALL_METRIC_SYMBOLS)
    
    # Check for written out units
    written_units = any(word in str(net_qty).lower() for word in 
        ['gram', 'kilogram', 'litre', 'liter', 'millilitre', 'milliliter'])
    
    # Extract numeric value
    numeric_match = re.search(r'(\d+\.?\d*)', str(net_qty))
    numeric_value = float(numeric_match.group(1)) if numeric_match else None
    
    return {
        'present': has_net_qty,
        'value': net_qty,
        'numeric_value': numeric_value,
        'has_metric': has_metric,
        'metric_units': metric_units_found,
        'manner': manner,
        'uses_symbols': uses_symbols,
        'written_units': written_units
    }


def evaluate_net_qty_rule_1(label_data: Dict, qty_info: Dict) -> Dict[str, Any]:
    """Rule 1: Is a net quantity declaration present?"""
    
    compliant = qty_info['present']
    
    return {
        "rule_id": "net_qty_present",
        "rule_number": 1,
        "rule_text": NET_QUANTITY_RULES[1]["text"],
        "compliant": compliant,
        "confidence": 0.9 if qty_info['present'] else 0.7,
        "finding": f"Net quantity {'found' if compliant else 'not detected'}: {qty_info['value']}" if compliant else "No net quantity declaration found on label",
        "reasoning": "Checked for presence of net quantity declaration in extracted label data",
        "recommendations": [] if compliant else ["Add net quantity declaration to label"],
        "regulatory_references": [NET_QUANTITY_RULES[1]["citation"]]
    }


def evaluate_net_qty_rule_2(label_data: Dict, qty_info: Dict, rule_1_result: Dict) -> Dict[str, Any]:
    """Rule 2: If not present, is the product exempt?"""
    
    if rule_1_result.get('compliant'):
        return {
            "rule_id": "net_qty_exempt",
            "rule_number": 2,
            "rule_text": NET_QUANTITY_RULES[2]["text"],
            "compliant": True,
            "confidence": 0.95,
            "finding": "Not applicable - net quantity is present",
            "reasoning": "Rule 1 passed, exemption check not required",
            "recommendations": [],
            "regulatory_references": [NET_QUANTITY_RULES[2]["citation"]]
        }
    
    # Check for exemption indicators
    product_type = str(label_data.get('product_type', '')).lower()
    exemption_found = None
    
    exempt_products = ['fresh fruit', 'fresh vegetable', 'one bite', 'individual portion']
    for exempt in exempt_products:
        if exempt in product_type:
            exemption_found = exempt
            break
    
    return {
        "rule_id": "net_qty_exempt",
        "rule_number": 2,
        "rule_text": NET_QUANTITY_RULES[2]["text"],
        "compliant": exemption_found is not None,
        "confidence": 0.6,
        "finding": f"Exemption may apply: {exemption_found}" if exemption_found else "No exemption detected - net quantity required",
        "reasoning": f"Checked product type '{product_type}' against exemption categories",
        "recommendations": [] if exemption_found else ["Add net quantity declaration or verify exemption eligibility"],
        "regulatory_references": [NET_QUANTITY_RULES[2]["citation"]]
    }


def evaluate_net_qty_rule_3(label_data: Dict, qty_info: Dict) -> Dict[str, Any]:
    """Rule 3: Is the net quantity declared on the PDP?"""
    
    # If net quantity is present, assume it's on PDP (OCR typically from PDP)
    compliant = qty_info['present']
    
    return {
        "rule_id": "net_qty_on_pdp",
        "rule_number": 3,
        "rule_text": NET_QUANTITY_RULES[3]["text"],
        "compliant": compliant if qty_info['present'] else None,
        "confidence": 0.75 if compliant else 0.5,
        "finding": "Net quantity appears on principal display panel" if compliant else "Cannot verify PDP placement",
        "reasoning": "Net quantity extracted from label images, typically from principal display panel",
        "recommendations": [] if compliant else ["Ensure net quantity is on principal display panel"],
        "regulatory_references": [NET_QUANTITY_RULES[3]["citation"]]
    }


def evaluate_net_qty_rule_4(label_data: Dict, qty_info: Dict) -> Dict[str, Any]:
    """Rule 4: Is it in metric units?"""
    
    if not qty_info['present']:
        return {
            "rule_id": "net_qty_metric_units",
            "rule_number": 4,
            "rule_text": NET_QUANTITY_RULES[4]["text"],
            "compliant": None,
            "confidence": 0.0,
            "finding": "Cannot evaluate - no net quantity found",
            "reasoning": "Net quantity not present",
            "recommendations": [],
            "regulatory_references": [NET_QUANTITY_RULES[4]["citation"]]
        }
    
    compliant = qty_info['has_metric']
    
    return {
        "rule_id": "net_qty_metric_units",
        "rule_number": 4,
        "rule_text": NET_QUANTITY_RULES[4]["text"],
        "compliant": compliant,
        "confidence": 0.85 if compliant else 0.7,
        "finding": f"Metric units {'detected' if compliant else 'not detected'}: {qty_info['metric_units']}" if compliant else "No metric units found in net quantity",
        "reasoning": f"Analyzed net quantity '{qty_info['value']}' for metric unit symbols",
        "recommendations": [] if compliant else ["Use metric units (g, kg, ml, mL, L)"],
        "regulatory_references": [NET_QUANTITY_RULES[4]["citation"]]
    }


def evaluate_net_qty_rule_5(label_data: Dict, qty_info: Dict) -> Dict[str, Any]:
    """Rule 5: Retail bulk packaging alternative"""
    
    # This is an alternative to Rule 4, so if Rule 4 passes or product is retail bulk
    product_type = str(label_data.get('product_type', '')).lower()
    is_retail_bulk = 'retail' in product_type or 'bulk' in product_type
    
    return {
        "rule_id": "net_qty_retail_bulk",
        "rule_number": 5,
        "rule_text": NET_QUANTITY_RULES[5]["text"],
        "compliant": True if qty_info['has_metric'] else is_retail_bulk,
        "confidence": 0.7,
        "finding": "Metric units used" if qty_info['has_metric'] else ("Retail bulk exemption may apply" if is_retail_bulk else "Standard metric requirement applies"),
        "reasoning": "Alternative metric/Canadian units option for retail bulk packaging",
        "recommendations": [],
        "regulatory_references": [NET_QUANTITY_RULES[5]["citation"]]
    }


def evaluate_net_qty_rule_6(label_data: Dict, qty_info: Dict) -> Dict[str, Any]:
    """Rule 6: Appropriate manner (volume, weight, count)"""
    
    if not qty_info['present']:
        return {
            "rule_id": "net_qty_manner",
            "rule_number": 6,
            "rule_text": NET_QUANTITY_RULES[6]["text"],
            "compliant": None,
            "confidence": 0.0,
            "finding": "Cannot evaluate - no net quantity found",
            "reasoning": "Net quantity not present",
            "recommendations": [],
            "regulatory_references": [NET_QUANTITY_RULES[6]["citation"]]
        }
    
    manner = qty_info['manner']
    product_type = str(label_data.get('product_type', '')).lower()
    
    # Basic heuristics for appropriate manner
    appropriate = manner != 'unknown'
    
    return {
        "rule_id": "net_qty_manner",
        "rule_number": 6,
        "rule_text": NET_QUANTITY_RULES[6]["text"],
        "compliant": appropriate,
        "confidence": 0.7,
        "finding": f"Net quantity declared by {manner}" if appropriate else "Unable to determine measurement manner",
        "reasoning": f"Detected measurement type: {manner} for product type: {product_type}",
        "recommendations": [] if appropriate else ["Verify appropriate measurement manner is used"],
        "regulatory_references": [NET_QUANTITY_RULES[6]["citation"]]
    }


def evaluate_net_qty_rule_7(label_data: Dict, qty_info: Dict) -> Dict[str, Any]:
    """Rule 7: Rounded to 3 figures unless below 100"""
    
    if not qty_info['present'] or qty_info['numeric_value'] is None:
        return {
            "rule_id": "net_qty_rounding",
            "rule_number": 7,
            "rule_text": NET_QUANTITY_RULES[7]["text"],
            "compliant": None,
            "confidence": 0.0,
            "finding": "Cannot evaluate - no numeric value found",
            "reasoning": "Net quantity numeric value not extractable",
            "recommendations": [],
            "regulatory_references": [NET_QUANTITY_RULES[7]["citation"]]
        }
    
    value = qty_info['numeric_value']
    
    # Check rounding: if >= 100, should have max 3 significant figures
    if value >= 100:
        sig_figs = len(str(int(value)))
        compliant = sig_figs <= 3
    else:
        compliant = True  # No restriction below 100
    
    return {
        "rule_id": "net_qty_rounding",
        "rule_number": 7,
        "rule_text": NET_QUANTITY_RULES[7]["text"],
        "compliant": compliant,
        "confidence": 0.8,
        "finding": f"Numeric value {value} - rounding appears {'correct' if compliant else 'incorrect'}",
        "reasoning": f"Checked if value {value} follows 3-figure rounding rule",
        "recommendations": [] if compliant else ["Round net quantity to 3 significant figures"],
        "regulatory_references": [NET_QUANTITY_RULES[7]["citation"]]
    }


def evaluate_net_qty_rule_8(label_data: Dict, qty_info: Dict) -> Dict[str, Any]:
    """Rule 8: Correct bilingual symbols used"""
    
    if not qty_info['present']:
        return {
            "rule_id": "net_qty_symbols",
            "rule_number": 8,
            "rule_text": NET_QUANTITY_RULES[8]["text"],
            "compliant": None,
            "confidence": 0.0,
            "finding": "Cannot evaluate - no net quantity found",
            "reasoning": "Net quantity not present",
            "recommendations": [],
            "regulatory_references": [NET_QUANTITY_RULES[8]["citation"]]
        }
    
    uses_correct_symbols = qty_info['uses_symbols']
    
    return {
        "rule_id": "net_qty_symbols",
        "rule_number": 8,
        "rule_text": NET_QUANTITY_RULES[8]["text"],
        "compliant": uses_correct_symbols,
        "confidence": 0.8,
        "finding": f"Bilingual symbols {'used' if uses_correct_symbols else 'not detected'}: {qty_info['metric_units']}",
        "reasoning": "Checked for standard metric symbols (ml, mL, L, g, kg)",
        "recommendations": [] if uses_correct_symbols else ["Use standard bilingual symbols"],
        "regulatory_references": [NET_QUANTITY_RULES[8]["citation"]]
    }


def evaluate_net_qty_rule_9(label_data: Dict, qty_info: Dict) -> Dict[str, Any]:
    """Rule 9: Written out units in both languages"""
    
    if not qty_info['written_units']:
        return {
            "rule_id": "net_qty_written_units",
            "rule_number": 9,
            "rule_text": NET_QUANTITY_RULES[9]["text"],
            "compliant": True,  # Not applicable if using symbols
            "confidence": 0.9,
            "finding": "Symbols used - written unit requirement not applicable",
            "reasoning": "Net quantity uses abbreviated symbols, not written words",
            "recommendations": [],
            "regulatory_references": [NET_QUANTITY_RULES[9]["citation"]]
        }
    
    # Check for both English and French written units
    net_qty_text = str(qty_info['value']).lower()
    has_english = any(w in net_qty_text for w in ['gram', 'kilogram', 'liter', 'litre', 'milliliter'])
    has_french = any(w in net_qty_text for w in ['gramme', 'kilogramme', 'litre', 'millilitre'])
    
    bilingual = has_english and has_french
    
    return {
        "rule_id": "net_qty_written_units",
        "rule_number": 9,
        "rule_text": NET_QUANTITY_RULES[9]["text"],
        "compliant": bilingual,
        "confidence": 0.7,
        "finding": f"Written units {'in both languages' if bilingual else 'may need French translation'}",
        "reasoning": "Checked for bilingual written unit declarations",
        "recommendations": [] if bilingual else ["Include both English and French unit names"],
        "regulatory_references": [NET_QUANTITY_RULES[9]["citation"]]
    }


def evaluate_net_qty_rule_10(label_data: Dict, qty_info: Dict) -> Dict[str, Any]:
    """Rule 10: Type height and bold face requirements"""
    
    # Cannot verify visually from OCR alone
    return {
        "rule_id": "net_qty_type_height",
        "rule_number": 10,
        "rule_text": NET_QUANTITY_RULES[10]["text"],
        "compliant": None,  # Cannot verify from OCR
        "confidence": 0.3,
        "finding": "Type height and bold face require visual verification",
        "reasoning": "OCR extraction cannot verify font size or weight",
        "recommendations": ["Visually verify minimum type height (based on PDS size) and bold face"],
        "regulatory_references": [NET_QUANTITY_RULES[10]["citation"]]
    }


def evaluate_net_qty_rule_11(label_data: Dict, qty_info: Dict) -> Dict[str, Any]:
    """Rule 11: Optional Canadian units properly declared"""
    
    net_qty_text = str(qty_info.get('value', '')).lower()
    has_canadian = any(u in net_qty_text for u in ['oz', 'lb', 'pound', 'ounce'])
    
    if not has_canadian:
        return {
            "rule_id": "net_qty_canadian_units",
            "rule_number": 11,
            "rule_text": NET_QUANTITY_RULES[11]["text"],
            "compliant": True,
            "confidence": 0.9,
            "finding": "No optional Canadian units present - not applicable",
            "reasoning": "No Canadian units detected in net quantity",
            "recommendations": [],
            "regulatory_references": [NET_QUANTITY_RULES[11]["citation"]]
        }
    
    return {
        "rule_id": "net_qty_canadian_units",
        "rule_number": 11,
        "rule_text": NET_QUANTITY_RULES[11]["text"],
        "compliant": None,  # Need manual verification
        "confidence": 0.5,
        "finding": "Canadian units detected - verify proper declaration",
        "reasoning": "Canadian units present, manual verification required",
        "recommendations": ["Verify Canadian units follow CFIA format requirements"],
        "regulatory_references": [NET_QUANTITY_RULES[11]["citation"]]
    }


def evaluate_net_qty_rule_12(label_data: Dict, qty_info: Dict) -> Dict[str, Any]:
    """Rule 12: Optional US units properly identified"""
    
    net_qty_text = str(qty_info.get('value', '')).lower()
    has_us = any(u in net_qty_text for u in ['gallon', 'quart', 'fl oz', 'fluid oz'])
    
    if not has_us:
        return {
            "rule_id": "net_qty_us_units",
            "rule_number": 12,
            "rule_text": NET_QUANTITY_RULES[12]["text"],
            "compliant": True,
            "confidence": 0.9,
            "finding": "No US units present - not applicable",
            "reasoning": "No US gallons/quarts detected",
            "recommendations": [],
            "regulatory_references": [NET_QUANTITY_RULES[12]["citation"]]
        }
    
    return {
        "rule_id": "net_qty_us_units",
        "rule_number": 12,
        "rule_text": NET_QUANTITY_RULES[12]["text"],
        "compliant": None,
        "confidence": 0.5,
        "finding": "US units detected - verify proper identification",
        "reasoning": "US units present, verify proper format",
        "recommendations": ["Verify US units are properly identified per CFIA requirements"],
        "regulatory_references": [NET_QUANTITY_RULES[12]["citation"]]
    }


def evaluate_all_net_quantity_rules(label_data: Dict, client=None) -> Dict[str, Any]:
    """Evaluate all net quantity declaration rules."""
    
    # Extract net quantity info once
    qty_info = extract_net_quantity_info(label_data)
    
    results = {}
    
    # Evaluate each rule
    rule_1 = evaluate_net_qty_rule_1(label_data, qty_info)
    results['net_qty_rule_1'] = rule_1
    
    results['net_qty_rule_2'] = evaluate_net_qty_rule_2(label_data, qty_info, rule_1)
    results['net_qty_rule_3'] = evaluate_net_qty_rule_3(label_data, qty_info)
    results['net_qty_rule_4'] = evaluate_net_qty_rule_4(label_data, qty_info)
    results['net_qty_rule_5'] = evaluate_net_qty_rule_5(label_data, qty_info)
    results['net_qty_rule_6'] = evaluate_net_qty_rule_6(label_data, qty_info)
    results['net_qty_rule_7'] = evaluate_net_qty_rule_7(label_data, qty_info)
    results['net_qty_rule_8'] = evaluate_net_qty_rule_8(label_data, qty_info)
    results['net_qty_rule_9'] = evaluate_net_qty_rule_9(label_data, qty_info)
    results['net_qty_rule_10'] = evaluate_net_qty_rule_10(label_data, qty_info)
    results['net_qty_rule_11'] = evaluate_net_qty_rule_11(label_data, qty_info)
    results['net_qty_rule_12'] = evaluate_net_qty_rule_12(label_data, qty_info)
    
    # Calculate overall
    evaluated = [r for r in results.values() if r.get('compliant') is not None]
    compliant_count = sum(1 for r in evaluated if r.get('compliant'))
    
    results['net_qty_overall'] = {
        "compliant": all(r.get('compliant', True) for r in evaluated),
        "rules_passed": compliant_count,
        "rules_evaluated": len(evaluated),
        "total_rules": 12,
        "summary": f"Net quantity: {compliant_count}/{len(evaluated)} rules passed"
    }
    
    return results
