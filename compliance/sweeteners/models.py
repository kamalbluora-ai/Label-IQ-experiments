from typing import List, Literal, Optional
from pydantic import BaseModel


class DetectedSweetener(BaseModel):
    """Represents a single detected sweetener."""
    name: str
    sweetener_category: str
    category: Literal["with_quantity", "no_quantity"]
    quantity: Optional[str] = None
    source: Literal["ingredients", "nft", "both"]
    status: Optional[Literal["needs_review"]] = None


class SweetenerDetectionResult(BaseModel):
    """Complete sweetener detection result."""
    detected: List[DetectedSweetener]
    has_quantity_sweeteners: bool
    has_no_quantity_sweeteners: bool
