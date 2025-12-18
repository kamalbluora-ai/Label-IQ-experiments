"""
Date Marking Rule Evaluation Methods
Based on CFIA Food Labelling Requirements Checklist - Date markings section

10 consolidated rules covering:
- Best before date requirements
- Packaged on date requirements
- Expiration date (for special dietary/infant formula)
- Storage instructions
- Date format and presentation
- Legibility requirements
"""

import re
from typing import Dict, Any, List


# Date marking rules - consolidated from CFIA checklist
DATE_MARKING_RULES = {
    1: {
        "id": "best_before_present",
        "text": "Is a 'best before' date present if required (durable life ≤90 days)?",
        "citation": "https://inspection.canada.ca/en/food-labels/labelling/industry/date-markings-and-storage-instructions#s1c1"
    },
    2: {
        "id": "best_before_wording",
        "text": "Is correct bilingual wording used ('best before' / 'meilleur avant')?",
        "citation": "https://inspection.canada.ca/en/food-labels/labelling/industry/date-markings-and-storage-instructions#s1c1"
    },
    3: {
        "id": "best_before_format",
        "text": "Is the date in correct format (year/month/day with bilingual month symbols)?",
        "citation": "https://inspection.canada.ca/en/food-labels/labelling/industry/date-markings-and-storage-instructions"
    },
    4: {
        "id": "best_before_location",
        "text": "Is date location acceptable (with reference if on bottom)?",
        "citation": "https://inspection.canada.ca/en/food-labels/labelling/industry/date-markings-and-storage-instructions"
    },
    5: {
        "id": "packaged_on_present",
        "text": "Is 'packaged on' date present if required (packaged at retail with ≤90 day durable life)?",
        "citation": "https://inspection.canada.ca/en/food-labels/labelling/industry/date-markings-and-storage-instructions#s3c1"
    },
    6: {
        "id": "packaged_on_wording",
        "text": "Is correct wording 'packaged on' / 'empaqueté le' used?",
        "citation": "https://inspection.canada.ca/en/food-labels/labelling/industry/date-markings-and-storage-instructions#s3c1"
    },
    7: {
        "id": "expiration_date",
        "text": "Is expiration date present if required (special dietary use, infant formula)?",
        "citation": "https://inspection.canada.ca/en/food-labels/labelling/industry/date-markings-and-storage-instructions#s15c4"
    },
    8: {
        "id": "storage_instructions",
        "text": "Are storage instructions present if required (non-room temperature storage)?",
        "citation": "https://inspection.canada.ca/en/food-labels/labelling/industry/date-markings-and-storage-instructions#c5"
    },
    9: {
        "id": "date_grouped",
        "text": "Is date wording grouped with the date or clearly referenced?",
        "citation": "https://inspection.canada.ca/en/food-labels/labelling/industry/date-markings-and-storage-instructions"
    },
    10: {
        "id": "date_legibility",
        "text": "Is date information readily discernible and legible?",
        "citation": "https://inspection.canada.ca/en/food-labels/labelling/industry/date-markings-and-storage-instructions"
    }
}

# Bilingual month symbols
BILINGUAL_MONTHS = {
    'JA': 'January', 'FE': 'February', 'MR': 'March', 'AL': 'April',
    'MA': 'May', 'JN': 'June', 'JL': 'July', 'AU': 'August',
    'SE': 'September', 'OC': 'October', 'NO': 'November', 'DE': 'December'
}


