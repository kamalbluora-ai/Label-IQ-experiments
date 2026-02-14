import re
from typing import List
from compliance.allergens_gluten.models import (
    DetectedAllergenOrGluten,
    AllergenGlutenDetectionResult,
)
from compliance.allergens_gluten.constants import (
    ALL_ALLERGEN_KEYWORDS,
    ALL_GLUTEN_KEYWORDS,
    ALLERGEN_KEYWORD_TO_CATEGORY,
    GLUTEN_KEYWORD_TO_CATEGORY,
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


def detect_allergens_gluten(ingredients: str) -> AllergenGlutenDetectionResult:
    """
    Detect allergens and gluten sources from ingredients list.
    
    Args:
        ingredients: Raw ingredients text from label (typically ingredients_list_en)
    
    Returns:
        AllergenGlutenDetectionResult with detected items
    """
    norm_ingredients = normalize_text(ingredients)
    
    detected: List[DetectedAllergenOrGluten] = []
    seen_categories = set()  # Deduplicate by category
    
    # Check for allergens
    for keyword in sorted(ALL_ALLERGEN_KEYWORDS, key=len, reverse=True):
        if keyword in norm_ingredients:
            category = ALLERGEN_KEYWORD_TO_CATEGORY[keyword]
            
            # Deduplicate: only one detection per category
            if category not in seen_categories:
                seen_categories.add(category)
                detected.append(DetectedAllergenOrGluten(
                    name=keyword,
                    category=category,
                    type="allergen",
                ))
    
    # Check for gluten sources
    for keyword in sorted(ALL_GLUTEN_KEYWORDS, key=len, reverse=True):
        if keyword in norm_ingredients:
            category = GLUTEN_KEYWORD_TO_CATEGORY[keyword]
            
            # Deduplicate: only one detection per category
            dedup_key = f"gluten:{category}"
            if dedup_key not in seen_categories:
                seen_categories.add(dedup_key)
                detected.append(DetectedAllergenOrGluten(
                    name=keyword,
                    category=category,
                    type="gluten",
                ))
    
    has_allergens = any(item.type == "allergen" for item in detected)
    has_gluten = any(item.type == "gluten" for item in detected)
    
    return AllergenGlutenDetectionResult(
        detected=detected,
        has_allergens=has_allergens,
        has_gluten=has_gluten,
    )
