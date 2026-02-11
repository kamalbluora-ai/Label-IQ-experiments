from typing import Dict, Optional
from compliance.nutrition_facts.models import CrossFieldResult, ComplianceStatus
from compliance.nutrition_facts.integration import DAILY_VALUES


def check_calorie_calculation(
    fat: float,
    carbs: float,
    protein: float,
    declared_cal: float
) -> CrossFieldResult:
    """
    Verify declared calories match calculated from macros.
    
    Formula: Calories = (Fat × 9) + (Carbohydrate × 4) + (Protein × 4)
    Tolerance: ±20% or ±20 Cal (whichever is greater)
    """
    calculated = (fat * 9) + (carbs * 4) + (protein * 4)
    
    # Determine tolerance
    tolerance_percent = abs(calculated * 0.20)
    tolerance_absolute = 20
    tolerance = max(tolerance_percent, tolerance_absolute)
    
    diff = abs(declared_cal - calculated)
    is_compliant = diff <= tolerance
    
    status = ComplianceStatus.PASS if is_compliant else ComplianceStatus.FAIL
    message = (
        f"Declared: {declared_cal} Cal, Calculated: {calculated:.1f} Cal, "
        f"Difference: {diff:.1f} Cal (tolerance: ±{tolerance:.1f} Cal)"
    )
    
    return CrossFieldResult(
        check_name="Calorie Calculation",
        status=status,
        message=message,
        fields_involved=["Fat", "Carbohydrate", "Protein", "Calories"],
        declared_value=declared_cal,
        expected_value=calculated,
        tolerance=f"±{tolerance:.1f} Cal"
    )


def check_sat_trans_combined_dv(
    sat_g: float,
    trans_g: float,
    declared_dv: Optional[float] = None
) -> CrossFieldResult:
    """
    Verify Saturated + Trans combined %DV is correctly calculated.
    
    Formula: %DV = round((Sat + Trans) / 20 × 100)
    """
    combined_g = sat_g + trans_g
    expected_dv = round((combined_g / DAILY_VALUES["Saturated + Trans"]) * 100)
    
    if declared_dv is None:
        status = ComplianceStatus.WARNING
        message = f"Saturated + Trans combined %DV not declared (expected: {expected_dv}%)"
    else:
        is_compliant = abs(declared_dv - expected_dv) < 0.5
        status = ComplianceStatus.PASS if is_compliant else ComplianceStatus.FAIL
        message = f"Declared: {declared_dv}%, Expected: {expected_dv}%"
    
    return CrossFieldResult(
        check_name="Saturated + Trans %DV",
        status=status,
        message=message,
        fields_involved=["Saturated Fat", "Trans Fat"],
        declared_value=declared_dv,
        expected_value=float(expected_dv)
    )


def check_fat_components(
    total_fat: float,
    sat: float,
    trans: float
) -> CrossFieldResult:
    """
    Verify fat components don't exceed total fat.
    
    Rule: Saturated + Trans ≤ Total Fat
    """
    combined = sat + trans
    is_compliant = combined <= total_fat + 0.01  # Small tolerance for rounding
    
    status = ComplianceStatus.PASS if is_compliant else ComplianceStatus.FAIL
    message = (
        f"Total Fat: {total_fat}g, Saturated: {sat}g, Trans: {trans}g, "
        f"Combined: {combined}g"
    )
    
    return CrossFieldResult(
        check_name="Fat Component Consistency",
        status=status,
        message=message,
        fields_involved=["Fat", "Saturated Fat", "Trans Fat"],
        declared_value=combined,
        expected_value=total_fat
    )


def check_carb_components(
    total_carbs: float,
    fibre: float,
    sugars: float
) -> CrossFieldResult:
    """
    Verify carb components don't exceed total carbohydrate.
    
    Rule: Fibre + Sugars ≤ Total Carbohydrate
    """
    combined = fibre + sugars
    is_compliant = combined <= total_carbs + 0.01  # Small tolerance for rounding
    
    status = ComplianceStatus.PASS if is_compliant else ComplianceStatus.FAIL
    message = (
        f"Total Carbohydrate: {total_carbs}g, Fibre: {fibre}g, Sugars: {sugars}g, "
        f"Combined: {combined}g"
    )
    
    return CrossFieldResult(
        check_name="Carbohydrate Component Consistency",
        status=status,
        message=message,
        fields_involved=["Carbohydrate", "Fibre", "Sugars"],
        declared_value=combined,
        expected_value=total_carbs
    )


def check_dv_calculation(
    nutrient: str,
    rounded_weight: float,
    declared_dv: float,
    unit: str = "mg"
) -> CrossFieldResult:
    """
    Verify %DV is calculated from rounded weight (for minerals).
    
    Rule: %DV = round((rounded_weight / daily_value) × 100)
    """
    if nutrient not in DAILY_VALUES:
        return CrossFieldResult(
            check_name=f"{nutrient} %DV Calculation",
            status=ComplianceStatus.SKIP,
            message=f"No daily value defined for {nutrient}",
            fields_involved=[nutrient]
        )
    
    daily_value = DAILY_VALUES[nutrient]
    expected_dv = round((rounded_weight / daily_value) * 100)
    
    is_compliant = abs(declared_dv - expected_dv) < 0.5
    status = ComplianceStatus.PASS if is_compliant else ComplianceStatus.FAIL
    message = (
        f"{nutrient}: {rounded_weight}{unit} → Declared %DV: {declared_dv}%, "
        f"Expected: {expected_dv}%"
    )
    
    return CrossFieldResult(
        check_name=f"{nutrient} %DV Calculation",
        status=status,
        message=message,
        fields_involved=[nutrient],
        declared_value=declared_dv,
        expected_value=float(expected_dv)
    )
