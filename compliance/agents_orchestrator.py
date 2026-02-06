"""
Compliance Orchestrator

Coordinates all compliance agents and aggregates results.
"""

import asyncio
import json
from typing import Dict, List, Any
from pathlib import Path

# Load questions directly from JSON file
_questions_file = Path(__file__).parent / "questions" / "questions.json"
with open(_questions_file, encoding="utf-8") as f:
    QUESTIONS = json.load(f).get("sections", {})

# Import all agents
from compliance.agents.common_name import CommonNameAgent
from compliance.agents.net_quantity import NetQuantityAgent
from compliance.agents.ingredients import IngredientsAgent
from compliance.agents.name_address import NameAddressAgent
from compliance.agents.date_marking import DateMarkingAgent
from compliance.agents.nutrition_facts import NutritionFactsAgent
from compliance.agents.fop_symbol import FOPSymbolAgent
from compliance.agents.bilingual import BilingualAgent
from compliance.agents.irradiation import IrradiationAgent
from compliance.agents.sweeteners import SweetenersAgent
from compliance.agents.country_origin import CountryOriginAgent
from compliance.nft_audit_table.integration import map_docai_to_inputs
from compliance.nft_audit_table.audit_orchestrator import NFTAuditor

class ComplianceOrchestrator:
    """
    Orchestrates compliance evaluation across all agents.
    
    Workflow:
    1. Load questions from questions.json
    2. For each section, dispatch to appropriate agent
    3. Run agents in parallel
    4. Aggregate results and calculate compliance score
    """
    
    def __init__(self):
        self.questions = QUESTIONS
        
        self.nft_auditor = NFTAuditor()
                
        # Initialize all 11 agents
        self.agents = {
            "common_name": CommonNameAgent(),
            # "net_quantity": NetQuantityAgent(),
            # "list_of_ingredients": IngredientsAgent(),
            # "name_and_address": NameAddressAgent(),
            # "date_markings": DateMarkingAgent(),
            # "fop_nutrition_symbol": FOPSymbolAgent(),
            # "bilingual_requirements": BilingualAgent(),
            # "irradiation": IrradiationAgent(),
            # "sweeteners": SweetenersAgent(),
            # "country_of_origin": CountryOriginAgent()
        }
    
    # Questions are now imported directly from compliance.questions
    
    def run_nft_audit(self, label_facts: Dict[str, Any], section_questions: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Run NFT auditor and convert results to orchestrator format.
        
        Returns results with full calculation details for frontend display.
        """
        try:
            # Extract fields from DocAI output
            fields = label_facts.get("fields", {})
            
            # Convert to simple key:value format for integration
            simple_fields = {}
            for key, val in fields.items():
                if isinstance(val, dict) and "text" in val:
                    simple_fields[key] = val["text"]
                else:
                    simple_fields[key] = val
            
            # Map to NutrientData objects
            nutrient_inputs = map_docai_to_inputs(simple_fields)
            
            # Audit each nutrient
            nutrient_audits = []
            for nutrient in nutrient_inputs:
                audit_result = self.nft_auditor.audit_nutrient(nutrient)
                nutrient_audits.append({
                    "nutrient_name": audit_result.nutrient_name,
                    "original_value": audit_result.original_value,
                    "expected_value": audit_result.expected_value,
                    "unit": audit_result.unit,
                    "is_dv": audit_result.is_dv,
                    "status": audit_result.status.value,
                    "message": audit_result.message,
                    "rule_applied": audit_result.rule_applied
                })
            
            # Run cross-field validations
            nutrients_dict = {n.name: n.value for n in nutrient_inputs}
            cross_field_audits = []
            for cross_result in self.nft_auditor.audit_cross_fields(nutrients_dict):
                cross_field_audits.append({
                    "check_name": cross_result.check_name,
                    "status": cross_result.status.value,
                    "message": cross_result.message,
                    "tolerance": cross_result.tolerance
                })
            
            # Convert to orchestrator format
            check_results = []
            for q in section_questions:
                # Determine result based on audit status
                # If any nutrient failed, mark as fail
                has_fail = any(a["status"] == "fail" for a in nutrient_audits)
                has_cross_fail = any(a["status"] == "fail" for a in cross_field_audits)
                
                if has_fail or has_cross_fail:
                    result = "fail"
                    rationale = "NFT audit detected compliance issues. See audit details below."
                else:
                    result = "pass"
                    rationale = "All nutrient values comply with CFIA rounding rules."
                
                check_results.append({
                    "question_id": q["id"],
                    "question": q["text"],
                    "result": result,
                    "rationale": rationale
                })
            
            return {
                "section": "Nutrition Facts Table",
                "results": check_results,
                "audit_details": {  # Full calculation details for frontend
                    "nutrient_audits": nutrient_audits,
                    "cross_field_audits": cross_field_audits
                }
            }
            
        except Exception as e:
            # Return error result
            return {
                "section": "Nutrition Facts Table",
                "results": [
                    {
                        "question_id": q["id"],
                        "question": q["text"],
                        "result": "needs_review",
                        "rationale": f"NFT Auditor error: {str(e)}"
                    }
                    for q in section_questions
                ],
                "audit_details": None
            }
    
    async def evaluate(self, label_facts: Dict[str, Any], user_context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Run compliance evaluation across all agents.
        
        Args:
            label_facts: DocAI output with fields, fields_all, panels, text
            user_context: Optional user-provided context (e.g., food_type)
        
        Returns:
            {
                "compliance_score": float (0-100),
                "checks_passed": int,
                "checks_total": int,
                "check_results": [
                    {
                        "section": str,
                        "question_id": str,
                        "question": str,
                        "result": "pass" | "fail" | "needs_review",
                        "selected_value": str (optional),
                        "rationale": str
                    }
                ]
            }
        """
        # Semaphore to limit concurrent API calls (max 3 at a time)
        semaphore = asyncio.Semaphore(3)
        
        async def run_agent_with_limit(section_key, agent):
            async with semaphore:
                section_questions = self.questions.get(section_key, {}).get("questions", [])
                if not section_questions:
                    return None
                try:
                    # Check if this is the NFT auditor
                    if agent == "NFT_AUDITOR":
                        return self.run_nft_audit(label_facts, section_questions)
                    else:
                        return await agent.evaluate(label_facts, section_questions, user_context)
                except Exception as e:
                    return e
        
        # Run all agents with semaphore limiting
        tasks = [run_agent_with_limit(key, agent) for key, agent in self.agents.items()]
        results = await asyncio.gather(*tasks)
        all_results = [r for r in results if r is not None]
        
        # Aggregate
        return self._aggregate_results(all_results)
    
    def _aggregate_results(self, agent_results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Aggregate results from all agents.
        
        Args:
            agent_results: List of results from each agent
        
        Returns:
            Aggregated compliance report
        """
        all_results = []
        passed = 0
        total = 0
        
        for agent_result in agent_results:
            # Handle exceptions
            if isinstance(agent_result, Exception):
                continue
            
            section = agent_result.get("section", "unknown")
            
            for result in agent_result.get("results", []):
                # Add section to each result
                result["section"] = section
                all_results.append(result)
                
                # Count pass/fail
                total += 1
                if result.get("result") == "pass":
                    passed += 1
        
        # Calculate score
        compliance_score = (passed / total * 100) if total > 0 else 0
        
        return {
            "compliance_score": round(compliance_score, 2),
            "checks_passed": passed,
            "checks_total": total,
            "check_results": all_results,
        }
    
    def evaluate_sync(self, label_facts: Dict[str, Any], user_context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Synchronous wrapper for evaluate().
        Handles both async and non-async calling contexts.
        """
        import concurrent.futures
        
        try:
            # Check if we're in an async context
            asyncio.get_running_loop()
            # We're in an async context - run in a separate thread
            with concurrent.futures.ThreadPoolExecutor() as pool:
                future = pool.submit(asyncio.run, self.evaluate(label_facts, user_context))
                return future.result()
        except RuntimeError:
            # No running loop - safe to use asyncio.run()
            return asyncio.run(self.evaluate(label_facts, user_context))
