from typing import Dict, Any
from compliance.base_agent import BaseComplianceAgent


class NameAddressAgent(BaseComplianceAgent):
    
    def __init__(self):
        super().__init__(section_name="Name and Principal Place of Business")
    
    def get_section_context(self) -> str:
        """Get section-specific context."""
        return "Confirm dealer name and principal place of business: presence, proper identification (imported by/for), and placement on label."
    
    def prepare_input_data(self, label_facts: Dict[str, Any]) -> Dict[str, Any]:
        fields_all = label_facts.get("fields_all", {})
        
        return {
            "dealer_name": [c.get("text", "") for c in fields_all.get("dealer_name", [])],
            "dealer_address": [c.get("text", "") for c in fields_all.get("dealer_address", [])],
        }
