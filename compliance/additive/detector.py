import re
from compliance.additive.models import DetectedAdditive, AdditiveDetectionResult
from compliance.additive.constants import ALL_ADDITIVES, ADDITIVE_TO_CATEGORY


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


def detect_additives(ingredients: str, nft_text: str = "") -> AdditiveDetectionResult:
    """
    Detect food additives from ingredients list and NFT table text.
    """
    # Normalize inputs
    norm_ingredients = normalize_text(ingredients)
    norm_nft = normalize_text(nft_text)
    
    detected = []
    
    for additive in ALL_ADDITIVES:
        in_ingredients = additive in norm_ingredients
        in_nft = additive in norm_nft
        
        if in_ingredients or in_nft:
            # Determine source
            if in_ingredients and in_nft:
                source = "both"
            elif in_ingredients:
                source = "ingredients"
            else:
                source = "nft"
            
            detected.append(DetectedAdditive(
                name=additive,
                category=ADDITIVE_TO_CATEGORY[additive],
                source=source
            ))
    
    return AdditiveDetectionResult(
        detected=detected,
        has_additives=len(detected) > 0
    )
