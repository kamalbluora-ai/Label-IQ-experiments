import json
from typing import Dict, Any
from compliance.agents.common_name import CommonNameAgent
from compliance.agents.date_marking import DateMarkingAgent
from compliance.agents.ingredients import IngredientsAgent
from compliance.agents.country_origin import CountryOriginAgent
from compliance.agents.bilingual import BilingualAgent
from compliance.agents.irradiation import IrradiationAgent
from compliance.agents.fop_symbol import FOPSymbolAgent


async def reevaluate_question(
    question_id: str,
    question: str,
    original_answer: str,
    original_tag: str,
    original_rationale: str,
    user_comment: str
) -> Dict[str, Any]:
    """
    Re-evaluate a single compliance question with user feedback.
    """
    # Determine which agent to use based on question_id prefix from questions.json
    if question_id.startswith("CN-"):
        agent = CommonNameAgent()
    elif question_id.startswith("DM-"):
        agent = DateMarkingAgent()
    elif question_id.startswith("LI-"):
        agent = IngredientsAgent() 
    elif question_id.startswith("CO-"):
        agent = CountryOriginAgent()
    elif question_id.startswith("BR-"):
        agent = BilingualAgent()
    elif question_id.startswith("IR-"):
        agent = IrradiationAgent()
    elif question_id.startswith("FOP-"):
        agent = FOPSymbolAgent()
    else:
        # Tables are not supported for re-evaluation via agents
        raise ValueError(f"Unsupported question type or ID prefix: {question_id}")
    
    # Create a synthetic question with re-evaluation context
    reevaluation_question = {
        "question_id": question_id,
        "question": question,
        "type": "reevaluation"
    }
    
    # Build context that includes previous evaluation + user comment
    user_context = {
        "reevaluation_mode": True,
        "previous_evaluation": {
            "answer": original_answer,
            "tag": original_tag,
            "rationale": original_rationale
        },
        "user_comment": user_comment
    }
    
    # Run evaluation with re-evaluation context
    # Note: label_facts is empty since we're using previous data
    result = await agent.evaluate(
        label_facts={},
        questions=[reevaluation_question],
        user_context=user_context
    )
    
    # Extract the re-evaluated result
    if result and "check_results" in result and len(result["check_results"]) > 0:
        check = result["check_results"][0]
        return {
            "question_id": question_id,
            "new_tag": check["result"],
            "new_rationale": check["rationale"]
        }
    
    # Fallback if evaluation fails
    return {
        "question_id": question_id,
        "new_tag": original_tag,
        "new_rationale": f"Re-evaluation failed. Original: {original_rationale}"
    }
