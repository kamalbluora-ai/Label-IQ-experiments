from typing import Dict, List, Any
from compliance.base_agent import BaseComplianceAgent

class FOPSymbolAgent(BaseComplianceAgent):
    def __init__(self):
        super().__init__(section_name="Front-of-Package (FOP) Nutrition Symbol")
    
    def get_section_context(self) -> str:
        """Get section-specific context."""
        return "Check Front-of-Package nutrition symbol: presence, location on PDP, legibility, and technical specifications."
    
    def prepare_input_data(self, label_facts: Dict[str, Any]) -> Dict[str, Any]:
        fields = label_facts.get("fields", {})
        panels = label_facts.get("panels", {})
        
        def get_text(key):
            val = fields.get(key, {}).get("text", "")
            return [val] if val else []

        return {
            "fop_symbol_present": get_text("fop_symbol"),
            "panel_pdp": panels.get("panel_pdp", {}).get("text", ""),
        }

    async def evaluate(
        self,
        label_facts: Dict[str, Any],
        questions: List[Dict[str, Any]],
        user_context: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """Evaluate with product_description injected into input data."""
        # Inject product_description so the LLM can see it
        original_prepare = self.prepare_input_data
        def patched_prepare(lf):
            data = original_prepare(lf)
            if user_context and "product_description" in user_context:
                data["product_description"] = user_context["product_description"]
            return data
        self.prepare_input_data = patched_prepare
        
        result = await super().evaluate(label_facts, questions, user_context)
        
        self.prepare_input_data = original_prepare
        return result
