from typing import List, Literal
from pydantic import BaseModel


class DetectedAllergenOrGluten(BaseModel):
    """Represents a single detected allergen or gluten source."""
    name: str
    category: str
    type: Literal["allergen", "gluten"]


class AllergenGlutenDetectionResult(BaseModel):
    """Complete allergen and gluten detection result."""
    detected: List[DetectedAllergenOrGluten]
    has_allergens: bool
    has_gluten: bool
