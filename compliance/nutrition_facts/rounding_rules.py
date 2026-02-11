from dataclasses import dataclass
from typing import Callable, List, Dict, Optional
import math

@dataclass
class RoundingRule:
    """Defines a single rounding condition and its logic."""
    condition: Callable[[float], bool]
    round_func: Callable[[float], float]
    description: str

def round_to_multiple(value: float, multiple: float) -> float:
    """Rounds value to the nearest multiple."""
    if multiple == 0: return 0
    return round(value / multiple) * multiple

def zero_rule():
    return lambda v: 0.0

def multiple_rule(multiple: float):
    return lambda v: round_to_multiple(v, multiple)

# --- Rule Definitions ---

# 1. Serving Size (Metric)
# "Metric unit is less than 10 g or 10 mL" -> Round to nearest 0.1
# "Metric unit is 10 g or 10 mL or more" -> Round to nearest 1
SERVING_SIZE_RULES = [
    RoundingRule(lambda v: v < 10, multiple_rule(0.1), "Round to nearest 0.1 (if < 10)"),
    RoundingRule(lambda v: v >= 10, multiple_rule(1), "Round to nearest 1 (if >= 10)"),
]

# 2. Energy value (Calories)
CALORIES_RULES = [
    RoundingRule(lambda v: v < 5, zero_rule(), "Round to 0 (if < 5)"),
    RoundingRule(lambda v: 5 <= v <= 50, multiple_rule(5), "Round to nearest 5 (5-50 Cal)"),
    RoundingRule(lambda v: v > 50, multiple_rule(10), "Round to nearest 10 (> 50 Cal)"),
]

# 3. Fat, Saturated, Trans
# < 0.5 -> 0
# 0.5 - 5 -> nearest 0.5
# > 5 -> nearest 1
FAT_RULES = [
    RoundingRule(lambda v: v < 0.5, zero_rule(), "Round to 0 (if < 0.5)"),
    RoundingRule(lambda v: 0.5 <= v <= 5, multiple_rule(0.5), "Round to nearest 0.5 (0.5-5 g)"),
    RoundingRule(lambda v: v > 5, multiple_rule(1), "Round to nearest 1 (> 5 g)"),
]

FAT_DV_RULES = [
    RoundingRule(lambda v: v == 0, zero_rule(), "Round to 0% (if 0%)"),
    RoundingRule(lambda v: v != 0, multiple_rule(1), "Round to nearest 1% (if > 0%)"),
]

# 4. Cholesterol
# < 2 mg (approx free) -> 0. But JSON says 'Meets free of cholesterol conditions'.
# JSON: "Meets 'free of cholesterol' conditions (typically < 2 mg)" -> 0
# JSON: "All other cases" -> nearest 5 mg
CHOLESTEROL_RULES = [
    RoundingRule(lambda v: v < 2, zero_rule(), "Round to 0 mg (< 2 mg)"),
    RoundingRule(lambda v: v >= 2, multiple_rule(5), "Round to nearest 5 mg (>= 2 mg)"),
]

# 5. Sodium
# < 5 mg -> 0
# 5 - 140 mg -> nearest 5
# > 140 mg -> nearest 10
SODIUM_RULES = [
    RoundingRule(lambda v: v < 5, zero_rule(), "Round to 0 mg (< 5 mg)"),
    RoundingRule(lambda v: 5 <= v <= 140, multiple_rule(5), "Round to nearest 5 mg (5-140 mg)"),
    RoundingRule(lambda v: v > 140, multiple_rule(10), "Round to nearest 10 mg (> 140 mg)"),
]

# 6. Carbohydrate, Fibre, Sugars
# < 0.5 -> 0
# >= 0.5 -> nearest 1
CARB_RULES = [
    RoundingRule(lambda v: v < 0.5, zero_rule(), "Round to 0 g (< 0.5)"),
    RoundingRule(lambda v: v >= 0.5, multiple_rule(1), "Round to nearest 1 g (>= 0.5)"),
]

