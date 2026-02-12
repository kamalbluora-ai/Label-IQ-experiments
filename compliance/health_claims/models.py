from typing import List, Literal
from pydantic import BaseModel


class DetectedClaim(BaseModel):
    """Represents a single detected health/nutrient claim."""
    name: str
    category: str
    claim_type: Literal[
        "disease_risk_reduction",
        "nutrient_function",
        "nutrient_content",
        "probiotic",
    ]
    source: Literal[
        "health_claims",
        "nutrient_content",
        "nutrient_function",
        "label_text",
    ]


class HealthClaimsDetectionResult(BaseModel):
    """Complete health claims detection result."""
    detected: List[DetectedClaim]
    has_health_claims: bool
