"""
Dealer Name and Principal Place of Business Rule Evaluation Methods
Based on CFIA Food Labelling Requirements Checklist - Name and principal place of business section

6 consolidated rules covering:
- Presence of dealer name and address
- Exemption conditions
- Imported product requirements
- Type height requirements
- Location and legibility
"""

import re
from typing import Dict, Any, List


# Dealer name and business rules
DEALER_RULES = {
    1: {
        "id": "dealer_present",
        "text": "Is a name and principal place of business present?",
        "citation": "https://inspection.canada.ca/en/food-labels/labelling/industry/name-and-principal-place-business"
    },
    2: {
        "id": "dealer_address",
        "text": "Is the address complete (city and country for Canadian, or complete address)?",
        "citation": "https://inspection.canada.ca/en/food-labels/labelling/industry/name-and-principal-place-business"
    },
    3: {
        "id": "dealer_imported",
        "text": "For imported products, is 'Imported by/for' with Canadian address present?",
        "citation": "https://inspection.canada.ca/en/food-labels/labelling/industry/name-and-principal-place-business"
    },
    4: {
        "id": "dealer_type_height",
        "text": "Is type height at least 1.6mm (or 0.8mm for small packages)?",
        "citation": "https://inspection.canada.ca/en/food-labels/labelling/industry/legibility-and-location#s15c3"
    },
    5: {
        "id": "dealer_location",
        "text": "Is dealer information on a label panel (not solely on bottom)?",
        "citation": "https://inspection.canada.ca/en/food-labels/labelling/industry/name-and-principal-place-business"
    },
    6: {
        "id": "dealer_legibility",
        "text": "Is dealer information readily discernible and legible?",
        "citation": "https://inspection.canada.ca/en/food-labels/labelling/industry/name-and-principal-place-business"
    }
}

# Canadian provinces and territories
CANADIAN_PROVINCES = [
    'ontario', 'quebec', 'québec', 'british columbia', 'alberta', 'manitoba',
    'saskatchewan', 'nova scotia', 'new brunswick', 'newfoundland', 'pei',
    'prince edward island', 'yukon', 'northwest territories', 'nunavut',
    'on', 'qc', 'bc', 'ab', 'mb', 'sk', 'ns', 'nb', 'nl', 'pe', 'yt', 'nt', 'nu'
]


def extract_dealer_info(label_data: Dict) -> Dict[str, Any]:
    """Extract dealer/business information from label data"""
    
    # Get relevant fields
    manufacturer = str(label_data.get('manufacturer', '') or '')
    distributor = str(label_data.get('distributor', '') or '')
    dealer = str(label_data.get('dealer', '') or '')
    address = str(label_data.get('address', '') or '')
    importer = str(label_data.get('importer', '') or '')
    
    all_text = (manufacturer + ' ' + distributor + ' ' + dealer + ' ' + address + ' ' + importer).lower()
    
    # Check for company name
    has_company = bool(manufacturer.strip() or distributor.strip() or dealer.strip())
    
    # Check for address
    has_address = bool(address.strip()) or any(prov in all_text for prov in CANADIAN_PROVINCES)
    
    # Check for Canadian address indicators
    has_canada = 'canada' in all_text or any(prov in all_text for prov in CANADIAN_PROVINCES)
    
    # Check for imported by
    has_imported_by = any(imp in all_text for imp in [
        'imported by', 'imported for', 'importé par', 'importé pour',
        'distributed by', 'distribué par'
    ])
    
    # Check for city names (simple heuristic)
    has_city = any(city in all_text for city in [
        'toronto', 'montreal', 'vancouver', 'calgary', 'ottawa', 'edmonton',
        'winnipeg', 'quebec city', 'hamilton', 'kitchener', 'london', 'markham'
    ])
    
    return {
        'has_company': has_company,
        'has_address': has_address or has_city,
        'has_canada': has_canada,
        'has_imported_by': has_imported_by,
        'company_name': manufacturer or distributor or dealer,
        'address_text': address,
        'all_text': all_text
    }


