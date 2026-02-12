import asyncio
from typing import Dict, Any, List
import json
from compliance.agents.common_name import CommonNameAgent
from compliance.agents.ingredients import IngredientsAgent
from compliance.agents.date_marking import DateMarkingAgent
from compliance.agents.fop_symbol import FOPSymbolAgent
from compliance.agents.bilingual import BilingualAgent
from compliance.agents.irradiation import IrradiationAgent
from compliance.agents.country_origin import CountryOriginAgent
from compliance.agents.claim_tag import ClaimTagAgent
from compliance.nutrition_facts.auditor import NFTAuditor
# from compliance.nutrition_facts.integration import map_docai_to_inputs # Removed as requested in implementation details
from compliance.sweeteners.detector import detect_sweeteners
from compliance.supplements_table.detector import detect_supplements
from compliance.additive.detector import detect_additives
from compliance.attributes_orchestrator import AttributeOrchestrator
from core.db import DatabaseManager


# Agent group definitions
AGENT_GROUPS = {
    "identity": ["common_name", "bilingual", "country_origin", "irradiation"],
    "content": ["ingredients", "date_marking", "fop_symbol", "claim_tag"],
    "tables": ["nutrition_facts", "sweeteners", "supplements", "additives"],
}


class GroupExecutor:
    """Executes a specific group of compliance agents."""

    def __init__(self):
        self.orchestrator = AttributeOrchestrator()
        self.db = DatabaseManager()
        self.questions = self.orchestrator.questions

    def _get_questions(self, key: str) -> list:
        return self.questions.get(key, {}).get("questions", [])

    async def execute_group(self, group: str, label_facts: Dict[str, Any], job_id: str) -> Dict[str, Any]:
        """Run all agents in a group concurrently."""
        agent_names = AGENT_GROUPS.get(group, [])
        if not agent_names:
            raise ValueError(f"Unknown group: {group}")

        results = {}

        if group == "identity":
            results = await self._run_identity_group(label_facts, job_id)
        elif group == "content":
            results = await self._run_content_group(label_facts, job_id)
        elif group == "tables":
            results = await self._run_tables_group(label_facts, job_id)

        return results

    async def _run_identity_group(self, label_facts: Dict, job_id: str) -> Dict:
        """Group A: CommonName, Bilingual, CountryOrigin, Irradiation."""
        tasks = {
            "common_name": asyncio.create_task(
                self.orchestrator._run_agent_with_retry(
                    self.orchestrator.common_name_agent, label_facts,
                    questions=self._get_questions("common_name"), job_id=job_id,
                    agent_name="common_name"
                )
            ),
            "bilingual": asyncio.create_task(
                self.orchestrator._run_agent_with_retry(
                    self.orchestrator.bilingual_agent, label_facts,
                    questions=self._get_questions("bilingual_requirements"), job_id=job_id,
                    agent_name="bilingual"
                )
            ),
            "country_origin": asyncio.create_task(
                self.orchestrator._run_agent_with_retry(
                    self.orchestrator.country_origin_agent, label_facts,
                    questions=self._get_questions("country_of_origin"), job_id=job_id,
                    agent_name="country_origin"
                )
            ),
            "irradiation": asyncio.create_task(
                self.orchestrator._run_agent_with_retry(
                    self.orchestrator.irradiation_agent, label_facts,
                    questions=self._get_questions("irradiation"), job_id=job_id,
                    agent_name="irradiation"
                )
            ),
        }

        results = {}
        for name, task in tasks.items():
            results[name] = await task

        return results

    async def _run_content_group(self, label_facts: Dict, job_id: str) -> Dict:
        """Group B: Ingredients, DateMarking, FOPSymbol, ClaimTag."""
        tasks = {
            "ingredients": asyncio.create_task(
                self.orchestrator._run_agent_with_retry(
                    self.orchestrator.ingredients_agent, label_facts,
                    questions=self._get_questions("list_of_ingredients"), job_id=job_id,
                    agent_name="ingredients"
                )
            ),
            "date_marking": asyncio.create_task(
                self.orchestrator._run_agent_with_retry(
                    self.orchestrator.date_marking_agent, label_facts,
                    questions=self._get_questions("date_markings"), job_id=job_id,
                    agent_name="date_marking"
                )
            ),
            "fop_symbol": asyncio.create_task(
                self.orchestrator._run_agent_with_retry(
                    self.orchestrator.fop_symbol_agent, label_facts,
                    questions=self._get_questions("fop_nutrition_symbol"), job_id=job_id,
                    agent_name="fop_symbol"
                )
            ),
        }

        # ClaimTag is conditional
        claim_tag_type = label_facts.get("fields", {}).get("claim_tag_type", {}).get("text")
        if claim_tag_type:
            tasks["claim_tag"] = asyncio.create_task(
                self.orchestrator._run_agent_with_retry(
                    self.orchestrator.claim_tag_agent, label_facts,
                    questions=[], job_id=job_id,
                    agent_name="claim_tag"
                )
            )

        results = {}
        for name, task in tasks.items():
            results[name] = await task

        return results

    async def _run_tables_group(self, label_facts: Dict, job_id: str) -> Dict:
        """Group C: NFTAuditor, Sweeteners, Supplements, Additives."""
        tasks = {
            "nutrition_facts": asyncio.create_task(
                asyncio.to_thread(self.orchestrator._run_nft_audit_wrapper, label_facts, job_id)
            ),
            "sweeteners": asyncio.create_task(
                asyncio.to_thread(self.orchestrator._run_sweetener_detection_wrapper, label_facts, job_id)
            ),
            "supplements": asyncio.create_task(
                asyncio.to_thread(self.orchestrator._run_supplement_detection_wrapper, label_facts, job_id)
            ),
            "additives": asyncio.create_task(
                asyncio.to_thread(self.orchestrator._run_additive_detection_wrapper, label_facts, job_id)
            ),
        }

        results = {}
        for name, task in tasks.items():
            results[name] = await task

        return results

    def execute_group_sync(self, group: str, label_facts: Dict, job_id: str) -> Dict:
        """Synchronous wrapper."""
        return asyncio.run(self.execute_group(group, label_facts, job_id))
