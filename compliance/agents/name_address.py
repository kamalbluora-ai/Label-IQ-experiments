"""
Name and Principal Place of Business Compliance Agent
"""

from pathlib import Path
from typing import Dict, Any
from compliance.base_agent import BaseComplianceAgent


class NameAddressAgent(BaseComplianceAgent):
    
    def __init__(self):
        super().__init__(section_name="Name and Principal Place of Business")
    
    def load_system_prompt(self) -> str:
        prompt_path = Path(__file__).parent.parent / "prompts" / "name_address.txt"
        with open(prompt_path, "r", encoding="utf-8") as f:
            return f.read()
    
    def prepare_input_data(self, label_facts: Dict[str, Any]) -> Dict[str, Any]:
        fields_all = label_facts.get("fields_all", {})
        
        return {
            "dealer_name": [c.get("text", "") for c in fields_all.get("dealer_name", [])],
            "dealer_address": [c.get("text", "") for c in fields_all.get("dealer_address", [])],
        }
