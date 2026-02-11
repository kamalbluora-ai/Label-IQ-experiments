from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime


class ClaimTagResult(BaseModel):
    """Result for a single claim tag evaluation."""
    claim_type: str = Field(..., description="Type of claim (e.g., 'Nature / Natural', 'Kosher')")
    claim_text_found: Optional[str] = Field(None, description="Exact claim text found on label")
    certification_body: Optional[str] = Field(None, description="Certification body name if present")
    status: str = Field(default="NEEDS_REVIEW", description="Always 'NEEDS_REVIEW'")
    ai_reason: str = Field(..., description="AI-generated justification for the evaluation")
    rule_violations: List[str] = Field(default_factory=list, description="List of specific rule violations detected")
    supporting_evidence: List[str] = Field(default_factory=list, description="Evidence from ingredients/NFT supporting the evaluation")


class ClaimTagEvaluation(BaseModel):
    """Complete evaluation output for all claim tags."""
    product_id: Optional[str] = Field(None, description="Product identifier if available")
    evaluation_timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat(), description="ISO8601 timestamp")
    claims_detected: List[ClaimTagResult] = Field(default_factory=list, description="List of claim evaluations")
    summary: str = Field(..., description="Overall summary of claim tag evaluation")
