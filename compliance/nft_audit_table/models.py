from typing import Optional
from enum import Enum
from pydantic import BaseModel, Field, field_validator

class ComplianceStatus(str, Enum):
    PASS = "pass"
    FAIL = "fail"
    WARNING = "warning"
    SKIP = "skip"

class NutrientData(BaseModel):
    """Input data for a single nutrient to be audited."""
    name: str = Field(..., description="Nutrient name (e.g. 'Fat', 'Sodium')")
    value: float = Field(..., description="The declared value")
    unit: str = Field(..., description="Unit of measurement (e.g. 'g', 'mg', 'Cal')")
    is_dv: bool = Field(False, description="True if this is a % Daily Value percentage")
    
    @field_validator('value')
    def check_non_negative(cls, v):
        if v < 0:
            raise ValueError('Nutrient value must be non-negative')
        return v

class AuditResult(BaseModel):
    """Result of auditing a single nutrient."""
    nutrient_name: str
    original_value: float
    unit: str
    is_dv: bool
    status: ComplianceStatus
    expected_value: Optional[float] = None
    message: str
    rule_applied: Optional[str] = None

class CrossFieldResult(BaseModel):
    """Result of a cross-field validation."""
    check_name: str
    status: ComplianceStatus
    message: str
    fields_involved: list[str]
    declared_value: Optional[float] = None
    expected_value: Optional[float] = None
    tolerance: Optional[str] = None
