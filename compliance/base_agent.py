import json
from abc import ABC, abstractmethod
from typing import Dict, List, Any
from google import genai
from dotenv import load_dotenv
from compliance.prompt import format_prompt

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
        self.client = genai.Client()
    
    @abstractmethod
    def get_section_context(self) -> str:
        """
        Get the section-specific context/instruction for this agent.
        Should be implemented by each specific agent.
        
        Returns:
            Short description of what this agent evaluates (e.g., "Evaluate common name compliance")
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
    
    def build_system_prompt(self, data: Dict[str, Any], questions: List[Dict[str, Any]]) -> str:
        """
        Build the complete system prompt using the dynamic prompt builder.
        
        Args:
            data: Prepared input data (from prepare_input_data)
            questions: List of questions for this section
        
        Returns:
            Complete system prompt
        """
        # Add user context to fields if present
        fields = data.copy()
        if "user_context" in fields:
            # Keep user_context in the fields for the LLM to see
            pass
        
        return format_prompt(
            section_context=self.get_section_context(),
            questions=questions,
            fields=fields
        )
    
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
            
            # Build complete system prompt
            system_prompt = self.build_system_prompt(data, questions)
            
            # Call LLM with Gemini
            response = self.client.models.generate_content(
                model="gemini-3-flash-preview",
                contents=system_prompt,
                config={
                    "response_mime_type": "application/json",
                    "thinking_config": {"thinking_level": "high"}
                }
            )
            
            # Parse response
            result = json.loads(response.text)
            
            # Handle different response shapes from LLM
            if isinstance(result, list):
                # LLM returned a list directly instead of {"results": [...]}
                results = result
            elif isinstance(result, dict):
                results = result.get("results", [])
            else:
                results = []
            
            return {
                "section": self.section_name,
                "results": results
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


