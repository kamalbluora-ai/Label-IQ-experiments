from typing import Dict, Any
from compliance.base_agent import BaseComplianceAgent

class FOPSymbolAgent(BaseComplianceAgent):
    def __init__(self):
        super().__init__(section_name="Front-of-Package (FOP) Nutrition Symbol")
    
    def get_section_context(self) -> str:
        """Get section-specific context."""
        return "Check Front-of-Package nutrition symbol: presence, location on PDP, legibility, and technical specifications."
    
    def prepare_input_data(self, label_facts: Dict[str, Any]) -> Dict[str, Any]:
        fields = label_facts.get("fields", {})
        panels = label_facts.get("panels", {})
        
        def get_text(key):
            val = fields.get(key, {}).get("text", "")
            return [val] if val else []

        return {
            "fop_symbol_present": get_text("fop_symbol"),
            "panel_pdp": panels.get("panel_pdp", {}).get("text", ""),
        }
