"""
Ingredients and Allergen Labelling Compliance Agent

Evaluates ingredients and allergen compliance against CFIA requirements.
"""

from pathlib import Path
from typing import Dict, Any
from compliance.base_agent import BaseComplianceAgent


class IngredientsAgent(BaseComplianceAgent):
    """
    Agent for Ingredients and Allergen Labelling compliance.
    """
    
    def __init__(self):
        super().__init__(section_name="List of Ingredients and Allergen Labelling")
    
    def load_system_prompt(self) -> str:
        """Load system prompt from file."""
        prompt_path = Path(__file__).parent.parent / "prompts" / "ingredients.txt"
        with open(prompt_path, "r", encoding="utf-8") as f:
            return f.read()
    
    def prepare_input_data(self, label_facts: Dict[str, Any]) -> Dict[str, Any]:
        """Extract ingredients and allergen fields from DocAI output."""
        fields_all = label_facts.get("fields_all", {})
        
        return {
            "ingredients_list_en": [c.get("text", "") for c in fields_all.get("ingredients_list_en", [])],
            "ingredients_list_fr": [c.get("text", "") for c in fields_all.get("ingredients_list_fr", [])],
            "allergen_statement_en": [c.get("text", "") for c in fields_all.get("allergen_statement_en", [])],
            "allergen_statement_fr": [c.get("text", "") for c in fields_all.get("allergen_statement_fr", [])],
        }
