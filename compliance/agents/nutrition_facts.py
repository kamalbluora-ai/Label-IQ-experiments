from typing import Dict, Any
from compliance.base_agent import BaseComplianceAgent

class NutritionFactsAgent(BaseComplianceAgent):
    def __init__(self):
        super().__init__(section_name="Nutrition Facts Table (NFt)")
    
    def get_section_context(self) -> str:
        """Get section-specific context."""
        return "Assess Nutrition Facts Table: format family, serving size alignment, core nutrients declaration, and % Daily Value statement."
    
    def prepare_input_data(self, label_facts: Dict[str, Any]) -> Dict[str, Any]:
        fields = label_facts.get("fields", {})
        
        def get_text(key):
            val = fields.get(key, {}).get("text", "")
            return [val] if val else []

        return {
            "nft_title_en": get_text("nft_title_en"),
            "nft_title_fr": get_text("nft_title_fr"),
            "nft_serving_size_en": get_text("nft_serving_size_en"),
            "nft_serving_size_fr": get_text("nft_serving_size_fr"),
            "nft_calories_en": get_text("nft_calories_en"),
            "nft_calories_fr": get_text("nft_calories_fr"),
            "nft_table_en": get_text("nft_table_en"),
            "nft_table_fr": get_text("nft_table_fr"),
            "nft_text_block_en": get_text("nft_text_block_en"),
            "nft_text_block_fr": get_text("nft_text_block_fr"),
        }
