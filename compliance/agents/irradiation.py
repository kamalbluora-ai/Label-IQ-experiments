from typing import Dict, Any
from compliance.base_agent import BaseComplianceAgent

class IrradiationAgent(BaseComplianceAgent):
    def __init__(self):
        super().__init__(section_name="Irradiation")
    
    def get_section_context(self) -> str:
        """Get section-specific context."""
        return "Check irradiation labeling if applicable: statement presence, international symbol on PDP, and ingredient declarations."
    
    def prepare_input_data(self, label_facts: Dict[str, Any]) -> Dict[str, Any]:
        fields_all = label_facts.get("fields_all", {})
        return {
            "irradiation_statement": [c.get("text", "") for c in fields_all.get("irradiation_statement", [])],
        }