def evaluate_dealer_rule_1(label_data: Dict, info: Dict) -> Dict[str, Any]:
    """Rule 1: Is dealer name present?"""
    
    has_company = info['has_company']
    company = info['company_name']
    
    return {
        "rule_id": "dealer_present",
        "rule_number": 1,
        "rule_text": DEALER_RULES[1]["text"],
        "compliant": has_company,
        "confidence": 0.85 if has_company else 0.5,
        "finding": f"Dealer/manufacturer name found: {company[:40]}..." if has_company else "Dealer/manufacturer name not detected",
        "reasoning": "Checked for manufacturer, distributor, or dealer name",
        "recommendations": [] if has_company else ["Add dealer name or manufacturer information"],
        "regulatory_references": [DEALER_RULES[1]["citation"]]
    }


def evaluate_dealer_rule_2(label_data: Dict, info: Dict) -> Dict[str, Any]:
    """Rule 2: Is address complete?"""
    
    has_address = info['has_address']
    has_canada = info['has_canada']
    
    if not info['has_company']:
        return {
            "rule_id": "dealer_address",
            "rule_number": 2,
            "rule_text": DEALER_RULES[2]["text"],
            "compliant": None,
            "confidence": 0.0,
            "finding": "Not applicable - no dealer name detected",
            "reasoning": "No dealer to evaluate address for",
            "recommendations": [],
            "regulatory_references": [DEALER_RULES[2]["citation"]]
        }
    
    complete = has_address and has_canada
    
    return {
        "rule_id": "dealer_address",
        "rule_number": 2,
        "rule_text": DEALER_RULES[2]["text"],
        "compliant": complete,
        "confidence": 0.7 if complete else 0.5,
        "finding": f"Address found (Canada: {'Yes' if has_canada else 'Not detected'})" if has_address else "Complete address not detected",
        "reasoning": "Checked for city and Canada/province",
        "recommendations": [] if complete else ["Include city and country (Canada) in address"],
        "regulatory_references": [DEALER_RULES[2]["citation"]]
    }


def evaluate_dealer_rule_3(label_data: Dict, info: Dict) -> Dict[str, Any]:
    """Rule 3: Imported products requirements"""
    
    has_imported_by = info['has_imported_by']
    
    # Check if product appears to be imported
    origin = str(label_data.get('country_of_origin', '')).lower()
    is_imported = origin and 'canada' not in origin
    
    if not is_imported:
        return {
            "rule_id": "dealer_imported",
            "rule_number": 3,
            "rule_text": DEALER_RULES[3]["text"],
            "compliant": True,
            "confidence": 0.7,
            "finding": "Product appears to be Canadian or origin not specified",
            "reasoning": "Import declaration may not be required",
            "recommendations": [],
            "regulatory_references": [DEALER_RULES[3]["citation"]]
        }
    
    return {
        "rule_id": "dealer_imported",
        "rule_number": 3,
        "rule_text": DEALER_RULES[3]["text"],
        "compliant": has_imported_by,
        "confidence": 0.75 if has_imported_by else 0.5,
        "finding": "'Imported by/for' declaration found" if has_imported_by else "Product may be imported - verify 'Imported by' present",
        "reasoning": f"Origin appears to be: {origin}. Import declaration: {'Yes' if has_imported_by else 'Not detected'}",
        "recommendations": [] if has_imported_by else ["Add 'Imported by/Importé par' with Canadian address"],
        "regulatory_references": [DEALER_RULES[3]["citation"]]
    }


