from typing import Dict, Any
from compliance.base_agent import BaseComplianceAgent


class IngredientsAgent(BaseComplianceAgent):
    """
    Agent for Ingredients and Allergen Labelling compliance.
    """
    
    def __init__(self):
        super().__init__(section_name="List of Ingredients and Allergen Labelling")
    
    def get_section_context(self) -> str:
        """Get section-specific context."""
        return "Check ingredient list: descending order by weight, allergen declarations, component labeling, and sugars grouping."
    
    def prepare_input_data(self, label_facts: Dict[str, Any]) -> Dict[str, Any]:
        """Extract ingredients and allergen fields from DocAI output."""
        fields_all = label_facts.get("fields_all", {})
        
        return {
            "common_name_en": [c.get("text", "") for c in fields_all.get("common_name_en", [])],
            "common_name_fr": [c.get("text", "") for c in fields_all.get("common_name_fr", [])],
            "ingredients_list_en": [c.get("text", "") for c in fields_all.get("ingredients_list_en", [])],
            "ingredients_list_fr": [c.get("text", "") for c in fields_all.get("ingredients_list_fr", [])],
            "allergen_statement_en": [c.get("text", "") for c in fields_all.get("allergen_statement_en", [])],
            "allergen_statement_fr": [c.get("text", "") for c in fields_all.get("allergen_statement_fr", [])],
        }
