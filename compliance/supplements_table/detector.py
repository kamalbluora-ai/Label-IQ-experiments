import re
from compliance.supplements_table.models import DetectedSupplement, SupplementDetectionResult
from compliance.supplements_table.constants import ALL_SUPPLEMENTS, SUPPLEMENT_TO_CATEGORY


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


def detect_supplements(nft_text: str, ingredients: str = "") -> SupplementDetectionResult:
    """
    Detect supplements from NFT table text and ingredients list.
    """
    # Normalize inputs
    norm_nft = normalize_text(nft_text)
    norm_ingredients = normalize_text(ingredients)
    
    detected = []
    
    for supplement in ALL_SUPPLEMENTS:
        in_nft = supplement in norm_nft
        in_ingredients = supplement in norm_ingredients
        
        if in_nft or in_ingredients:
            # Determine source
            if in_nft and in_ingredients:
                source = "both"
            elif in_nft:
                source = "nft"
            else:
                source = "ingredients"
            
            detected.append(DetectedSupplement(
                name=supplement,
                category=SUPPLEMENT_TO_CATEGORY[supplement],
                source=source
            ))
    
    return SupplementDetectionResult(
        detected=detected,
        has_supplements=len(detected) > 0
    )
