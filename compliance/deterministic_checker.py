"""
Deterministic Compliance Checker

Handles simple rule-based compliance checks without LLM calls.
Used for presence checks, location checks, and format validation.
"""

import re
from typing import Dict, Any, Optional


class DeterministicChecker:
    """
    Evaluates deterministic compliance questions using Python logic.
    
    Supports:
    - field_exists: Check if a field has a value
    - in_panel: Check if value appears in a specific panel
    - regex: Pattern matching
    - always_needs_review: Visual checks that require human inspection
    """
    
    def check(self, question: Dict[str, Any], label_facts: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Evaluate a deterministic question.
        
        Args:
            question: Question dict with 'logic', 'field', etc.
            label_facts: DocAI extracted data
        
        Returns:
            Result dict with question_id, result, rationale, etc.
            Returns None if question cannot be handled deterministically.
        """
        logic = question.get("logic")
        
        if not logic:
            return None
        
        if logic == "field_exists":
            return self._check_field_exists(question, label_facts)
        
        if logic == "in_panel":
            return self._check_in_panel(question, label_facts)
        
        if logic == "regex":
            return self._check_regex(question, label_facts)
        
        if logic == "always_needs_review":
            return self._always_needs_review(question)
        
        # Unknown logic type - fallback to LLM
        return None
    
    def _check_field_exists(self, question: Dict[str, Any], label_facts: Dict[str, Any]) -> Dict[str, Any]:
        """Check if a field exists and has a value."""
        field = question.get("field")
        value = self._get_field(label_facts, field)
        
        # Handle list values (e.g., from fields_all)
        if isinstance(value, list):
            value = value[0] if value else None
        
        return {
            "question_id": question["id"],
            "question": question["text"],
            "result": "pass" if value else "fail",
            "selected_value": str(value) if value else "Not found",
            "rationale": f"Field '{field}' {'found' if value else 'not found'} in extracted data."
        }
    
    def _check_in_panel(self, question: Dict[str, Any], label_facts: Dict[str, Any]) -> Dict[str, Any]:
        """Check if a value appears in a specific panel."""
        field = question.get("field")
        panel_key = question.get("panel", "panel_pdp")  # Default to PDP
        
        value = self._get_field(label_facts, field)
        if isinstance(value, list):
            value = value[0] if value else None
        
        panel_text = label_facts.get("panels", {}).get(panel_key, {}).get("text", "")
        
        if not value:
            return {
                "question_id": question["id"],
                "question": question["text"],
                "result": "fail",
                "rationale": f"Field '{field}' not found in extracted data."
            }
        
        found = value.lower() in panel_text.lower()
        
        return {
            "question_id": question["id"],
            "question": question["text"],
            "result": "pass" if found else "fail",
            "selected_value": str(value),
            "rationale": f"'{value}' {'found' if found else 'not found'} in {panel_key}."
        }
    
    def _check_regex(self, question: Dict[str, Any], label_facts: Dict[str, Any]) -> Dict[str, Any]:
        """Check if a value matches a regex pattern."""
        field = question.get("field")
        pattern = question.get("pattern", "")
        
        value = self._get_field(label_facts, field)
        if isinstance(value, list):
            value = value[0] if value else None
        
        if not value:
            return {
                "question_id": question["id"],
                "question": question["text"],
                "result": "fail",
                "rationale": f"Field '{field}' not found."
            }
        
        match = re.search(pattern, str(value), re.IGNORECASE)
        
        return {
            "question_id": question["id"],
            "question": question["text"],
            "result": "pass" if match else "fail",
            "selected_value": str(value),
            "rationale": f"Pattern '{pattern}' {'matched' if match else 'did not match'} value '{value}'."
        }
    
    def _always_needs_review(self, question: Dict[str, Any]) -> Dict[str, Any]:
        """Return needs_review for visual/physical inspection questions."""
        return {
            "question_id": question["id"],
            "question": question["text"],
            "result": "needs_review",
            "rationale": "Requires physical inspection or visual verification."
        }
    
    def _get_field(self, label_facts, field):
        # Try fields first
        value = label_facts.get("fields", {}).get(field)
        if value:
            if isinstance(value, dict):
                return value.get("text", "")
            return value
        
        # Try fields_all
        all_candidates = label_facts.get("fields_all", {}).get(field, [])
        if all_candidates:
            first = all_candidates[0]
            if isinstance(first, dict):
                return first.get("text", "")
            return first
        
        return None
