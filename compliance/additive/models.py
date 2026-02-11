from typing import List, Literal
from pydantic import BaseModel


class DetectedAdditive(BaseModel):
    """Represents a single detected additive."""
    name: str
    category: str
    source: Literal["ingredients", "nft", "both"]


class AdditiveDetectionResult(BaseModel):
    """Complete additive detection result."""
    detected: List[DetectedAdditive]
    has_additives: bool
