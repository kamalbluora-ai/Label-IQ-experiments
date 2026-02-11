from typing import Dict, Any
from compliance.base_agent import BaseComplianceAgent

class CountryOriginAgent(BaseComplianceAgent):
    def __init__(self):
        super().__init__(section_name="Country of Origin")
    
    def get_section_context(self) -> str:
        """Get section-specific context."""
        return "Evaluate country of origin requirements for applicable products (wine, dairy, honey, fish, fruits, vegetables, eggs, meat, maple, processed)."
    
    def prepare_input_data(self, label_facts: Dict[str, Any]) -> Dict[str, Any]:
        fields = label_facts.get("fields", {})

        def get_text(key):
            val = fields.get(key, {}).get("text", "")
            return [val] if val else []

        return {
            "country_of_origin": get_text("country_of_origin"),
            "dealer_name": get_text("dealer_name"),
            "dealer_address": get_text("dealer_address"),
        }
