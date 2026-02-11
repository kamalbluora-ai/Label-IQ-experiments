"""
GPT-Based Compliance Evaluation Module.

This module provides dynamic compliance checking using GPT to evaluate
DocAI extracted values against CFIA checklist questions from JSON files.

Features:
- Batches all questions per attribute (one GPT call per attribute)
- Uses temperature=0 for consistent results
- Returns pass/fail/needs_review for each question
"""

import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv
load_dotenv()

from openai import OpenAI


# Path to checklist questions JSON files
CHECKLIST_QUESTIONS_DIR = Path(__file__).parent.parent / "checklist_questions"

# Attribute to JSON file mapping
ATTRIBUTE_JSON_MAP = {
    "common_name": "common_name.json",
    "net_quantity": "net_quantity_declaration.json",
    "list_of_ingredients": "list_of_ingredients.json",
}


def load_questions(attribute_name: str) -> Dict[str, Any]:
    """
    Load checklist questions for an attribute from its JSON file.
    
    Args:
        attribute_name: Name of the attribute (e.g., "common_name")
    
    Returns:
        Dictionary containing questions metadata and list
    """
    json_filename = ATTRIBUTE_JSON_MAP.get(attribute_name)
    if not json_filename:
        return {"questions": [], "error": f"No JSON mapping for attribute: {attribute_name}"}
    
    json_path = CHECKLIST_QUESTIONS_DIR / json_filename
    if not json_path.exists():
        return {"questions": [], "error": f"JSON file not found: {json_path}"}
    
    with open(json_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def build_compliance_prompt(
    attribute_name: str,
    extracted_value: Dict[str, Any],
    questions: List[Dict[str, Any]]
) -> List[Dict[str, str]]:
    """
    Build the messages for GPT compliance evaluation.
    
    Args:
        attribute_name: Name of the attribute being checked
        extracted_value: DocAI extracted field data
        questions: List of questions from JSON
    
    Returns:
        List of message dictionaries for the OpenAI API
    """
    # Extract the text value and confidence
    value_text = ""
    confidence = 0.0
    
    if isinstance(extracted_value, dict):
        value_text = extracted_value.get("text", "") or ""
        confidence = extracted_value.get("confidence", 0.0) or 0.0
    elif isinstance(extracted_value, str):
        value_text = extracted_value
    
    # Build questions list for prompt
    questions_text = ""
    for i, q in enumerate(questions, 1):
        question_text = q.get("question_text", "")
        # Include sub-questions in the main text for clarity, or handle them as separate lines
        sub_questions = q.get("sub_questions", [])
        
        q_str = f"{i}. {question_text}"
        if sub_questions:
            for sq in sub_questions:
                q_str += f" ({sq})"
        
        questions_text += f"{q_str}\n"

    system_prompt = """You are a Food Label Compliance Assistant supporting the Canadian Food Inspection Agency (CFIA).

Your responsibility is to evaluate extracted food label attributes against compliance checklist questions using only the provided text data. Your decisions must be conservative, auditable, and regulation-focused.

Allowed Results:
pass, fail, needs_review

Core Principles:
1. Assume standard Canadian food labeling requirements.
2. Do not infer or assume missing information.
3. Do not correct, rewrite, or enhance extracted text.
4. Do not reference regulations unless explicitly provided.
5. Do not output anything outside the defined JSON schema.

Decision Rules:
1. Text-Based Content Checks
   - clearly met -> pass
   - clearly unmet/missing/incorrect -> fail
   - ambiguous/incomplete -> needs_review
2. Visual / Formatting Checks
   - If requirement depends on font size, color, placement, layout, or bilingual visibility -> needs_review
3. Confidence-Aware Escalation
   - >= 85%: Definitive pass/fail if text is clear
   - 70-84%: needs_review if text is slightly unclear
   - < 70%: needs_review if precise wording matters; fail if clearly missing
4. No Assumptions
   - Missing required elements -> fail

Output JSON Format:
{
  "results": [
    {
      "question_id": <int>,
      "result": "pass | fail | needs_review",
      "rationale": "<concise justification>"
    }
  ]
}"""

    user_prompt = f"""ATTRIBUTE: {attribute_name}
EXTRACTED VALUE: "{value_text}"
EXTRACTION CONFIDENCE: {confidence:.0%}

CHECKLIST QUESTIONS:
{questions_text}"""

    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt}
    ]