def evaluate_dealer_rule_4(label_data: Dict, info: Dict) -> Dict[str, Any]:
    """Rule 4: Type height requirements"""
    
    if not info['has_company']:
        return {
            "rule_id": "dealer_type_height",
            "rule_number": 4,
            "rule_text": DEALER_RULES[4]["text"],
            "compliant": None,
            "confidence": 0.0,
            "finding": "Not applicable - no dealer name detected",
            "reasoning": "No dealer text to evaluate",
            "recommendations": [],
            "regulatory_references": [DEALER_RULES[4]["citation"]]
        }
    
    return {
        "rule_id": "dealer_type_height",
        "rule_number": 4,
        "rule_text": DEALER_RULES[4]["text"],
        "compliant": None,
        "confidence": 0.4,
        "finding": "Type height requires visual verification",
        "reasoning": "Cannot verify 1.6mm height from OCR",
        "recommendations": ["Verify dealer info is at least 1.6mm (or 0.8mm for small packages)"],
        "regulatory_references": [DEALER_RULES[4]["citation"]]
    }


def evaluate_dealer_rule_5(label_data: Dict, info: Dict) -> Dict[str, Any]:
    """Rule 5: Location requirements"""
    
    if not info['has_company']:
        return {
            "rule_id": "dealer_location",
            "rule_number": 5,
            "rule_text": DEALER_RULES[5]["text"],
            "compliant": None,
            "confidence": 0.0,
            "finding": "Not applicable - no dealer name detected",
            "reasoning": "No dealer text to evaluate location",
            "recommendations": [],
            "regulatory_references": [DEALER_RULES[5]["citation"]]
        }
    
    return {
        "rule_id": "dealer_location",
        "rule_number": 5,
        "rule_text": DEALER_RULES[5]["text"],
        "compliant": None,
        "confidence": 0.4,
        "finding": "Location requires visual verification",
        "reasoning": "Cannot verify panel location from OCR",
        "recommendations": ["Verify dealer info is not solely on bottom of package"],
        "regulatory_references": [DEALER_RULES[5]["citation"]]
    }


def evaluate_dealer_rule_6(label_data: Dict, info: Dict) -> Dict[str, Any]:
    """Rule 6: Legibility"""
    
    if not info['has_company']:
        return {
            "rule_id": "dealer_legibility",
            "rule_number": 6,
            "rule_text": DEALER_RULES[6]["text"],
            "compliant": None,
            "confidence": 0.0,
            "finding": "Not applicable - no dealer name detected",
            "reasoning": "No dealer text to evaluate",
            "recommendations": [],
            "regulatory_references": [DEALER_RULES[6]["citation"]]
        }
    
    # If OCR could read it, it's likely legible
    return {
        "rule_id": "dealer_legibility",
        "rule_number": 6,
        "rule_text": DEALER_RULES[6]["text"],
        "compliant": True,
        "confidence": 0.7,
        "finding": "Dealer information was readable by OCR - appears legible",
        "reasoning": "OCR successfully extracted dealer information",
        "recommendations": [],
        "regulatory_references": [DEALER_RULES[6]["citation"]]
    }


def evaluate_all_dealer_rules(label_data: Dict, client=None) -> Dict[str, Any]:
    """Evaluate all dealer name and business rules."""
    
    info = extract_dealer_info(label_data)
    results = {}
    
    results['dealer_rule_1'] = evaluate_dealer_rule_1(label_data, info)
    results['dealer_rule_2'] = evaluate_dealer_rule_2(label_data, info)
    results['dealer_rule_3'] = evaluate_dealer_rule_3(label_data, info)
    results['dealer_rule_4'] = evaluate_dealer_rule_4(label_data, info)
    results['dealer_rule_5'] = evaluate_dealer_rule_5(label_data, info)
    results['dealer_rule_6'] = evaluate_dealer_rule_6(label_data, info)
    
    evaluated = [r for r in results.values() if r.get('compliant') is not None]
    compliant_count = sum(1 for r in evaluated if r.get('compliant'))
    
    results['dealer_overall'] = {
        "compliant": all(r.get('compliant', True) for r in evaluated),
        "rules_passed": compliant_count,
        "rules_evaluated": len(evaluated),
        "total_rules": 6,
        "summary": f"Dealer name and business: {compliant_count}/{len(evaluated)} rules passed"
    }
    
    return results
