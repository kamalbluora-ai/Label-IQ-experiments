from typing import List, Dict, Any, Tuple
from compliance.nutrition_facts.models import NutrientData
import re

DAILY_VALUES = {
    "Fat": 75,                  # g
    "Saturated + Trans": 20,    # g
    "Cholesterol": 300,         # mg
    "Sodium": 2300,             # mg
    "Carbohydrate": 300,        # g
    "Fibre": 28,                # g
    "Sugars": 100,              # g
    "Protein": 50,              # g
    "Potassium": 4700,          # mg
    "Calcium": 1300,            # mg
    "Iron": 18,                 # mg
}

# Mapping: DocAI Key -> (Auditor Name, Unit, is_dv)
# Tuple format: (Nutrient Name, Unit, is_percentage)
FIELD_MAPPING: Dict[str, Tuple[str, str, bool]] = {
    # Quantity Fields
    "nft_serving_size_en": ("Serving Size", "g/mL", False),
    "nft_serving_size_fr": ("Serving Size", "g/mL", False),
    
    "nft_calories_en": ("Calories", "Cal", False),
    "nft_calories_fr": ("Calories", "Cal", False),
    
    "nft_fat_en": ("Fat", "g", False),
    "nft_fat_fr": ("Fat", "g", False),
    
    "nft_saturated_fat_en": ("Saturated Fat", "g", False),
    "nft_saturated_fat_fr": ("Saturated Fat", "g", False),
    
    "nft_trans_fat_en": ("Trans Fat", "g", False),
    "nft_trans_fat_fr": ("Trans Fat", "g", False),
    
    "nft_cholesterol_en": ("Cholesterol", "mg", False),
    "nft_cholesterol_fr": ("Cholesterol", "mg", False),
    
    "nft_sodium_en": ("Sodium", "mg", False),
    "nft_sodium_fr": ("Sodium", "mg", False),
    
    "nft_carbohydrate_en": ("Carbohydrate", "g", False),
    "nft_carbohydrate_fr": ("Carbohydrate", "g", False),
    
    "nft_fibre_en": ("Fibre", "g", False),
    "nft_fibre_fr": ("Fibre", "g", False),
    
    "nft_sugar_en": ("Sugars", "g", False),
    "nft_sugar_fr": ("Sugars", "g", False),
    
    "nft_protein_en": ("Protein", "g", False),
    "nft_protein_fr": ("Protein", "g", False),
    
    "nft_potassium_en": ("Potassium", "mg", False),
    "nft_potassium_fr": ("Potassium", "mg", False),
    
    "nft_calcium_en": ("Calcium", "mg", False),
    "nft_calcium_fr": ("Calcium", "mg", False),
    
    "nft_iron_en": ("Iron", "mg", False),
    "nft_iron_fr": ("Iron", "mg", False),
    
    # %DV Fields
    "nft_fat_dv_en": ("Fat", "%", True),
    "nft_fat_dv_fr": ("Fat", "%", True),
    
    "nft_cholesterol_dv_en": ("Cholesterol", "%", True),
    "nft_cholesterol_dv_fr": ("Cholesterol", "%", True),
    
    "nft_sodium_dv_en": ("Sodium", "%", True),
    "nft_sodium_dv_fr": ("Sodium", "%", True),
    
    "nft_carbohydrate_dv_en": ("Carbohydrate", "%", True),
    "nft_carbohydrate_dv_fr": ("Carbohydrate", "%", True),
    
    "nft_fibre_dv_en": ("Fibre", "%", True),
    "nft_fibre_dv_fr": ("Fibre", "%", True),
    
    "nft_sugars_dv_en": ("Sugars", "%", True),
    "nft_sugars_dv_fr": ("Sugars", "%", True),
    
    "nft_potassium_dv_en": ("Potassium", "%", True),
    "nft_potassium_dv_fr": ("Potassium", "%", True),
    
    "nft_calcium_dv_en": ("Calcium", "%", True),
    "nft_calcium_dv_fr": ("Calcium", "%", True),
    
    "nft_iron_dv_en": ("Iron", "%", True),
    "nft_iron_dv_fr": ("Iron", "%", True),
}

def map_docai_to_inputs(docai_data: Dict[str, Any]) -> List[NutrientData]:
    """
    Converts raw DocAI output into a list of NutrientData objects.
    
    Args:
        docai_data: Dictionary containing key-value pairs from Document AI.
                   Values are expected to be strings or numbers.
                   
    Returns:
        List of NutrientData objects ready for auditing.
    """
    inputs = []

    for doc_key, (name, default_unit, is_dv) in FIELD_MAPPING.items():
        # Check if the field exists in the input JSON
        raw_value = docai_data.get(doc_key)
        
        # Skip if missing, None, or empty string/placeholder
        if raw_value is not None and str(raw_value).strip() not in ["", "--"]:
            cleaned_str = str(raw_value).strip()
            
            # 1. Extract Number using Regex
            # Matches integers or decimals (e.g. "31", "5.2", "0.5")
            match = re.search(r"(\d+(?:\.\d+)?)", cleaned_str)
            
            if match:
                try:
                    value = float(match.group(1))
                    unit = default_unit
                    
                    # 2. Dynamic Unit Detection (specifically for Serving Size g/mL)
                    if default_unit == "g/mL":
                        if "mL" in cleaned_str: # Case sensitive check for mL
                            unit = "mL"
                        elif "g" in cleaned_str.lower():
                            unit = "g"
                    
                    inputs.append(NutrientData(
                        name=name,
                        value=value,
                        unit=unit,
                        is_dv=is_dv
                    ))
                except ValueError:
                    pass
            else:
                # No number found in string (e.g. "Per container")
                pass
                
    return inputs