def extract_date_info(label_data: Dict) -> Dict[str, Any]:
    """Extract date marking information from label data"""
    
    all_text = ''
    for key in ['best_before', 'packaged_on', 'expiration_date', 'date_markings', 'storage_instructions']:
        value = label_data.get(key, '')
        if value:
            all_text += ' ' + str(value)
    
    # Also check general extracted text
    general_text = str(label_data.get('extracted_text', '') or '')
    all_text += ' ' + general_text
    all_text = all_text.lower()
    
    # Check for best before
    has_best_before = any(bb in all_text for bb in [
        'best before', 'best by', 'bb', 'meilleur avant', 'ma'
    ])
    
    # Check for packaged on
    has_packaged_on = any(po in all_text for po in [
        'packaged on', 'packed on', 'empaqueté le', 'pack date'
    ])
    
    # Check for expiration
    has_expiration = any(exp in all_text for exp in [
        'expiration', 'expires', 'exp', 'use by', 'date limite'
    ])
    
    # Check for storage instructions
    has_storage = any(st in all_text for st in [
        'refrigerate', 'réfrigérer', 'keep cool', 'store', 'garder',
        'freeze', 'congeler', 'keep frozen', 'room temperature'
    ])
    
    # Check for bilingual date wording
    has_bilingual_date = ('best before' in all_text and 'meilleur avant' in all_text) or \
                         ('packaged on' in all_text and 'empaqueté le' in all_text)
    
    # Check for bilingual month symbols
    has_month_symbols = any(month in all_text.upper() for month in BILINGUAL_MONTHS.keys())
    
    # Check for date pattern (various formats)
    date_pattern = bool(re.search(r'\d{1,2}[/\-\.]\d{1,2}[/\-\.]\d{2,4}', all_text) or
                       re.search(r'\d{4}[/\-\.]\d{1,2}[/\-\.]\d{1,2}', all_text) or
                       re.search(r'[A-Z]{2}\s*\d{1,2}', all_text.upper()))
    
    # Check product type for special requirements
    product_type = str(label_data.get('product_type', '')).lower()
    is_infant_formula = 'infant' in product_type or 'formula' in product_type
    is_special_dietary = 'dietary' in product_type or 'supplement' in product_type
    
    return {
        'has_best_before': has_best_before,
        'has_packaged_on': has_packaged_on,
        'has_expiration': has_expiration,
        'has_storage': has_storage,
        'has_bilingual_date': has_bilingual_date,
        'has_month_symbols': has_month_symbols,
        'has_date_pattern': date_pattern,
        'is_infant_formula': is_infant_formula,
        'is_special_dietary': is_special_dietary,
        'all_text': all_text
    }


def evaluate_date_rule_1(label_data: Dict, info: Dict) -> Dict[str, Any]:
    """Rule 1: Best before date present if required"""
    
    has_bb = info['has_best_before']
    
    if has_bb:
        return {
            "rule_id": "best_before_present",
            "rule_number": 1,
            "rule_text": DATE_MARKING_RULES[1]["text"],
            "compliant": True,
            "confidence": 0.85,
            "finding": "Best before date detected on label",
            "reasoning": "Found best before or meilleur avant declaration",
            "recommendations": [],
            "regulatory_references": [DATE_MARKING_RULES[1]["citation"]]
        }
    
    return {
        "rule_id": "best_before_present",
        "rule_number": 1,
        "rule_text": DATE_MARKING_RULES[1]["text"],
        "compliant": None,
        "confidence": 0.5,
        "finding": "Best before date not detected - verify if required (durable life ≤90 days)",
        "reasoning": "Could not detect best before declaration. May be exempt if durable life >90 days",
        "recommendations": ["Verify if product requires best before date based on durable life"],
        "regulatory_references": [DATE_MARKING_RULES[1]["citation"]]
    }


