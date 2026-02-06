from typing import Dict, Any, List
from compliance.base_agent import BaseComplianceAgent


class CommonNameAgent(BaseComplianceAgent):
    """
    Agent for Common Name compliance.
    
    Takes all DocAI extracted common_name candidates (text only)
    and evaluates them against CFIA checklist questions.
    """
    
    def __init__(self):
        super().__init__(section_name="Common Name")
    
    def get_section_context(self) -> str:
        """Get section-specific context."""
        return "Evaluate if the product's common name is present, on the Principal Display Panel (PDP), and appropriate per CFIA requirements."
    
    def prepare_input_data(self, label_facts: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract common name fields from DocAI output.
        
        Uses fields_all (all candidates) and extracts text only.
        """
        fields_all = label_facts.get("fields_all", {})
        panels = label_facts.get("panels", {})
        
        # Extract ALL candidates - TEXT ONLY (no confidence scores)
        en_candidates = fields_all.get("common_name_en", [])
        fr_candidates = fields_all.get("common_name_fr", [])
        
        common_name_en = [c.get("text", "") for c in en_candidates if c.get("text")]
        common_name_fr = [c.get("text", "") for c in fr_candidates if c.get("text")]
        
        return {
            "common_name_en": common_name_en,  # List of text strings only
            "common_name_fr": common_name_fr,  # List of text strings only
            "panel_pdp": panels.get("panel_pdp", {}).get("text", ""),
        }
    
    async def evaluate(
        self, 
        label_facts: Dict[str, Any],
        questions: List[Dict[str, Any]],
        user_context: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Evaluate common name compliance with guardrail logic.
        
        Guardrail: If only 1 candidate exists for a language, use it directly without LLM.
        """
        # Prepare data
        data = self.prepare_input_data(label_facts)
        
        # Add product description from user_context if provided
        if user_context and "product_description" in user_context:
            data["product_description"] = user_context["product_description"]
        
        # GUARDRAIL: If only 1 candidate exists, skip agent
        en_candidates = data.get("common_name_en", [])
        fr_candidates = data.get("common_name_fr", [])
        
        if len(en_candidates) == 1 and len(fr_candidates) == 1:
            # Both have exactly 1 value - use them directly
            return {
                "section": self.section_name,
                "results": [
                    {
                        "question_id": q["id"],
                        "question": q["text"],
                        "result": "pass",
                        "selected_value": en_candidates[0] if "en" in q["id"].lower() else fr_candidates[0],
                        "rationale": "Single candidate detected, used directly without agent evaluation."
                    }
                    for q in questions
                ]
            }
        
        # Multiple candidates exist - call parent evaluate (LLM)
        return await super().evaluate(label_facts, questions, user_context)
