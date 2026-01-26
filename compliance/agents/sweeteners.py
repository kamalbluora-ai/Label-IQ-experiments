from typing import Dict, Any
from compliance.base_agent import BaseComplianceAgent

class SweetenersAgent(BaseComplianceAgent):
    def __init__(self):
        super().__init__(section_name="Sweeteners")
    
    def get_section_context(self) -> str:
        """Get section-specific context."""
        return "Verify sweetener declarations: phenylalanine statement for aspartame, and sweetness equivalence for table-top sweeteners."
    
    def prepare_input_data(self, label_facts: Dict[str, Any]) -> Dict[str, Any]:
        fields_all = label_facts.get("fields_all", {})
        return {
            "ingredients_list_en": [c.get("text", "") for c in fields_all.get("ingredients_list_en", [])],
            "phenylalanine_statement": [c.get("text", "") for c in fields_all.get("phenylalanine_statement", [])],
        }
