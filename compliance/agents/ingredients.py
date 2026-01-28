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
        fields = label_facts.get("fields", {})
        
        def get_text(key):
            val = fields.get(key, {}).get("text", "")
            return [val] if val else []
        
        return {
            "common_name_en": get_text("common_name_en"),
            "common_name_fr": get_text("common_name_fr"),
            "ingredients_list_en": get_text("ingredients_list_en"),
            "ingredients_list_fr": get_text("ingredients_list_fr"),
            "allergen_statement_en": get_text("allergen_statement_en"),
            "allergen_statement_fr": get_text("allergen_statement_fr"),
        }