def evaluate_date_rule_2(label_data: Dict, info: Dict) -> Dict[str, Any]:
    """Rule 2: Best before bilingual wording"""
    
    if not info['has_best_before']:
        return {
            "rule_id": "best_before_wording",
            "rule_number": 2,
            "rule_text": DATE_MARKING_RULES[2]["text"],
            "compliant": None,
            "confidence": 0.0,
            "finding": "Not applicable - no best before date detected",
            "reasoning": "No best before date to evaluate",
            "recommendations": [],
            "regulatory_references": [DATE_MARKING_RULES[2]["citation"]]
        }
    
    has_bilingual = info['has_bilingual_date']
    
    return {
        "rule_id": "best_before_wording",
        "rule_number": 2,
        "rule_text": DATE_MARKING_RULES[2]["text"],
        "compliant": has_bilingual,
        "confidence": 0.75 if has_bilingual else 0.6,
        "finding": "Bilingual date wording detected" if has_bilingual else "Verify bilingual wording present",
        "reasoning": "Checked for both English and French date declarations",
        "recommendations": [] if has_bilingual else ["Ensure 'best before' / 'meilleur avant' are both present"],
        "regulatory_references": [DATE_MARKING_RULES[2]["citation"]]
    }


def evaluate_date_rule_3(label_data: Dict, info: Dict) -> Dict[str, Any]:
    """Rule 3: Date format (year/month/day with bilingual symbols)"""
    
    if not info['has_best_before'] and not info['has_packaged_on'] and not info['has_expiration']:
        return {
            "rule_id": "best_before_format",
            "rule_number": 3,
            "rule_text": DATE_MARKING_RULES[3]["text"],
            "compliant": None,
            "confidence": 0.0,
            "finding": "Not applicable - no date marking detected",
            "reasoning": "No date to evaluate format",
            "recommendations": [],
            "regulatory_references": [DATE_MARKING_RULES[3]["citation"]]
        }
    
    has_pattern = info['has_date_pattern']
    has_symbols = info['has_month_symbols']
    
    return {
        "rule_id": "best_before_format",
        "rule_number": 3,
        "rule_text": DATE_MARKING_RULES[3]["text"],
        "compliant": has_pattern,
        "confidence": 0.7 if has_pattern else 0.5,
        "finding": f"Date format detected. Bilingual month symbols: {'Yes' if has_symbols else 'Verify'}",
        "reasoning": "Checked for proper date format and bilingual month abbreviations",
        "recommendations": [] if has_pattern else ["Use bilingual month symbols (JA, FE, MR, AL, MA, JN, JL, AU, SE, OC, NO, DE)"],
        "regulatory_references": [DATE_MARKING_RULES[3]["citation"]]
    }


def evaluate_date_rule_4(label_data: Dict, info: Dict) -> Dict[str, Any]:
    """Rule 4: Date location"""
    
    if not info['has_best_before'] and not info['has_packaged_on'] and not info['has_expiration']:
        return {
            "rule_id": "best_before_location",
            "rule_number": 4,
            "rule_text": DATE_MARKING_RULES[4]["text"],
            "compliant": None,
            "confidence": 0.0,
            "finding": "Not applicable - no date marking detected",
            "reasoning": "No date to evaluate location",
            "recommendations": [],
            "regulatory_references": [DATE_MARKING_RULES[4]["citation"]]
        }
    
    return {
        "rule_id": "best_before_location",
        "rule_number": 4,
        "rule_text": DATE_MARKING_RULES[4]["text"],
        "compliant": None,
        "confidence": 0.4,
        "finding": "Date location requires visual verification",
        "reasoning": "Cannot verify date location from OCR text alone",
        "recommendations": ["Verify date is visible and if on bottom, reference made elsewhere"],
        "regulatory_references": [DATE_MARKING_RULES[4]["citation"]]
    }


def evaluate_date_rule_5(label_data: Dict, info: Dict) -> Dict[str, Any]:
    """Rule 5: Packaged on date present if required"""
    
    has_po = info['has_packaged_on']
    
    if has_po:
        return {
            "rule_id": "packaged_on_present",
            "rule_number": 5,
            "rule_text": DATE_MARKING_RULES[5]["text"],
            "compliant": True,
            "confidence": 0.85,
            "finding": "Packaged on date detected",
            "reasoning": "Found 'packaged on' or 'empaqueté le' declaration",
            "recommendations": [],
            "regulatory_references": [DATE_MARKING_RULES[5]["citation"]]
        }
    
    return {
        "rule_id": "packaged_on_present",
        "rule_number": 5,
        "rule_text": DATE_MARKING_RULES[5]["text"],
        "compliant": None,
        "confidence": 0.5,
        "finding": "Packaged on date not detected - verify if required (packaged at retail)",
        "reasoning": "May not be required if not packaged where sold at retail",
        "recommendations": ["Verify if product was packaged at retail location"],
        "regulatory_references": [DATE_MARKING_RULES[5]["citation"]]
    }


