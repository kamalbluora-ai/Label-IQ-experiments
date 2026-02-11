from typing import List, Literal
from pydantic import BaseModel


class DetectedSupplement(BaseModel):
    """Represents a single detected supplement."""
    name: str
    category: str
    source: Literal["nft", "ingredients", "both"]


class SupplementDetectionResult(BaseModel):
    """Complete supplement detection result."""
    detected: List[DetectedSupplement]
    has_supplements: bool
