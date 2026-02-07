import re
from typing import Dict
from compliance.sweeteners.models import DetectedSweetener, SweetenerDetectionResult
from compliance.sweeteners.constants import (
    ALL_WITH_QUANTITY, ALL_NO_QUANTITY,
    SWEETENER_TO_CATEGORY_WITH_QTY, SWEETENER_TO_CATEGORY_NO_QTY
)


def normalize_text(text: str) -> str:
    """
    Normalize text for matching.   
    - Lowercase
    - Remove special characters (keep alphanumeric and spaces)
    - Collapse whitespace
    """
    if not text:
        return ""
    
    # Lowercase
    text = text.lower()
    
    # Remove special characters, keep alphanumeric and spaces
    text = re.sub(r'[^a-z0-9\s]', ' ', text)
    
    # Collapse whitespace
    text = re.sub(r'\s+', ' ', text).strip()
    
    return text


def parse_nft_to_dict(nft_text: str) -> Dict[str, str]:
    """
    Parse NFT table text into key-value pairs.
    """
    if not nft_text:
        return {}
    
    normalized = normalize_text(nft_text)
    result = {}
    
    # Pattern: nutrient name followed by numeric value with optional unit
    pattern = r'([a-z\s]+?)\s+([\d.]+\s*[gm]?[gl]?)\b'
    
    for match in re.finditer(pattern, normalized):
        name = match.group(1).strip()
        value = match.group(2).strip()
        result[name] = value
    
    return result


def detect_sweeteners(ingredients: str, nft_text: str) -> SweetenerDetectionResult:
    """
    Detect sweeteners from ingredients list and NFT table.
    """
    # Normalize inputs
    norm_ingredients = normalize_text(ingredients)
    norm_nft = normalize_text(nft_text)
    nft_dict = parse_nft_to_dict(nft_text)
    
    detected = []
    
    # Check with_quantity sweeteners
    for sweetener in ALL_WITH_QUANTITY:
        in_ingredients = sweetener in norm_ingredients
        in_nft = sweetener in norm_nft
        
        if in_ingredients or in_nft:
            # Determine source
            if in_ingredients and in_nft:
                source = "both"
            elif in_ingredients:
                source = "ingredients"
            else:
                source = "nft"
            
            # Try to extract quantity from NFT
            quantity = None
            for nft_key, nft_value in nft_dict.items():
                if sweetener in nft_key:
                    quantity = nft_value
                    break
            
            # Set status only if needs_review (with_quantity but no quantity found)
            status = "needs_review" if not quantity else None
            
            detected.append(DetectedSweetener(
                name=sweetener,
                sweetener_category=SWEETENER_TO_CATEGORY_WITH_QTY[sweetener],
                category="with_quantity",
                quantity=quantity,
                source=source,
                status=status
            ))
    
    # Check no_quantity sweeteners
    for sweetener in ALL_NO_QUANTITY:
        in_ingredients = sweetener in norm_ingredients
        in_nft = sweetener in norm_nft
        
        if in_ingredients or in_nft:
            # Determine source
            if in_ingredients and in_nft:
                source = "both"
            elif in_ingredients:
                source = "ingredients"
            else:
                source = "nft"
            
            detected.append(DetectedSweetener(
                name=sweetener,
                sweetener_category=SWEETENER_TO_CATEGORY_NO_QTY[sweetener],
                category="no_quantity",
                quantity=None,
                source=source
            ))
    
    return SweetenerDetectionResult(
        detected=detected,
        has_quantity_sweeteners=any(d.category == "with_quantity" for d in detected),
        has_no_quantity_sweeteners=any(d.category == "no_quantity" for d in detected)
    )
