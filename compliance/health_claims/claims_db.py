"""
Known Canadian health and nutrient claim patterns.
Organized by category for substring matching against DocAI-extracted text.
Reference: canadian_health_nutrient_claims_extraction.md
"""
from typing import Dict, List, Set


# ─── DISEASE RISK REDUCTION CLAIMS ───

DISEASE_RISK_REDUCTION_CLAIMS: Dict[str, List[str]] = {
    "Sodium/Potassium - Blood Pressure": [
        "high in potassium and low in sodium may reduce the risk of high blood pressure",
        "reduce the risk of high blood pressure a risk factor for stroke and heart disease",
    ],
    "Calcium/Vitamin D - Osteoporosis": [
        "adequate calcium and vitamin d",
        "may reduce the risk of osteoporosis",
        "help to achieve strong bones",
    ],
    "Saturated/Trans Fats - Heart Disease": [
        "low in saturated and trans fats may reduce the risk of heart disease",
        "free of saturated and trans fats",
    ],
    "Cancer Risk Reduction": [
        "rich in a variety of vegetables and fruit may help reduce the risk of some types of cancer",
    ],
    "Heart Disease - Vegetables/Fruit": [
        "rich in a variety of vegetables and fruit may help reduce the risk of heart disease",
    ],
    "Dental Caries": [
        "wont cause cavities",
        "does not promote tooth decay",
        "does not promote dental caries",
        "non cariogenic",
    ],
}


# ─── NUTRIENT FUNCTION CLAIMS ───

NUTRIENT_FUNCTION_CLAIMS: Dict[str, List[str]] = {
    "Protein": [
        "helps build and repair body tissues",
        "helps build antibodies",
        "helps build strong muscles",
    ],
    "Fat": [
        "supplies energy",
        "aids in the absorption of fat soluble vitamins",
    ],
    "DHA": [
        "dha an omega 3 fatty acid supports the normal physical development of the brain eyes and nerves",
    ],
    "ARA": [
        "ara an omega 6 fatty acid supports the normal physical development of the brain eyes and nerves",
    ],
    "Carbohydrate": [
        "assists in the utilization of fats",
    ],
    "Vitamin A": [
        "aids normal bone and tooth development",
        "aids in the development and maintenance of night vision",
        "aids in maintaining the health of the skin and membranes",
        "contributes to the maintenance of normal vision",
        "supports night vision",
        "supports healthy skin",
    ],
    "Vitamin D": [
        "factor in the formation and maintenance of bones and teeth",
        "enhances calcium and phosphorus absorption and utilization",
        "builds and maintains strong bones and teeth",
        "improves calcium absorption",
        "improves calcium and phosphorus absorption",
    ],
    "Vitamin E": [
        "a dietary antioxidant that protects the fat in body tissues from oxidation",
    ],
    "Vitamin C": [
        "a factor in the development and maintenance of bones cartilage teeth and gums",
        "a dietary antioxidant that significantly decreases the adverse effects of free radicals",
        "a dietary antioxidant that helps to reduce free radicals and lipid oxidation",
        "helps build teeth bones cartilage and gums",
        "protects against the damage of free radicals",
        "protects against the oxidative effects of free radicals",
        "protects against free radicals",
    ],
    "Thiamine (B1)": [
        "releases energy from carbohydrate",
        "aids normal growth",
    ],
    "Riboflavin (B2)": [
        "factor in energy metabolism and tissue formation",
    ],
    "Niacin": [
        "aids in normal growth and development",
    ],
    "Vitamin B6": [
        "factor in energy metabolism and tissue formation",
    ],
    "Folate": [
        "aids in red blood cell formation",
        "a factor in normal early fetal development",
        "a factor in the normal early development of the fetal brain and spinal cord",
        "contributes to normal amino acid synthesis",
    ],
    "Vitamin B12": [
        "factor in energy metabolism",
    ],
    "Biotin": [
        "factor in energy metabolism",
    ],
    "Vitamin K": [
        "contributes to the maintenance of bones",
    ],
    "Pantothenic Acid": [
        "factor in energy metabolism and tissue formation",
    ],
    "Calcium": [
        "aids in the formation and maintenance of bones and teeth",
    ],
    "Phosphorus": [
        "factor in the formation and maintenance of bones and teeth",
    ],
    "Magnesium": [
        "contributes to normal muscle function",
        "factor in energy metabolism tissue formation and bone development",
    ],
    "Iron": [
        "factor in red blood cell formation",
        "helps build red blood cells",
    ],
    "Zinc": [
        "contributes to the maintenance of normal skin",
        "contributes to the normal function of the immune system",
    ],
    "Iodine": [
        "factor in the normal function of the thyroid gland",
    ],
    "Selenium": [
        "a dietary antioxidant involved in the formation of a protein that defends against oxidative stress",
        "helps protect against oxidative stress",
    ],
    "Chromium": [
        "contributes to normal glucose metabolism",
    ],
    "Copper": [
        "contributes to the maintenance of normal connective tissue",
    ],
    "Manganese": [
        "contributes to the formation and maintenance of bones",
    ],
}


