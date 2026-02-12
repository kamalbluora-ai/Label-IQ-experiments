from typing import Dict, Any, List
from compliance.base_agent import BaseComplianceAgent
from compliance.health_claims.detector import detect_health_claims

class HealthNutrientClaimsAgent(BaseComplianceAgent):
    """
    Agent for detecting health and nutrient content claims.
    Uses deterministic matching against a database of allowed claims.
    Reference: canadian_health_nutrient_claims_extraction.md
    """
    
    def get_section_context(self) -> str:
        return "Evaluate health and nutrient content claims"

    def prepare_input_data(self, label_facts: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract relevant fields for health claim detection.
        """
        fields = label_facts.get("fields", {})
        
        # Helper to safely get text from field dict
        def get_text(field_name: str) -> str:
            val = fields.get(field_name)
            if isinstance(val, dict):
                return val.get("text", "") or ""
            return str(val) if val else ""

        return {
            "health_claims_text": get_text("health_claims"),
            "nutrient_content_text": get_text("nutrient_content_claims"),
            "nutrient_function_text": get_text("nutrient_function_claims"),
            "label_text": label_facts.get("text", "")  # Fallback to full text
        }

    async def evaluate(
        self, 
        label_facts: Dict[str, Any],
        questions: List[Dict[str, Any]],
        user_context: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Evaluate health claims using deterministic matching.
        Bypasses LLM for now as requested.
        """
        # 1. Prepare data
        data = self.prepare_input_data(label_facts)
        
        # 2. Run detection logic
        detection_result = detect_health_claims(
            health_claims_text=data["health_claims_text"],
            nutrient_content_text=data["nutrient_content_text"],
            nutrient_function_text=data["nutrient_function_text"],
            label_text=data["label_text"]
        )
        
        # 3. Format results
        results = []
        
        if not detection_result.has_health_claims:
            # If no claims detected, we can either return nothing or a "pass" result
            # For now, let's return an info result saying no claims found, 
            # or just empty list if that's preferred by frontend.
            # Usually agents return a list of findings.
            return {
                "section": self.section_name,
                "results": []
            }

        seen_claims = set()
        
        for claim in detection_result.detected:
            # Avoid duplicates if multiple variations matched same category/phrase
            claim_id = f"{claim.category}:{claim.name}"
            if claim_id in seen_claims:
                continue
            seen_claims.add(claim_id)
            
            results.append({
                "question_id": f"claim_{len(results)+1}",
                "question": f"Health/Nutrient Claim Detected: {claim.category}",
                "result": "pass", # It's a "pass" in the sense that we found it and key is present. 
                                # Or should it be "needs_review"? 
                                # The user said "We point it to the user. That's it."
                                # "pass" usually implies compliance. 
                                # If the claim is present, is it compliant? 
                                # The logic checks against *allowed* claims. 
                                # So if it's found, it is likely compliant (or at least a valid claim type).
                                # Let's mark as "pass" with the detected text.
                "selected_value": claim.name,
                "rationale": f"Detected valid {claim.claim_type} claim in {claim.source}: '{claim.name}' matched category '{claim.category}'."
            })
            
        return {
            "section": self.section_name,
            "results": results
        }