def evaluate_attribute(
    attribute_name: str,
    extracted_value: Dict[str, Any],
    api_key: Optional[str] = None
) -> Dict[str, Any]:
    """
    Evaluate an attribute against its CFIA checklist questions using GPT.
    
    Args:
        attribute_name: Name of the attribute (e.g., "common_name")
        extracted_value: DocAI extracted field data
        api_key: OpenAI API key (uses env var if not provided)
    
    Returns:
        Dictionary with evaluation results:
        {
            "attribute": str,
            "extracted_value": str,
            "results": [{"question_id": int, "answer": str, "reason": str}],
            "overall_status": str,
            "error": str (if any)
        }
    """
    # Load questions from JSON
    questions_data = load_questions(attribute_name)
    questions = questions_data.get("questions", [])
    
    if not questions:
        return {
            "attribute": attribute_name,
            "extracted_value": extracted_value,
            "results": [],
            "overall_status": "needs_review",
            "error": questions_data.get("error", "No questions found")
        }
    
    # Build messages
    messages = build_compliance_prompt(attribute_name, extracted_value, questions)
    
    # Call GPT
    try:
        client = OpenAI(api_key=api_key)
        
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=messages,
            temperature=0.3, 
        )
        
        response_text = response.choices[0].message.content
        
        # Parse JSON response
        json_start = response_text.find('{')
        json_end = response_text.rfind('}') + 1
        if json_start != -1 and json_end > json_start:
            parsed = json.loads(response_text[json_start:json_end])
            
            check_results = parsed.get("results", [])
            
            # Reconstruct legacy format for compatibility (answer/reason -> result/rationale)
            # And calculate overall status
            formatted_results = []
            final_status = "pass"
            
            for r in check_results:
                q_id = r.get("question_id")
                # Handle possible key variations if model hallucinates slightly, though system prompt forbids it
                res = r.get("result") or r.get("answer") or "needs_review"
                rationale = r.get("rationale") or r.get("reason") or "No rationale provided"
                
                formatted_results.append({
                    "question_id": q_id,
                    "answer": res,
                    "reason": rationale
                })
                
                # Logic: Any Fail -> Fail. If no Fail but needs_review -> needs_review. Else Pass.
                if res == "fail":
                    final_status = "fail"
                elif res == "needs_review" and final_status != "fail":
                    final_status = "needs_review"

            return {
                "attribute": attribute_name,
                "extracted_value": extracted_value.get("text", "") if isinstance(extracted_value, dict) else str(extracted_value),
                "results": formatted_results,
                "overall_status": final_status,
                "questions_count": len(questions),
                "error": None
            }
        else:
            return {
                "attribute": attribute_name,
                "extracted_value": extracted_value,
                "results": [],
                "overall_status": "needs_review",
                "error": "Failed to parse GPT response as JSON"
            }
            
    except Exception as e:
        return {
            "attribute": attribute_name,
            "extracted_value": extracted_value,
            "results": [],
            "overall_status": "needs_review",
            "error": str(e)
        }


def evaluate_all_attributes(
    label_facts: Dict[str, Any],
    api_key: Optional[str] = None
) -> Dict[str, Any]:
    """
    Evaluate all supported attributes against their CFIA checklist questions.
    
    Args:
        label_facts: Full DocAI extraction results with "fields" dict
        api_key: OpenAI API key
    
    Returns:
        Dictionary with all evaluation results keyed by attribute name
    """
    fields = label_facts.get("fields", {}) or {}
    
    results = {}
    
    # Common name - check multiple possible field names
    common_name_value = (
        fields.get("common_name_en") or 
        fields.get("common_name_fr") or 
        fields.get("common_name") or
        {}
    )
    results["common_name"] = evaluate_attribute("common_name", common_name_value, api_key)
    
    # Net quantity
    net_quantity_value = (
        fields.get("net_quantity_full_text") or
        fields.get("net_quantity_value") or
        fields.get("net_quantity") or
        {}
    )
    results["net_quantity"] = evaluate_attribute("net_quantity", net_quantity_value, api_key)
    
    # List of ingredients
    ingredients_value = (
        fields.get("ingredients_list_en") or
        fields.get("ingredients_list_fr") or
        fields.get("ingredients_list") or
        {}
    )
    results["list_of_ingredients"] = evaluate_attribute("list_of_ingredients", ingredients_value, api_key)
    
    return results


if __name__ == "__main__":
    # Demo: test with sample data
    print("=" * 60)
    print("GPT Compliance Evaluation Demo")
    print("=" * 60)
    
    # Check for API key
    if not os.environ.get("OPENAI_API_KEY"):
        print("ERROR: OPENAI_API_KEY not set")
        exit(1)
    
    result = evaluate_attribute("common_name", sample_value)
    
    print(f"Attribute: {result['attribute']}")
    print(f"Overall Status: {result['overall_status']}")
    print(f"Results:")
    for r in result.get("results", []):
        print(f"  Q{r['question_id']}: {r['answer']} - {r['reason']}")
