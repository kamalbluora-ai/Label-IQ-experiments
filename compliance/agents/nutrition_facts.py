"""Nutrition Facts Table Compliance Agent"""
from pathlib import Path
from typing import Dict, Any
from compliance.base_agent import BaseComplianceAgent

class NutritionFactsAgent(BaseComplianceAgent):
    def __init__(self):
        super().__init__(section_name="Nutrition Facts Table (NFt)")
    
    def load_system_prompt(self) -> str:
        prompt_path = Path(__file__).parent.parent / "prompts" / "nutrition_facts.txt"
        with open(prompt_path, "r", encoding="utf-8") as f:
            return f.read()
    
    def prepare_input_data(self, label_facts: Dict[str, Any]) -> Dict[str, Any]:
        fields_all = label_facts.get("fields_all", {})
        return {
            "nft_title_en": [c.get("text", "") for c in fields_all.get("nft_title_en", [])],
            "nft_title_fr": [c.get("text", "") for c in fields_all.get("nft_title_fr", [])],
            "nft_serving_size_en": [c.get("text", "") for c in fields_all.get("nft_serving_size_en", [])],
            "nft_serving_size_fr": [c.get("text", "") for c in fields_all.get("nft_serving_size_fr", [])],
            "nft_calories_en": [c.get("text", "") for c in fields_all.get("nft_calories_en", [])],
            "nft_table_en": [c.get("text", "") for c in fields_all.get("nft_table_en", [])],
            "nft_table_fr": [c.get("text", "") for c in fields_all.get("nft_table_fr", [])],
        }
