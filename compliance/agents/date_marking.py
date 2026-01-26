from typing import Dict, Any
from compliance.base_agent import BaseComplianceAgent


class DateMarkingAgent(BaseComplianceAgent):
    
    def __init__(self):
        super().__init__(section_name="Date Markings")
    
    def get_section_context(self) -> str:
        """Get section-specific context."""
        return "Evaluate date markings: best before, packaged on, expiration dates, storage instructions, and proper wording/placement."
    
    def prepare_input_data(self, label_facts: Dict[str, Any]) -> Dict[str, Any]:
        fields_all = label_facts.get("fields_all", {})
        
        return {
            "best_before_date": [c.get("text", "") for c in fields_all.get("best_before_date", [])],
            "packaged_on_date": [c.get("text", "") for c in fields_all.get("packaged_on_date", [])],
            "expiration_date": [c.get("text", "") for c in fields_all.get("expiration_date", [])],
            "storage_instructions": [c.get("text", "") for c in fields_all.get("storage_instructions", [])],
        }
