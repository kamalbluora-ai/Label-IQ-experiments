"""
Compliance Orchestrator

Coordinates all compliance agents and aggregates results.
"""

import json
import asyncio
from typing import Dict, List, Any
from pathlib import Path

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


class ComplianceOrchestrator:
    """
    Orchestrates compliance evaluation across all agents.
    
    Workflow:
    1. Load questions from questions.json
    2. For each section, dispatch to appropriate agent
    3. Run agents in parallel
    4. Aggregate results and calculate compliance score
    """
    
    def __init__(self, questions_path: str = "questions/questions.json"):
        self.questions_path = Path(questions_path)
        self.questions = self._load_questions()
        
        # Initialize all 11 agents
        self.agents = {
            "common_name": CommonNameAgent(),
            "net_quantity": NetQuantityAgent()

            # Other agents commented out - needs improvement
            # "list_of_ingredients": IngredientsAgent(),
            # "name_and_address": NameAddressAgent(),
            # "date_markings": DateMarkingAgent(),
            # "nutrition_facts_table": NutritionFactsAgent(),
            # "fop_nutrition_symbol": FOPSymbolAgent(),
            # "bilingual_requirements": BilingualAgent(),
            # "irradiation": IrradiationAgent(),
            # "sweeteners": SweetenersAgent(),
            # "country_of_origin": CountryOriginAgent(),
        }
    
    def _load_questions(self) -> Dict[str, Any]:
        """Load questions from JSON file."""
        if not self.questions_path.exists():
            raise FileNotFoundError(
                f"Questions file not found: {self.questions_path}\n"
                f"Please run questions/cfia_crawler.py and questions/question_extractor.py first."
            )
        
        with open(self.questions_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        return data.get("sections", {})
    
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
        # Run all agents sequentially (avoids async context issues)
        agent_results = []
        for section_key, agent in self.agents.items():
            section_questions = self.questions.get(section_key, {}).get("questions", [])
            if section_questions:
                try:
                    result = await agent.evaluate(label_facts, section_questions, user_context)
                    agent_results.append(result)
                except Exception as e:
                    agent_results.append(e)
        
        # Aggregate
        return self._aggregate_results(agent_results)
    
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
