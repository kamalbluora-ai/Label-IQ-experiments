from typing import Dict, Any, List
from compliance.base_agent import BaseComplianceAgent
from compliance.claim_tags.claim_tag_models import ClaimTagResult, ClaimTagEvaluation
import json

class ClaimTagAgent(BaseComplianceAgent):
    """
    Agent for evaluating claim tags (Nature/Natural, Kosher, Halal, Homemade/Artisan Made, Organic).
    """
    def __init__(self):
        super().__init__(section_name="Claim Tags")
    
    def get_section_context(self) -> str:
        """Required by BaseComplianceAgent."""
        return "Evaluate food labeling claim tags against Canadian food labeling standards."
    
    def prepare_input_data(self, label_facts: Dict[str, Any]) -> Dict[str, Any]:
        """Extract the 3 required fields from DocAI output."""
        fields = label_facts.get("fields", {})
        return {
            "claim_tag_type": fields.get("claim_tag_type", {}).get("text", ""),
            "ingredients_list_en": fields.get("ingredients_list_en", {}).get("text", ""),
            "nft_table_en": fields.get("nft_table_en", {}).get("text", ""),
        }
    
    def build_prompt(self, data: Dict[str, Any]) -> str:
        """Build the evaluation prompt with the 3 DocAI fields."""
        return f"""You are a Canadian food labeling compliance evaluator.

FIELDS PROVIDED:
1. claim_tag_type: {data.get('claim_tag_type', 'None')}
2. ingredients_list_en: {data.get('ingredients_list_en', 'Not available')}
3. nft_table_en: {data.get('nft_table_en', 'Not available')}

RULES PER CLAIM TYPE:
- Nature/Natural: Must NOT contain artificial additives, vitamins, minerals, or undergo maximum processing (hydrogenated oils, chemical extraction). Natural flavors ARE allowed.
- Kosher: Must have Rabbi/Rabbinical certification. "Kosher style" also requires full certification.
- Halal: Must have certifying body NAME on label (logo alone is insufficient).
- Homemade/Artisan Made: "Homemade" cannot be used for commercial products (only "Homemade style"). Artisan requires household-level additives only (vinegar, salt, sugar).
- Organic: Greater than 95% can use "Organic" + logo. 70 to 95% can state percentage only. Less than 70% can only list organic ingredients in ingredient list. Certification body required for greater than 70%.

TASK:
Using the claim_tag_type field, identify which claim(s) are present. Then evaluate them against the ingredients_list_en and nft_table_en using the rules above. ALL results must have status "NEEDS_REVIEW".

Return JSON:
{{
  "claims_detected": [
    {{
      "claim_type": "string",
      "claim_text_found": "string",
      "certification_body": "string or null",
      "status": "NEEDS_REVIEW",
      "ai_reason": "string",
      "rule_violations": ["string"],
      "supporting_evidence": ["string"]
    }}
  ],
  "summary": "Brief overall summary"
}}"""
    
    async def evaluate(
        self, 
        label_facts: Dict[str, Any],
        questions: List[Dict[str, Any]] = None,
        user_context: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Evaluate claim tags.
        """
        try:
            # Prepare data
            data = self.prepare_input_data(label_facts)
            
            # Build specialized prompt
            prompt = self.build_prompt(data)
            
            # Call LLM
            response = self.client.models.generate_content(
                model="gemini-2.0-flash-exp",
                contents=prompt,
                config={
                    "response_mime_type": "application/json",
                    "thinking_config": {"thinking_level": "high"}
                }
            )
            
            # Parse response
            result = json.loads(response.text)
            
            # Validate with Pydantic
            evaluation = ClaimTagEvaluation(
                claims_detected=[ClaimTagResult(**claim) for claim in result.get("claims_detected", [])],
                summary=result.get("summary", "No claims evaluated")
            )
            
            # Transform to match orchestrator expected format
            return {
                "section": self.section_name,
                "results": [
                    {
                        "question_id": f"claim_tag_{i}",
                        "question": f"Claim: {claim.claim_type}",
                        "result": "needs_review",
                        "selected_value": claim.claim_text_found,
                        "rationale": claim.ai_reason,
                        "metadata": {
                            "claim_type": claim.claim_type,
                            "certification_body": claim.certification_body,
                            "rule_violations": claim.rule_violations,
                            "supporting_evidence": claim.supporting_evidence
                        }
                    }
                    for i, claim in enumerate(evaluation.claims_detected)
                ],
                "summary": evaluation.summary
            }
            
        except Exception as e:
            # Graceful fallback
            return {
                "section": self.section_name,
                "error": str(e),
                "results": [
                    {
                        "question_id": "claim_tag_error",
                        "question": "Claim Tag Evaluation",
                        "result": "needs_review",
                        "rationale": f"Agent error: {str(e)}"
                    }
                ]
            }