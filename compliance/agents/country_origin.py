"""Country of Origin Agent"""
from pathlib import Path
from typing import Dict, Any
from compliance.base_agent import BaseComplianceAgent

class CountryOriginAgent(BaseComplianceAgent):
    def __init__(self):
        super().__init__(section_name="Country of Origin")
    
    def load_system_prompt(self) -> str:
        prompt_path = Path(__file__).parent.parent / "prompts" / "country_origin.txt"
        with open(prompt_path, "r", encoding="utf-8") as f:
            return f.read()
    
    def prepare_input_data(self, label_facts: Dict[str, Any]) -> Dict[str, Any]:
        fields_all = label_facts.get("fields_all", {})
        return {
            "country_of_origin": [c.get("text", "") for c in fields_all.get("country_of_origin", [])],
            "dealer_address": [c.get("text", "") for c in fields_all.get("dealer_address", [])],
        }
