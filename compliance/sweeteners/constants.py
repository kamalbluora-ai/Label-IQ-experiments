from typing import Dict, List, Set

# Sweeteners requiring quantity declaration
SWEETENERS_WITH_QUANTITY: Dict[str, List[str]] = {
    "Polyol": [
        "polydextrose", "erythritol", "isomalt", "lactitol",
        "maltitol", "maltitol syrup", "mannitol", "sorbitol",
        "sorbitol syrup", "xylitol", "hydrogenated starch hydrolysates",
    ],
}

# Sweeteners without quantity requirement
SWEETENERS_NO_QUANTITY: Dict[str, List[str]] = {
    "Non-Nutritive": [
        "acesulfame potassium", "advantame", "aspartame",
        "neotame", "sucralose", "thaumatin",
    ],
    "Saccharin": [
        "saccharin", "calcium saccharin",
        "potassium saccharin", "sodium saccharin",
    ],
    "Steviol Glycoside": [
        "steviol glycosides", "stevia extract", "stevia leaf extract",
        "rebaudioside a", "rebaudioside m", "rebaudioside b",
        "rebaudioside c", "rebaudioside d", "rebaudioside f",
        "rebiana", "dulcoside a", "rubusoside",
        "steviolbioside", "stevioside",
    ],
    "Monk Fruit": ["monk fruit extract"],
}

# Helper: Build reverse lookup (sweetener → category)
def _build_lookup(d: Dict[str, List[str]]) -> Dict[str, str]:
    return {name: cat for cat, names in d.items() for name in names}

SWEETENER_TO_CATEGORY_WITH_QTY = _build_lookup(SWEETENERS_WITH_QUANTITY)
SWEETENER_TO_CATEGORY_NO_QTY = _build_lookup(SWEETENERS_NO_QUANTITY)

# Sets for quick lookup
ALL_WITH_QUANTITY: Set[str] = set(SWEETENER_TO_CATEGORY_WITH_QTY.keys())
ALL_NO_QUANTITY: Set[str] = set(SWEETENER_TO_CATEGORY_NO_QTY.keys())
ALL_SWEETENERS: Set[str] = ALL_WITH_QUANTITY | ALL_NO_QUANTITY
