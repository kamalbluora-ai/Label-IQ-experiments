import asyncio
from typing import Dict, Any, List
import json
from pathlib import Path
from compliance.agents.common_name import CommonNameAgent
from compliance.nutrition_facts.auditor import NFTAuditor
from compliance.nutrition_facts.integration import map_docai_to_inputs
from compliance.sweeteners.detector import detect_sweeteners
from compliance.supplements_table.detector import detect_supplements
from compliance.additive.detector import detect_additives
from compliance.health_claims.detector import detect_health_claims
from compliance.agents.ingredients import IngredientsAgent
from compliance.agents.date_marking import DateMarkingAgent
from compliance.agents.fop_symbol import FOPSymbolAgent
from compliance.agents.bilingual import BilingualAgent
from compliance.agents.irradiation import IrradiationAgent
from compliance.agents.country_origin import CountryOriginAgent
from compliance.agents.claim_tag import ClaimTagAgent
from compliance.agents.health_nutrient_claims import HealthNutrientClaimsAgent
from core.db import DatabaseManager


class AttributeOrchestrator:
    def __init__(self):
        self.common_name_agent = CommonNameAgent()
        self.nft_auditor = NFTAuditor()
        self.ingredients_agent = IngredientsAgent()
        self.date_marking_agent = DateMarkingAgent()
        self.fop_symbol_agent = FOPSymbolAgent()
        self.bilingual_agent = BilingualAgent()
        self.irradiation_agent = IrradiationAgent()
        self.country_origin_agent = CountryOriginAgent()
        self.claim_tag_agent = ClaimTagAgent()
        self.health_claims_agent = HealthNutrientClaimsAgent("health_claims")
        
        # Load questions from JSON
        self.questions = self._load_questions()
        self.db = DatabaseManager()

    def _load_questions(self) -> Dict[str, Any]:
        """Load the CFIA checklist questions from JSON."""
        try:
            # Path relative to this file
            path = Path(__file__).parent / "questions.json"
            if not path.exists():
                print(f"WARNING: questions.json not found at {path}")
                return {}
                
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return data.get("sections", {})
        except Exception as e:
            print(f"Error loading questions.json: {e}")
            return {}
    
    async def evaluate(self, label_facts: Dict[str, Any], job_id: str = None) -> Dict[str, Any]:
        """Run all compliance checks in parallel, streaming results as completed."""
        # Helper to get questions safely
        def get_q(key):
            return self.questions.get(key, {}).get("questions", [])

        tasks = {
            "common_name": asyncio.create_task(self._run_agent_with_retry(self.common_name_agent, label_facts, questions=get_q("common_name"), job_id=job_id)),
            "ingredients": asyncio.create_task(self._run_agent_with_retry(self.ingredients_agent, label_facts, questions=get_q("list_of_ingredients"), job_id=job_id)),
            "date_marking": asyncio.create_task(self._run_agent_with_retry(self.date_marking_agent, label_facts, questions=get_q("date_markings"), job_id=job_id)),
            "fop_symbol": asyncio.create_task(self._run_agent_with_retry(self.fop_symbol_agent, label_facts, questions=get_q("fop_nutrition_symbol"), job_id=job_id)),
            "bilingual": asyncio.create_task(self._run_agent_with_retry(self.bilingual_agent, label_facts, questions=get_q("bilingual_requirements"), job_id=job_id)),
            "irradiation": asyncio.create_task(self._run_agent_with_retry(self.irradiation_agent, label_facts, questions=get_q("irradiation"), job_id=job_id)),
            "country_origin": asyncio.create_task(self._run_agent_with_retry(self.country_origin_agent, label_facts, questions=get_q("country_of_origin"), job_id=job_id)),

            "nutrition_facts": asyncio.create_task(asyncio.to_thread(self._run_nft_audit_wrapper, label_facts, job_id)),
            "sweeteners": asyncio.create_task(asyncio.to_thread(self._run_sweetener_detection_wrapper, label_facts, job_id)),
            "supplements": asyncio.create_task(asyncio.to_thread(self._run_supplement_detection_wrapper, label_facts, job_id)),
            "additives": asyncio.create_task(asyncio.to_thread(self._run_additive_detection_wrapper, label_facts, job_id)),
            "health_claims": asyncio.create_task(asyncio.to_thread(self._run_health_claims_detection_wrapper, label_facts, job_id)),
        }
        
        # GUARDRAIL: Only trigger claim_tag agent if claim_tag_type field is not empty
        claim_tag_type = label_facts.get("fields", {}).get("claim_tag_type", {}).get("text")
        if claim_tag_type:
            tasks["claim_tag"] = asyncio.create_task(self._run_agent_with_retry(self.claim_tag_agent, label_facts, questions=[], job_id=job_id))
        
        # Map task objects back to their names
        task_to_name = {task: name for name, task in tasks.items()}
        
        results = {}
        for coro in asyncio.as_completed(tasks.values()):
            result = await coro
            name = task_to_name[coro] if coro in task_to_name else None
            # Find which task completed
            for task, task_name in task_to_name.items():
                if task.done() and task_name not in results:
                    results[task_name] = task.result()
                    print(f"[DONE] {task_name}")
                    break
        
        return results
    
    async def _run_agent_with_retry(self, agent, label_facts, questions, max_retries=2, job_id=None, agent_name=None):
        """Run agent with automatic retry on failure."""
        target_name = agent_name or agent.section_name
        
        if job_id:
            self.db.update_compliance_result(job_id, target_name, "RUNNING")

        for attempt in range(max_retries + 1):
            try:
                result = await agent.evaluate(label_facts, questions)
                # Transform to match frontend expected structure
                final_result = {
                    "check_results": [
                        {
                            "question_id": r.get("question_id", ""),
                            "question": r.get("question", ""),
                            "result": r.get("result", "needs_review"),
                            "selected_value": r.get("selected_value"),
                            "rationale": r.get("rationale", ""),
                            "section": result.get("section", agent.section_name)
                        }
                        for r in result.get("results", [])
                    ]
                }
                if job_id:
                    self.db.update_compliance_result(job_id, target_name, "DONE", final_result)
                return final_result
            except Exception as e:
                if attempt == max_retries:
                    error_result = {
                        "check_results": [{
                            "question_id": f"{target_name}-ERROR",
                            "question": "Agent execution failed",
                            "result": "needs_review",
                            "rationale": f"Error after {max_retries + 1} attempts: {str(e)}",
                            "section": agent.section_name
                        }]
                    }
                    if job_id:
                        self.db.update_compliance_result(job_id, target_name, "ERROR", error_result)
                    return error_result
                await asyncio.sleep(1)
    
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
    
    def _run_supplement_detection(self, label_facts):
        fields = label_facts.get("fields", {})
        nft_text = fields.get("nft_table_en", {}).get("text", "")
        ingredients = fields.get("ingredients_list_en", {}).get("text", "")
        
        result = detect_supplements(nft_text, ingredients)
        return result.model_dump()
    
    def _run_additive_detection(self, label_facts):
        fields = label_facts.get("fields", {})
        ingredients = fields.get("ingredients_list_en", {}).get("text", "")
        nft_text = fields.get("nft_table_en", {}).get("text", "")
        
        result = detect_additives(ingredients, nft_text)
        return result.model_dump()
    
    # --- Wrappers for synchronous detectors to handle DB logging ---
    
    def _run_nft_audit_wrapper(self, label_facts, job_id=None):
        if job_id: self.db.update_compliance_result(job_id, "nutrition_facts", "RUNNING")
        try:
            res = self._run_nft_audit(label_facts)
            if job_id: self.db.update_compliance_result(job_id, "nutrition_facts", "DONE", res)
            return res
        except Exception as e:
            if job_id: self.db.update_compliance_result(job_id, "nutrition_facts", "ERROR", {"error": str(e)})
            return {"error": str(e)}

    def _run_sweetener_detection_wrapper(self, label_facts, job_id=None):
        if job_id: self.db.update_compliance_result(job_id, "sweeteners", "RUNNING")
        try:
            res = self._run_sweetener_detection(label_facts)
            if job_id: self.db.update_compliance_result(job_id, "sweeteners", "DONE", res)
            return res
        except Exception as e:
            if job_id: self.db.update_compliance_result(job_id, "sweeteners", "ERROR", {"error": str(e)})
            return {"error": str(e)}

    def _run_supplement_detection_wrapper(self, label_facts, job_id=None):
        if job_id: self.db.update_compliance_result(job_id, "supplements", "RUNNING")
        try:
            res = self._run_supplement_detection(label_facts)
            if job_id: self.db.update_compliance_result(job_id, "supplements", "DONE", res)
            return res
        except Exception as e:
            if job_id: self.db.update_compliance_result(job_id, "supplements", "ERROR", {"error": str(e)})
            return {"error": str(e)}

    def _run_additive_detection_wrapper(self, label_facts, job_id=None):
        if job_id: self.db.update_compliance_result(job_id, "additives", "RUNNING")
        try:
            res = self._run_additive_detection(label_facts)
            if job_id: self.db.update_compliance_result(job_id, "additives", "DONE", res)
            return res
        except Exception as e:
            if job_id: self.db.update_compliance_result(job_id, "additives", "ERROR", {"error": str(e)})
            return {"error": str(e)}

    def _run_health_claims_detection(self, label_facts):
        fields = label_facts.get("fields", {})
        health_claims_text = fields.get("health_claims_text", {}).get("text", "")
        nutrient_content_text = fields.get("nutrient_content_claims_text", {}).get("text", "")
        nutrient_function_text = fields.get("nutrient_function_claims_text", {}).get("text", "")
        label_text = label_facts.get("text", "")

        result = detect_health_claims(
            health_claims_text=health_claims_text,
            nutrient_content_text=nutrient_content_text,
            nutrient_function_text=nutrient_function_text,
            label_text=label_text,
        )
        return result.model_dump()

    def _run_health_claims_detection_wrapper(self, label_facts, job_id=None):
        if job_id: self.db.update_compliance_result(job_id, "health_claims", "RUNNING")
        try:
            res = self._run_health_claims_detection(label_facts)
            if job_id: self.db.update_compliance_result(job_id, "health_claims", "DONE", res)
            return res
        except Exception as e:
            if job_id: self.db.update_compliance_result(job_id, "health_claims", "ERROR", {"error": str(e)})
            return {"error": str(e)}

    def evaluate_sync(self, label_facts: Dict[str, Any], job_id: str = None) -> Dict[str, Any]:
        """Synchronous wrapper for evaluate()."""
        return asyncio.run(self.evaluate(label_facts, job_id))
