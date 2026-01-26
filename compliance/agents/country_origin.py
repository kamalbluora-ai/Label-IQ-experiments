from typing import Dict, Any
from compliance.base_agent import BaseComplianceAgent

class CountryOriginAgent(BaseComplianceAgent):
    def __init__(self):
        super().__init__(section_name="Country of Origin")
    
    def get_section_context(self) -> str:
        """Get section-specific context."""
        return "Evaluate country of origin requirements for applicable products (wine, dairy, honey, fish, fruits, vegetables, eggs, meat, maple, processed)."
    
    def prepare_input_data(self, label_facts: Dict[str, Any]) -> Dict[str, Any]:
        fields_all = label_facts.get("fields_all", {})
        return {
            "country_of_origin": [c.get("text", "") for c in fields_all.get("country_of_origin", [])],
            "dealer_name": [c.get("text", "") for c in fields_all.get("dealer_name", [])],
            "dealer_address": [c.get("text", "") for c in fields_all.get("dealer_address", [])],
        }
