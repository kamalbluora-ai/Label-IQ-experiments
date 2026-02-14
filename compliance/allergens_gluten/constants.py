from typing import Dict, List, Set

# CFIA Priority Allergens (11 categories)
PRIORITY_ALLERGENS: Dict[str, List[str]] = {
    "Eggs": [
        "egg",
        "eggs",
        "egg white",
        "egg yolk",
        "egg powder",
        "dried egg",
        "liquid egg",
        "albumin",
        "ovalbumin",
        "ovomucin",
        "ovotransferrin",
        "lysozyme",
        "lecithin",  # can be egg-derived
    ],
    "Milk": [
        "milk",
        "cream",
        "butter",
        "cheese",
        "yogurt",
        "yoghurt",
        "whey",
        "casein",
        "caseinate",
        "lactose",
        "lactalbumin",
        "lactoglobulin",
        "curds",
        "ghee",
        "buttermilk",
        "dairy",
    ],
    "Mustard": [
        "mustard",
        "mustard seed",
        "mustard flour",
        "mustard oil",
    ],
    "Peanuts": [
        "peanut",
        "peanuts",
        "peanut butter",
        "peanut oil",
        "peanut flour",
        "groundnut",
        "arachis oil",
    ],
    "Crustaceans and Molluscs": [
        "crab",
        "lobster",
        "shrimp",
        "prawn",
        "crayfish",
        "langoustine",
        "krill",
        "barnacle",
        "oyster",
        "clam",
        "mussel",
        "scallop",
        "squid",
        "octopus",
        "snail",
        "abalone",
        "cockle",
        "periwinkle",
        "whelk",
        "crustacean",
        "mollusc",
        "shellfish",
    ],
    "Fish": [
        "fish",
        "salmon",
        "tuna",
        "cod",
        "haddock",
        "halibut",
        "anchovy",
        "anchovies",
        "sardine",
        "sardines",
        "mackerel",
        "herring",
        "trout",
        "bass",
        "tilapia",
        "pollock",
        "catfish",
        "fish sauce",
        "fish oil",
    ],
    "Sesame Seeds": [
        "sesame",
        "sesame seed",
        "sesame oil",
        "tahini",
        "sesamol",
        "sesamolin",
    ],
    "Soy": [
        "soy",
        "soya",
        "soybean",
        "soybeans",
        "soy protein",
        "soy lecithin",
        "tofu",
        "tempeh",
        "miso",
        "edamame",
        "soy sauce",
        "tamari",
        "textured vegetable protein",
        "tvp",
    ],
    "Sulphites": [
        "sulphite",
        "sulfite",
        "sulphites",
        "sulfites",
        "sulfur dioxide",
        "sulphur dioxide",
        "sodium sulphite",
        "sodium sulfite",
        "sodium bisulphite",
        "sodium bisulfite",
        "sodium metabisulphite",
        "sodium metabisulfite",
        "potassium bisulphite",
        "potassium bisulfite",
        "potassium metabisulphite",
        "potassium metabisulfite",
    ],
    "Tree Nuts": [
        "almond",
        "almonds",
        "brazil nut",
        "brazil nuts",
        "cashew",
        "cashews",
        "hazelnut",
        "hazelnuts",
        "macadamia",
        "macadamia nut",
        "pecan",
        "pecans",
        "pine nut",
        "pine nuts",
        "pistachio",
        "pistachios",
        "walnut",
        "walnuts",
        "chestnut",
        "chestnuts",
        "beechnut",
        "butternut",
        "hickory nut",
        "shea nut",
        "tree nut",
    ],
    "Wheat and Triticale": [
        "wheat",
        "triticale",
        "wheat flour",
        "wheat starch",
        "wheat bran",
        "wheat germ",
        "bulgur",
        "couscous",
    ],
}

# Gluten Sources (6 base grains)
GLUTEN_SOURCES: Dict[str, List[str]] = {
    "Wheat": [
        "wheat",
        "wheat flour",
        "wheat starch",
        "wheat bran",
        "wheat germ",
    ],
    "Oats": [
        "oat",
        "oats",
        "oat flour",
        "oat bran",
        "oatmeal",
    ],
    "Barley": [
        "barley",
        "barley flour",
        "barley malt",
        "malt",
        "malted barley",
    ],
    "Rye": [
        "rye",
        "rye flour",
        "rye bread",
    ],
    "Triticale": [
        "triticale",
    ],
    "Hybridized Strains": [
        "spelt",
        "kamut",
        "farro",
        "einkorn",
        "emmer",
    ],
}

# Flatten for fast lookup
ALL_ALLERGEN_KEYWORDS: Set[str] = {
    keyword.lower() for keywords in PRIORITY_ALLERGENS.values() for keyword in keywords
}

ALL_GLUTEN_KEYWORDS: Set[str] = {
    keyword.lower() for keywords in GLUTEN_SOURCES.values() for keyword in keywords
}

# Reverse lookup: keyword → category
ALLERGEN_KEYWORD_TO_CATEGORY: Dict[str, str] = {
    keyword.lower(): category
    for category, keywords in PRIORITY_ALLERGENS.items()
    for keyword in keywords
}

GLUTEN_KEYWORD_TO_CATEGORY: Dict[str, str] = {
    keyword.lower(): category
    for category, keywords in GLUTEN_SOURCES.items()
    for keyword in keywords
}
