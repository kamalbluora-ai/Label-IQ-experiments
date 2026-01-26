from typing import Dict, Any
from compliance.base_agent import BaseComplianceAgent


class NetQuantityAgent(BaseComplianceAgent):
    """
    Agent for Net Quantity Declaration compliance.
    
    Takes all DocAI extracted net quantity candidates (text only)
    and evaluates them against CFIA checklist questions.
    """
    
    def __init__(self):
        super().__init__(section_name="Net Quantity Declaration")
    
    def get_section_context(self) -> str:
        """Get section-specific context."""
        return "Verify net quantity declaration: metric units, proper rounding, correct bilingual symbols, and appropriate measurement type."
    
    def prepare_input_data(self, label_facts: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract net quantity fields from DocAI output.
        
        Uses fields_all (all candidates) and extracts text only.
        """
        fields_all = label_facts.get("fields_all", {})
        panels = label_facts.get("panels", {})
        
        return {
            "net_quantity_full_text": [c.get("text", "") for c in fields_all.get("net_quantity_full_text", [])],
            "net_quantity_value": [c.get("text", "") for c in fields_all.get("net_quantity_value", [])],
            "net_quantity_unit_words_en": [c.get("text", "") for c in fields_all.get("net_quantity_unit_words_en", [])],
            "net_quantity_unit_words_fr": [c.get("text", "") for c in fields_all.get("net_quantity_unit_words_fr", [])],
            "panel_pdp": panels.get("panel_pdp", {}).get("text", ""),
        }
