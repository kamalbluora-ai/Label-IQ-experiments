from typing import Dict, Any
from compliance.base_agent import BaseComplianceAgent


class DateMarkingAgent(BaseComplianceAgent):
    
    def __init__(self):
        super().__init__(section_name="Date Markings")
    
    def get_section_context(self) -> str:
        """Get section-specific context."""
        return "Evaluate date markings: best before, packaged on, expiration dates, storage instructions, and proper wording/placement."
    
    def prepare_input_data(self, label_facts: Dict[str, Any]) -> Dict[str, Any]:
        fields = label_facts.get("fields", {})
        
        def get_text(key):
            val = fields.get(key, {}).get("text", "")
            return [val] if val else []

        return {
            "best_before_date": get_text("best_before_date"),
            "packaged_on_date": get_text("packaged_on_date"),
            "expiration_date": get_text("expiration_date"),
            "storage_instructions": get_text("storage_instructions"),
        }
