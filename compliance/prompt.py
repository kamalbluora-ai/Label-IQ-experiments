import json
from typing import List, Dict, Any


# Pre-built prompt skeleton (loaded once at module import)
SYSTEM_PROMPT_SKELETON = """You are a Canadian Food Compliance Agent.

Use your reasoning capabilities to judge if the food label is compliant with CFIA regulations.

DECISION RULES:
• PASS: Requirement clearly met
• FAIL: Requirement clearly NOT met  
• NEEDS_REVIEW: Cannot determine from available data

SUB-QUESTION LOGIC:
• If a question has sub-questions, ONLY evaluate sub-questions if the main question result is "FAIL"
• If main question is "PASS" or "NEEDS_REVIEW", skip sub-questions entirely

---
SECTION FOCUS:
{section_context}

QUESTIONS:
{questions}

EXTRACTED DATA:
{fields}
---

OUTPUT: JSON with "results" array. Each result must have:
- question_id: The question ID (e.g., "CN-1")
- question: The full question text
- result: "pass" | "fail" | "needs_review"
- selected_value: The value you evaluated (if applicable)
- rationale: Detailed explanation of your decision
"""


def format_questions(questions: List[Dict[str, Any]]) -> str:
    """Format questions for the prompt."""
    formatted = []
    for q in questions:
        formatted.append(f"[{q['id']}] {q['text']}")
        if q.get('sub_questions'):
            for sub_q in q['sub_questions']:
                formatted.append(f"    - {sub_q}")
    return "\n".join(formatted)


def format_prompt(
    section_context: str,
    questions: List[Dict[str, Any]],
    fields: Dict[str, Any]
) -> str:
    """
    Inject inputs into the pre-built prompt skeleton.
    
    Args:
        section_context: Agent-specific instruction (e.g., "Evaluate common name compliance")
        questions: List of questions for this section
        fields: Extracted DocAI fields relevant to this agent
    
    Returns:
        Complete system prompt ready for LLM
    """
    return SYSTEM_PROMPT_SKELETON.format(
        section_context=section_context,
        questions=format_questions(questions),
        fields=json.dumps(fields, indent=2, ensure_ascii=False)
    )
