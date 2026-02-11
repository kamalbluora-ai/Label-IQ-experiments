from typing import Dict, List, Set

SUPPLEMENTS: Dict[str, List[str]] = {
    "Amino Acid": [
        "l-arginine",
        "l-citrulline",
        "l-glutamine",
        "l-leucine",
        "l-isoleucine",
        "l-valine",
        "taurine",
    ],
    "Bioactive": [
        "caffeine",
        "green tea extract",
        "inositol",
        "panax ginseng extract",
        "coenzyme q10",
        "glucosamine",
        "chondroitin sulfate",
    ],
    "Vitamin": [
        "vitamin a",
        "vitamin b1",
        "thiamine",
        "vitamin b2",
        "riboflavin",
        "vitamin b3",
        "niacin",
        "vitamin b5",
        "pantothenic acid",
        "vitamin b6",
        "vitamin b7",
        "biotin",
        "vitamin b9",
        "folate",
        "vitamin b12",
        "vitamin c",
        "vitamin d",
        "vitamin e",
    ],
    "Mineral": [
        "calcium",
        "iron",
        "magnesium",
        "potassium",
        "zinc",
        "selenium",
        "copper",
        "manganese",
        "chromium",
        "molybdenum",
    ],
    "Other": [
        "choline",
        "lutein",
        "lycopene",
    ],
}

# Reverse lookup: supplement → category
SUPPLEMENT_TO_CATEGORY: Dict[str, str] = {
    name: cat for cat, names in SUPPLEMENTS.items() for name in names
}

ALL_SUPPLEMENTS: Set[str] = set(SUPPLEMENT_TO_CATEGORY.keys())
