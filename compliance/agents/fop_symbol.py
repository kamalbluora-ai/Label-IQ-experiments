from typing import Dict, Any
from compliance.base_agent import BaseComplianceAgent

class FOPSymbolAgent(BaseComplianceAgent):
    def __init__(self):
        super().__init__(section_name="Front-of-Package (FOP) Nutrition Symbol")
    
    def get_section_context(self) -> str:
        """Get section-specific context."""
        return "Check Front-of-Package nutrition symbol: presence, location on PDP, legibility, and technical specifications."
    
    def prepare_input_data(self, label_facts: Dict[str, Any]) -> Dict[str, Any]:
        fields_all = label_facts.get("fields_all", {})
        panels = label_facts.get("panels", {})
        return {
            "fop_symbol_present": [c.get("text", "") for c in fields_all.get("fop_symbol", [])],
            "panel_pdp": panels.get("panel_pdp", {}).get("text", ""),
        }
