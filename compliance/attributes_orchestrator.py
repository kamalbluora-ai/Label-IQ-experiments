import asyncio
from typing import Dict, Any

# Active components
from compliance.agents.common_name import CommonNameAgent
from compliance.nutrition_facts.auditor import NFTAuditor
from compliance.nutrition_facts.integration import map_docai_to_inputs
from compliance.sweeteners.detector import detect_sweeteners

# from compliance.agents.net_quantity import NetQuantityAgent
# from compliance.agents.ingredients import IngredientsAgent
# from compliance.agents.date_marking import DateMarkingAgent
# from compliance.agents.fop_symbol import FOPSymbolAgent
# from compliance.agents.bilingual import BilingualAgent
# from compliance.agents.irradiation import IrradiationAgent
# from compliance.agents.country_origin import CountryOriginAgent


class AttributeOrchestrator:
    def __init__(self):
        self.common_name_agent = CommonNameAgent()
        self.nft_auditor = NFTAuditor()
    
    async def evaluate(self, label_facts: Dict[str, Any]) -> Dict[str, Any]:
        """Run all compliance checks in parallel."""
        common_name, nft, sweeteners = await asyncio.gather(
            self._run_common_name(label_facts),
            asyncio.to_thread(self._run_nft_audit, label_facts),
            asyncio.to_thread(self._run_sweetener_detection, label_facts),
        )
        return {
            "common_name": common_name,
            "nutrition_facts": nft,
            "sweeteners": sweeteners,
        }
    
    async def _run_common_name(self, label_facts):
        return await self.common_name_agent.evaluate(label_facts, [])
    
    def _run_nft_audit(self, label_facts):
        fields = label_facts.get("fields", {})
        docai_flat = {k: v.get("text") for k, v in fields.items()}
        
        nutrients = map_docai_to_inputs(docai_flat)
        
        # Run audits
        nutrient_results = [self.nft_auditor.audit_nutrient(n) for n in nutrients]
        
        # Build dict for cross-field checks
        nutrient_dict = {n.name: n.value for n in nutrients}
        cross_results = self.nft_auditor.audit_cross_fields(nutrient_dict)
        
        return {
            "nutrient_audits": [r.__dict__ for r in nutrient_results],
            "cross_field_audits": [r.__dict__ for r in cross_results]
        }
    
    def _run_sweetener_detection(self, label_facts):
        fields = label_facts.get("fields", {})
        ingredients = fields.get("ingredients_list_en", {}).get("text", "")
        nft_text = fields.get("nft_table_en", {}).get("text", "")
        
        result = detect_sweeteners(ingredients, nft_text)
        return result.model_dump()
    
    def evaluate_sync(self, label_facts: Dict[str, Any]) -> Dict[str, Any]:
        """Synchronous wrapper for evaluate()."""
        return asyncio.run(self.evaluate(label_facts))
