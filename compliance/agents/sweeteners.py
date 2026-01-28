from typing import Dict, Any
from compliance.base_agent import BaseComplianceAgent

class SweetenersAgent(BaseComplianceAgent):
    def __init__(self):
        super().__init__(section_name="Sweeteners")
    
    def get_section_context(self) -> str:
        """Get section-specific context."""
        return "Verify sweetener declarations: phenylalanine statement for aspartame, and sweetness equivalence for table-top sweeteners."
    
    def prepare_input_data(self, label_facts: Dict[str, Any]) -> Dict[str, Any]:
        fields = label_facts.get("fields", {})

        def get_text(key):
            val = fields.get(key, {}).get("text", "")
            return [val] if val else []

        return {
            "ingredients_list_en": get_text("ingredients_list_en"),
            "phenylalanine_statement": get_text("phenylalanine_statement"),
        }
