import math
from typing import List, Dict, Optional
from compliance.nft_audit_table.models import NutrientData, AuditResult, ComplianceStatus
from compliance.nft_audit_table.rounding_rules import NFT_RULES_QUANTITY, NFT_RULES_DV
from compliance.nft_audit_table.cross_check_rules import (
    check_calorie_calculation,
    check_sat_trans_combined_dv,
    check_fat_components,
    check_carb_components,
    check_dv_calculation
)

class NFTAuditor:
    """
    Audits nutrient declarations against CFIA rounding rules.
    """
    
    def audit_nutrient(self, data: NutrientData) -> AuditResult:
        """
        Audits a single nutrient value.
        """
        rules_map = NFT_RULES_DV if data.is_dv else NFT_RULES_QUANTITY
        
        # Normalize name lookup (simple case-insensitive generic match)
        # In a real app, might want a more robust alias map.
        rules = self._find_rules(data.name, rules_map)
        
        if not rules:
            return AuditResult(
                nutrient_name=data.name,
                original_value=data.value,
                unit=data.unit,
                is_dv=data.is_dv,
                status=ComplianceStatus.SKIP,
                message=f"No rounding rules found for '{data.name}'",
            )
            
        return self._apply_rules(data, rules)
    
    def _find_rules(self, name: str, rules_map: dict):
        """Finds rules for a given nutrient name, trying exact and fuzzy matches."""
        if name in rules_map:
            return rules_map[name]
        
        return None

    def _apply_rules(self, data: NutrientData, rules: List[object]) -> AuditResult:
        matched_rule = None
        
        for rule in rules:
            if rule.condition(data.value):
                matched_rule = rule
                break
        
        if not matched_rule:
            return AuditResult(
                nutrient_name=data.name,
                original_value=data.value,
                unit=data.unit,
                is_dv=data.is_dv,
                status=ComplianceStatus.SKIP,
                message="Value did not match any defined rule conditions.",
            )
            
        expected_value = matched_rule.round_func(data.value)
        
        # Floating point comparison
        is_compliant = math.isclose(data.value, expected_value, abs_tol=1e-9)
        
        status = ComplianceStatus.PASS if is_compliant else ComplianceStatus.FAIL
        message = "compliant" if is_compliant else f"Value {data.value} should be rounded to {expected_value}"
        
        return AuditResult(
            nutrient_name=data.name,
            original_value=data.value,
            unit=data.unit,
            is_dv=data.is_dv,
            status=status,
            expected_value=expected_value,
            message=message,
            rule_applied=matched_rule.description
        )

    def audit_cross_fields(self, nutrients: Dict[str, float]) -> list:
        """
        Run all cross-field validations.
        
        Args:
            nutrients: Dict mapping nutrient names to their values
                      e.g., {"Fat": 8.0, "Carbohydrate": 18.0, ...}
        
        Returns:
            List of CrossFieldResult objects
        """
        results = []
        
        # 1. Calorie calculation check
        if all(k in nutrients for k in ["Fat", "Carbohydrate", "Protein", "Calories"]):
            results.append(check_calorie_calculation(
                fat=nutrients["Fat"],
                carbs=nutrients["Carbohydrate"],
                protein=nutrients["Protein"],
                declared_cal=nutrients["Calories"]
            ))
        
        # 2. Saturated + Trans combined %DV
        if "Saturated Fat" in nutrients and "Trans Fat" in nutrients:
            sat_trans_dv = nutrients.get("Saturated + Trans %DV")
            results.append(check_sat_trans_combined_dv(
                sat_g=nutrients["Saturated Fat"],
                trans_g=nutrients["Trans Fat"],
                declared_dv=sat_trans_dv
            ))
        
        # 3. Fat component consistency
        if all(k in nutrients for k in ["Fat", "Saturated Fat", "Trans Fat"]):
            results.append(check_fat_components(
                total_fat=nutrients["Fat"],
                sat=nutrients["Saturated Fat"],
                trans=nutrients["Trans Fat"]
            ))
        
        # 4. Carb component consistency
        if all(k in nutrients for k in ["Carbohydrate", "Fibre", "Sugars"]):
            results.append(check_carb_components(
                total_carbs=nutrients["Carbohydrate"],
                fibre=nutrients["Fibre"],
                sugars=nutrients["Sugars"]
            ))
        
        # 5. %DV calculation checks for minerals
        mineral_checks = [
            ("Sodium", "mg"),
            ("Potassium", "mg"),
            ("Calcium", "mg"),
            ("Iron", "mg"),
        ]
        
        for nutrient, unit in mineral_checks:
            if nutrient in nutrients and f"{nutrient} %DV" in nutrients:
                results.append(check_dv_calculation(
                    nutrient=nutrient,
                    rounded_weight=nutrients[nutrient],
                    declared_dv=nutrients[f"{nutrient} %DV"],
                    unit=unit
                ))
        
        return results
