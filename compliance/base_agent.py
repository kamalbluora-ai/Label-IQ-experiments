"""
Base Compliance Agent

Abstract base class for all compliance agents.
Each agent evaluates one CFIA checklist section.
"""

import json
from abc import ABC, abstractmethod
from typing import Dict, List, Any
from pathlib import Path
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()


class BaseComplianceAgent(ABC):
    """
    Base class for all compliance agents.
    
    Each agent:
    - Handles one CFIA section (e.g., Common Name, Net Quantity)
    - Has a specialized system prompt with domain knowledge
    - Receives relevant DocAI fields + questions
    - Returns structured compliance results
    """
    
    def __init__(self, section_name: str):
        self.section_name = section_name
        self.client = OpenAI()
        self.system_prompt = self.load_system_prompt()
    
    @abstractmethod
    def load_system_prompt(self) -> str:
        """
        Load the system prompt for this agent.
        Should be implemented by each specific agent.
        """
        pass
    
    @abstractmethod
    def prepare_input_data(self, label_facts: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract relevant fields from DocAI output for this agent.
        Should be implemented by each specific agent.
        
        Args:
            label_facts: Full DocAI output with fields, fields_all, panels, text
        
        Returns:
            Dict with only the relevant data for this agent
        """
        pass
    
    def build_user_prompt(self, data: Dict[str, Any], questions: List[Dict[str, Any]]) -> str:
        """
        Build the user prompt for LLM evaluation.
        
        Args:
            data: Prepared input data (from prepare_input_data)
            questions: List of questions for this section
        
        Returns:
            Formatted user prompt
        """
        questions_text = self._format_questions(questions)
        
        # Add user context instructions if present
        context_instructions = ""
        if "user_context" in data:
            context_instructions = """
USER CONTEXT:
The user has provided additional context about this product. Use this information
when evaluating compliance questions (e.g., food_type may affect storage requirements,
is_imported may affect country of origin requirements).
"""
        
        return f"""SECTION: {self.section_name}
{context_instructions}
EXTRACTED DATA:
{json.dumps(data, indent=2, ensure_ascii=False)}

QUESTIONS TO ANSWER:
{questions_text}

For each question, respond with:
{{
  "results": [
    {{
      "question_id": "...",
      "question": "...",
      "result": "pass" | "fail" | "needs_review",
      "selected_value": "the value you evaluated (if applicable)",
      "rationale": "detailed explanation of your decision"
    }}
  ]
}}
"""
    
    def _format_questions(self, questions: List[Dict[str, Any]]) -> str:
        """Format questions for the prompt."""
        formatted = []
        for q in questions:
            formatted.append(f"[{q['id']}] {q['text']}")
            if q.get('sub_questions'):
                for sub_q in q['sub_questions']:
                    formatted.append(f"    - {sub_q}")
        return "\n".join(formatted)
    
    async def evaluate(
        self, 
        label_facts: Dict[str, Any],
        questions: List[Dict[str, Any]],
        user_context: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Main evaluation method.
        
        Args:
            label_facts: Full DocAI output
            questions: Questions for this section
            user_context: Optional user-provided context (e.g., food_type)
        
        Returns:
            {
                "section": str,
                "results": [
                    {
                        "question_id": str,
                        "question": str,
                        "result": "pass" | "fail" | "needs_review",
                        "selected_value": str (optional),
                        "rationale": str
                    }
                ]
            }
        """
        try:
            # Prepare data
            data = self.prepare_input_data(label_facts)
            
            # Add user context if provided
            if user_context:
                data["user_context"] = user_context
            
            # Build prompt
            user_prompt = self.build_user_prompt(data, questions)
            
            # Call LLM
            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                response_format={"type": "json_object"},
                temperature=0.2  # Low for consistency
            )
            
            # Parse response
            result = json.loads(response.choices[0].message.content)
            
            return {
                "section": self.section_name,
                "results": result.get("results", [])
            }
            
        except Exception as e:
            # Graceful fallback
            return {
                "section": self.section_name,
                "error": str(e),
                "results": [
                    {
                        "question_id": q["id"],
                        "question": q["text"],
                        "result": "needs_review",
                        "rationale": f"Agent error: {str(e)}"
                    }
                    for q in questions
                ]
            }