def evaluate_date_rule_6(label_data: Dict, info: Dict) -> Dict[str, Any]:
    """Rule 6: Packaged on wording"""
    
    if not info['has_packaged_on']:
        return {
            "rule_id": "packaged_on_wording",
            "rule_number": 6,
            "rule_text": DATE_MARKING_RULES[6]["text"],
            "compliant": None,
            "confidence": 0.0,
            "finding": "Not applicable - no packaged on date detected",
            "reasoning": "No packaged on date to evaluate",
            "recommendations": [],
            "regulatory_references": [DATE_MARKING_RULES[6]["citation"]]
        }
    
    all_text = info['all_text']
    has_bilingual = 'packaged on' in all_text and 'empaqueté le' in all_text
    
    return {
        "rule_id": "packaged_on_wording",
        "rule_number": 6,
        "rule_text": DATE_MARKING_RULES[6]["text"],
        "compliant": has_bilingual,
        "confidence": 0.75 if has_bilingual else 0.6,
        "finding": "Bilingual packaged on wording detected" if has_bilingual else "Verify bilingual wording present",
        "reasoning": "Checked for both English and French declarations",
        "recommendations": [] if has_bilingual else ["Ensure 'packaged on' / 'empaqueté le' are both present"],
        "regulatory_references": [DATE_MARKING_RULES[6]["citation"]]
    }


def evaluate_date_rule_7(label_data: Dict, info: Dict) -> Dict[str, Any]:
    """Rule 7: Expiration date for special products"""
    
    requires_exp = info['is_infant_formula'] or info['is_special_dietary']
    has_exp = info['has_expiration']
    
    if not requires_exp:
        return {
            "rule_id": "expiration_date",
            "rule_number": 7,
            "rule_text": DATE_MARKING_RULES[7]["text"],
            "compliant": True,
            "confidence": 0.8,
            "finding": "Not a special dietary or infant formula product - expiration date not required",
            "reasoning": "Product type does not require expiration date",
            "recommendations": [],
            "regulatory_references": [DATE_MARKING_RULES[7]["citation"]]
        }
    
    return {
        "rule_id": "expiration_date",
        "rule_number": 7,
        "rule_text": DATE_MARKING_RULES[7]["text"],
        "compliant": has_exp,
        "confidence": 0.8 if has_exp else 0.6,
        "finding": "Expiration date found" if has_exp else "Special product may require expiration date",
        "reasoning": f"Product appears to be {'infant formula' if info['is_infant_formula'] else 'special dietary'}, requires expiration date",
        "recommendations": [] if has_exp else ["Add expiration date for special dietary/infant formula products"],
        "regulatory_references": [DATE_MARKING_RULES[7]["citation"]]
    }


def evaluate_date_rule_8(label_data: Dict, info: Dict) -> Dict[str, Any]:
    """Rule 8: Storage instructions"""
    
    has_storage = info['has_storage']
    
    return {
        "rule_id": "storage_instructions",
        "rule_number": 8,
        "rule_text": DATE_MARKING_RULES[8]["text"],
        "compliant": has_storage if has_storage else None,
        "confidence": 0.7 if has_storage else 0.5,
        "finding": "Storage instructions detected" if has_storage else "Storage instructions not detected - verify if required",
        "reasoning": "Storage instructions required for products not stored at room temperature",
        "recommendations": [] if has_storage else ["Add storage instructions if product requires non-room-temperature storage"],
        "regulatory_references": [DATE_MARKING_RULES[8]["citation"]]
    }


