from typing import Dict, Any
from compliance.base_agent import BaseComplianceAgent

class NutritionFactsAgent(BaseComplianceAgent):
    def __init__(self):
        super().__init__(section_name="Nutrition Facts Table (NFt)")
    
    def get_section_context(self) -> str:
        """Get section-specific context."""
        return "Assess Nutrition Facts Table: format family, serving size alignment, core nutrients declaration, and % Daily Value statement."
    
    def prepare_input_data(self, label_facts: Dict[str, Any]) -> Dict[str, Any]:
        fields_all = label_facts.get("fields_all", {})
        return {
            "nft_title_en": [c.get("text", "") for c in fields_all.get("nft_title_en", [])],
            "nft_title_fr": [c.get("text", "") for c in fields_all.get("nft_title_fr", [])],
            "nft_serving_size_en": [c.get("text", "") for c in fields_all.get("nft_serving_size_en", [])],
            "nft_serving_size_fr": [c.get("text", "") for c in fields_all.get("nft_serving_size_fr", [])],
            "nft_calories_en": [c.get("text", "") for c in fields_all.get("nft_calories_en", [])],
            "nft_calories_fr": [c.get("text", "") for c in fields_all.get("nft_calories_fr", [])],
            "nft_table_en": [c.get("text", "") for c in fields_all.get("nft_table_en", [])],
            "nft_table_fr": [c.get("text", "") for c in fields_all.get("nft_table_fr", [])],
            "nft_text_block_en": [c.get("text", "") for c in fields_all.get("nft_text_block_en", [])],
            "nft_text_block_fr": [c.get("text", "") for c in fields_all.get("nft_text_block_fr", [])],
        }
