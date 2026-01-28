from typing import Dict, Any
from compliance.base_agent import BaseComplianceAgent


class NameAddressAgent(BaseComplianceAgent):
    
    def __init__(self):
        super().__init__(section_name="Name and Principal Place of Business")
    
    def get_section_context(self) -> str:
        """Get section-specific context."""
        return "Confirm dealer name and principal place of business: presence, proper identification (imported by/for), and placement on label."
    
    def prepare_input_data(self, label_facts: Dict[str, Any]) -> Dict[str, Any]:
        fields = label_facts.get("fields", {})
        
        def get_text(key):
            val = fields.get(key, {}).get("text", "")
            return [val] if val else []

        return {
            "dealer_name": get_text("dealer_name"),
            "dealer_address": get_text("dealer_address"),
        }