def evaluate_date_rule_9(label_data: Dict, info: Dict) -> Dict[str, Any]:
    """Rule 9: Date wording grouped with date"""
    
    has_any_date = info['has_best_before'] or info['has_packaged_on'] or info['has_expiration']
    
    if not has_any_date:
        return {
            "rule_id": "date_grouped",
            "rule_number": 9,
            "rule_text": DATE_MARKING_RULES[9]["text"],
            "compliant": None,
            "confidence": 0.0,
            "finding": "Not applicable - no date marking detected",
            "reasoning": "No date to evaluate grouping",
            "recommendations": [],
            "regulatory_references": [DATE_MARKING_RULES[9]["citation"]]
        }
    
    return {
        "rule_id": "date_grouped",
        "rule_number": 9,
        "rule_text": DATE_MARKING_RULES[9]["text"],
        "compliant": None,
        "confidence": 0.4,
        "finding": "Date grouping requires visual verification",
        "reasoning": "Cannot verify date wording proximity from OCR",
        "recommendations": ["Verify date wording is grouped with the date or clearly referenced"],
        "regulatory_references": [DATE_MARKING_RULES[9]["citation"]]
    }


def evaluate_date_rule_10(label_data: Dict, info: Dict) -> Dict[str, Any]:
    """Rule 10: Date legibility"""
    
    has_any_date = info['has_best_before'] or info['has_packaged_on'] or info['has_expiration']
    
    if not has_any_date:
        return {
            "rule_id": "date_legibility",
            "rule_number": 10,
            "rule_text": DATE_MARKING_RULES[10]["text"],
            "compliant": None,
            "confidence": 0.0,
            "finding": "Not applicable - no date marking detected",
            "reasoning": "No date to evaluate legibility",
            "recommendations": [],
            "regulatory_references": [DATE_MARKING_RULES[10]["citation"]]
        }
    
    # If OCR could read it, it's likely legible
    return {
        "rule_id": "date_legibility",
        "rule_number": 10,
        "rule_text": DATE_MARKING_RULES[10]["text"],
        "compliant": True,
        "confidence": 0.7,
        "finding": "Date was readable by OCR - appears legible",
        "reasoning": "OCR successfully extracted date marking",
        "recommendations": [],
        "regulatory_references": [DATE_MARKING_RULES[10]["citation"]]
    }


def evaluate_all_date_marking_rules(label_data: Dict, client=None) -> Dict[str, Any]:
    """Evaluate all date marking rules."""
    
    info = extract_date_info(label_data)
    results = {}
    
    results['date_rule_1'] = evaluate_date_rule_1(label_data, info)
    results['date_rule_2'] = evaluate_date_rule_2(label_data, info)
    results['date_rule_3'] = evaluate_date_rule_3(label_data, info)
    results['date_rule_4'] = evaluate_date_rule_4(label_data, info)
    results['date_rule_5'] = evaluate_date_rule_5(label_data, info)
    results['date_rule_6'] = evaluate_date_rule_6(label_data, info)
    results['date_rule_7'] = evaluate_date_rule_7(label_data, info)
    results['date_rule_8'] = evaluate_date_rule_8(label_data, info)
    results['date_rule_9'] = evaluate_date_rule_9(label_data, info)
    results['date_rule_10'] = evaluate_date_rule_10(label_data, info)
    
    evaluated = [r for r in results.values() if r.get('compliant') is not None]
    compliant_count = sum(1 for r in evaluated if r.get('compliant'))
    
    results['date_overall'] = {
        "compliant": all(r.get('compliant', True) for r in evaluated),
        "rules_passed": compliant_count,
        "rules_evaluated": len(evaluated),
        "total_rules": 10,
        "summary": f"Date markings: {compliant_count}/{len(evaluated)} rules passed"
    }
    
    return results