# 7. Protein
# < 0.5 -> nearest 0.1 (Wait, JSON says 'Round to the nearest multiple of 0.1 g' for < 0.5)
# >= 0.5 -> nearest 1
PROTEIN_RULES = [
    RoundingRule(lambda v: v < 0.5, multiple_rule(0.1), "Round to nearest 0.1 g (< 0.5)"),
    RoundingRule(lambda v: v >= 0.5, multiple_rule(1), "Round to nearest 1 g (>= 0.5)"),
]

# 8. Potassium, Calcium (MGM) -> Vitamins/Minerals logic usually similar
# Potassium: < 5 -> 0; 5-50 -> 10; 50-250 -> 25; >= 250 -> 50
POTASSIUM_CALCIUM_RULES = [
    RoundingRule(lambda v: v < 5, zero_rule(), "Round to 0 mg (< 5)"),
    RoundingRule(lambda v: 5 <= v < 50, multiple_rule(10), "Round to nearest 10 mg (5-50)"),
    RoundingRule(lambda v: 50 <= v < 250, multiple_rule(25), "Round to nearest 25 mg (50-250)"),
    RoundingRule(lambda v: v >= 250, multiple_rule(50), "Round to nearest 50 mg (>= 250)"),
]

# 9. Iron
# < 0.05 -> 0
# 0.05 - 0.5 -> 0.1
# 0.5 - 2.5 -> 0.25
# >= 2.5 -> 0.5
IRON_RULES = [
    RoundingRule(lambda v: v < 0.05, zero_rule(), "Round to 0 mg (< 0.05)"),
    RoundingRule(lambda v: 0.05 <= v < 0.5, multiple_rule(0.1), "Round to nearest 0.1 mg (0.05-0.5)"),
    RoundingRule(lambda v: 0.5 <= v < 2.5, multiple_rule(0.25), "Round to nearest 0.25 mg (0.5-2.5)"),
    RoundingRule(lambda v: v >= 2.5, multiple_rule(0.5), "Round to nearest 0.5 mg (>= 2.5)"),
]

# Generic DV Rules (mostly nearest 1%)
STANDARD_DV_RULES = [
    RoundingRule(lambda v: True, multiple_rule(1), "Round to nearest 1%"),
]

# --- Mapping ---

NFT_RULES_QUANTITY: Dict[str, List[RoundingRule]] = {
    "Serving Size": SERVING_SIZE_RULES,
    "Calories": CALORIES_RULES,
    "Fat": FAT_RULES,
    "Saturated Fat": FAT_RULES,
    "Saturated fatty acids": FAT_RULES,
    "Trans Fat": FAT_RULES,
    "Trans fatty acids": FAT_RULES,
    "Cholesterol": CHOLESTEROL_RULES,
    "Sodium": SODIUM_RULES,
    "Carbohydrate": CARB_RULES,
    "Fibre": CARB_RULES,
    "Sugars": CARB_RULES,
    "Protein": PROTEIN_RULES,
    "Potassium": POTASSIUM_CALCIUM_RULES,
    "Calcium": POTASSIUM_CALCIUM_RULES,
    "Iron": IRON_RULES
}

NFT_RULES_DV: Dict[str, List[RoundingRule]] = {
    "Fat": FAT_DV_RULES,
    "Saturated": FAT_DV_RULES,
    "Trans": FAT_DV_RULES,
    "Cholesterol": STANDARD_DV_RULES,
    "Sodium": STANDARD_DV_RULES,
    "Carbohydrate": STANDARD_DV_RULES,
    "Fibre": STANDARD_DV_RULES,
    "Sugars": STANDARD_DV_RULES,
    "Potassium": STANDARD_DV_RULES,
    "Calcium": STANDARD_DV_RULES,
    "Iron": STANDARD_DV_RULES
}
