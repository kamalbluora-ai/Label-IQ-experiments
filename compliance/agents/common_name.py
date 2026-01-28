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
        fields = label_facts.get("fields", {})
        panels = label_facts.get("panels", {})
        
        # Extract text only from best candidate
        common_name_en = fields.get("common_name_en", {}).get("text", "")
        common_name_fr = fields.get("common_name_fr", {}).get("text", "")
        
        return {
            "common_name_en": [common_name_en] if common_name_en else [],
            "common_name_fr": [common_name_fr] if common_name_fr else [],
            "panel_pdp": panels.get("panel_pdp", {}).get("text", ""),
        }
