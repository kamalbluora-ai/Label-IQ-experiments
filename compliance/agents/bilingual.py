"""Bilingual Requirements Agent"""
from pathlib import Path
from typing import Dict, Any
from compliance.base_agent import BaseComplianceAgent

class BilingualAgent(BaseComplianceAgent):
    def __init__(self):
        super().__init__(section_name="Bilingual Requirements")
    
    def load_system_prompt(self) -> str:
        prompt_path = Path(__file__).parent.parent / "prompts" / "bilingual.txt"
        with open(prompt_path, "r", encoding="utf-8") as f:
            return f.read()
    
    def prepare_input_data(self, label_facts: Dict[str, Any]) -> Dict[str, Any]:
        fields_all = label_facts.get("fields_all", {})
        return {
            "common_name_en": [c.get("text", "") for c in fields_all.get("common_name_en", [])],
            "common_name_fr": [c.get("text", "") for c in fields_all.get("common_name_fr", [])],
            "ingredients_list_en": [c.get("text", "") for c in fields_all.get("ingredients_list_en", [])],
            "ingredients_list_fr": [c.get("text", "") for c in fields_all.get("ingredients_list_fr", [])],
        }
