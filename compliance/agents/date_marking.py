"""
Date Markings Compliance Agent
"""

from pathlib import Path
from typing import Dict, Any
from compliance.base_agent import BaseComplianceAgent


class DateMarkingAgent(BaseComplianceAgent):
    
    def __init__(self):
        super().__init__(section_name="Date Markings")
    
    def load_system_prompt(self) -> str:
        prompt_path = Path(__file__).parent.parent / "prompts" / "date_markings.txt"
        with open(prompt_path, "r", encoding="utf-8") as f:
            return f.read()
    
    def prepare_input_data(self, label_facts: Dict[str, Any]) -> Dict[str, Any]:
        fields_all = label_facts.get("fields_all", {})
        
        return {
            "best_before_date": [c.get("text", "") for c in fields_all.get("best_before_date", [])],
            "packaged_on_date": [c.get("text", "") for c in fields_all.get("packaged_on_date", [])],
            "expiration_date": [c.get("text", "") for c in fields_all.get("expiration_date", [])],
            "storage_instructions": [c.get("text", "") for c in fields_all.get("storage_instructions", [])],
        }
