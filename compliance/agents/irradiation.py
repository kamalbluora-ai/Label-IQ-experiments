from typing import Dict, Any
from compliance.base_agent import BaseComplianceAgent

class IrradiationAgent(BaseComplianceAgent):
    def __init__(self):
        super().__init__(section_name="Irradiation")
    
    def get_section_context(self) -> str:
        """Get section-specific context."""
        return "Check irradiation labeling if applicable: statement presence, international symbol on PDP, and ingredient declarations."
    
    def prepare_input_data(self, label_facts: Dict[str, Any]) -> Dict[str, Any]:
        fields = label_facts.get("fields", {})
        
        def get_text(key):
            val = fields.get(key, {}).get("text", "")
            return [val] if val else []

        return {
            "irradiation_statement": get_text("irradiation_statement"),
        }
