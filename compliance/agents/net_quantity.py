"""
Net Quantity Declaration Compliance Agent

Evaluates net quantity compliance against CFIA requirements.
Uses all DocAI candidates (text only) for evaluation.
"""

from pathlib import Path
from typing import Dict, Any
from compliance.base_agent import BaseComplianceAgent


class NetQuantityAgent(BaseComplianceAgent):
    """
    Agent for Net Quantity Declaration compliance.
    
    Takes all DocAI extracted net quantity candidates (text only)
    and evaluates them against CFIA checklist questions.
    """
    
    def __init__(self):
        super().__init__(section_name="Net Quantity Declaration")
    
    def load_system_prompt(self) -> str:
        """Load system prompt from file."""
        prompt_path = Path(__file__).parent.parent / "prompts" / "net_quantity.txt"
        with open(prompt_path, "r", encoding="utf-8") as f:
            return f.read()
    
    def prepare_input_data(self, label_facts: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract net quantity fields from DocAI output.
        
        Uses fields_all (all candidates) and extracts text only.
        """
        fields_all = label_facts.get("fields_all", {})
        panels = label_facts.get("panels", {})
        
        return {
            "net_quantity_full_text": [c.get("text", "") for c in fields_all.get("net_quantity_full_text", [])],
            "net_quantity_value": [c.get("text", "") for c in fields_all.get("net_quantity_value", [])],
            "net_quantity_unit_words_en": [c.get("text", "") for c in fields_all.get("net_quantity_unit_words_en", [])],
            "net_quantity_unit_words_fr": [c.get("text", "") for c in fields_all.get("net_quantity_unit_words_fr", [])],
            "panel_pdp": panels.get("panel_pdp", {}).get("text", ""),
        }
