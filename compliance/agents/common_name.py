from typing import Dict, Any
from compliance.base_agent import BaseComplianceAgent


class CommonNameAgent(BaseComplianceAgent):
    """
    Agent for Common Name compliance.
    
    Takes all DocAI extracted common_name candidates (text only)
    and evaluates them against CFIA checklist questions.
    """
    
    def __init__(self):
        super().__init__(section_name="Common Name")
    
    def get_section_context(self) -> str:
        """Get section-specific context."""
        return "Evaluate if the product's common name is present, on the Principal Display Panel (PDP), and appropriate per CFIA requirements."
    
    def prepare_input_data(self, label_facts: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract common name fields from DocAI output.
        
        Uses fields_all (all candidates) and extracts text only.
        """
        fields_all = label_facts.get("fields_all", {})
        panels = label_facts.get("panels", {})
        
        # Extract text only from all candidates
        common_name_en = [c.get("text", "") for c in fields_all.get("common_name_en", [])]
        common_name_fr = [c.get("text", "") for c in fields_all.get("common_name_fr", [])]
        
        return {
            "common_name_en": common_name_en,
            "common_name_fr": common_name_fr,
            "panel_pdp": panels.get("panel_pdp", {}).get("text", ""),
        }
