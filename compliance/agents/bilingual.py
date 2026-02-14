from typing import Dict, Any
from compliance.base_agent import BaseComplianceAgent

class BilingualAgent(BaseComplianceAgent):
    def __init__(self):
        super().__init__(section_name="Bilingual Requirements")
    
    def get_section_context(self) -> str:
        """Get section-specific context."""
        return "Verify all mandatory information is present in both English and French, unless a bilingual exemption applies."
    
    def prepare_input_data(self, label_facts: Dict[str, Any]) -> Dict[str, Any]:
        fields = label_facts.get("fields", {})
        
        def get_text(key):
            val = fields.get(key, {}).get("text", "")
            return [val] if val else []

        return {
            "common_name_en": get_text("common_name_en"),
            "common_name_fr": get_text("common_name_fr"),
            "ingredients_list_en": get_text("ingredients_list_en"),
            "ingredients_list_fr": get_text("ingredients_list_fr"),
            "nft_table_en": get_text("nft_table_en"),
            "nft_table_fr": get_text("nft_table_fr")
        }