# ─── PROBIOTIC CLAIMS ───

PROBIOTIC_CLAIMS: Dict[str, List[str]] = {
    "Probiotic": [
        "probiotic that naturally forms part of the gut flora",
        "provides live microorganisms that contribute to healthy gut flora",
        "probiotic that contributes to healthy gut flora",
        "with beneficial probiotic cultures",
    ],
}


# ─── NUTRIENT CONTENT CLAIMS ───

NUTRIENT_CONTENT_CLAIMS: Dict[str, List[str]] = {
    "Energy": [
        "free of energy", "calorie free",
        "low in energy", "low calorie",
        "reduced in energy", "reduced calorie",
        "lower in energy",
        "source of energy",
        "more energy",
    ],
    "Protein": [
        "source of protein",
        "good source of protein",
        "excellent source of protein",
        "more protein",
        "higher in protein",
    ],
    "Fat/Fatty Acids/Cholesterol": [
        "fat free",
        "low in fat",
        "reduced in fat",
        "lower in fat",
        "100 fat free",
        "free of saturated fatty acids",
        "low in saturated fatty acids",
        "reduced in saturated fatty acids",
        "lower in saturated fatty acids",
        "free of trans fatty acids",
        "reduced in trans fatty acids",
        "lower in trans fatty acids",
        "source of omega 3 polyunsaturated fatty acids",
        "source of omega 6 polyunsaturated fatty acids",
        "source of omega 3",
        "source of omega 6",
        "free of cholesterol", "cholesterol free",
        "low in cholesterol",
        "reduced in cholesterol",
        "lower in cholesterol",
    ],
    "Sodium/Salt": [
        "free of sodium", "sodium free",
        "free of salt", "salt free",
        "low in sodium", "low sodium",
        "low in salt",
        "reduced in sodium", "reduced in salt",
        "lower in sodium", "lower in salt",
        "no added sodium", "no added salt",
        "lightly salted",
    ],
    "Sugars": [
        "free of sugars", "sugar free",
        "reduced in sugars",
        "lower in sugars",
        "no added sugars", "no added sugar",
    ],
    "Fibre": [
        "source of fibre", "source of fiber",
        "high source of fibre", "high source of fiber",
        "very high source of fibre", "very high source of fiber",
        "more fibre", "more fiber",
        "higher in fibre", "higher in fiber",
    ],
    "Light": [
        "light in energy",
        "light in fat",
    ],
    "Lean": [
        "extra lean",
        "lean",
    ],
}


# ─── HELPERS: Build reverse lookup structures ───

def _build_claim_lookup(d: Dict[str, List[str]]) -> Dict[str, str]:
    """Build reverse lookup: claim_phrase -> category."""
    return {phrase: cat for cat, phrases in d.items() for phrase in phrases}


DISEASE_RISK_PHRASE_TO_CATEGORY = _build_claim_lookup(DISEASE_RISK_REDUCTION_CLAIMS)
NUTRIENT_FUNCTION_PHRASE_TO_CATEGORY = _build_claim_lookup(NUTRIENT_FUNCTION_CLAIMS)
PROBIOTIC_PHRASE_TO_CATEGORY = _build_claim_lookup(PROBIOTIC_CLAIMS)
NUTRIENT_CONTENT_PHRASE_TO_CATEGORY = _build_claim_lookup(NUTRIENT_CONTENT_CLAIMS)

ALL_DISEASE_RISK_PHRASES: Set[str] = set(DISEASE_RISK_PHRASE_TO_CATEGORY.keys())
ALL_NUTRIENT_FUNCTION_PHRASES: Set[str] = set(NUTRIENT_FUNCTION_PHRASE_TO_CATEGORY.keys())
ALL_PROBIOTIC_PHRASES: Set[str] = set(PROBIOTIC_PHRASE_TO_CATEGORY.keys())
ALL_NUTRIENT_CONTENT_PHRASES: Set[str] = set(NUTRIENT_CONTENT_PHRASE_TO_CATEGORY.keys())
