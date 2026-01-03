#!/usr/bin/env python3
"""
Test runner for chatgpt_search2.py — run multiple key/value queries and view structured results.
"""

import os
import sys
import json
import uuid
from datetime import datetime
from typing import Dict

# Ensure app package is importable
sys.path.insert(0, os.path.dirname(__file__))

from app.chatgpt_search2 import execute_queries, format_results_text, format_results_json, get_allowed_sources_env


DEFAULT_QUERIES: Dict[str, str] = {
    "allergens": "What are CFIA requirements for allergen labeling on prepackaged foods?",
    "bilingual": "What are CFIA bilingual labeling requirements for consumer prepackaged foods?",
    "nutrition": "What CFIA requirements exist for the nutrition facts table formatting and content?",
}

MY_QUERIES: Dict[str, str] = {
    # "CFIA_RULES_COMMON_NAME": "What are CFIA requirements for common name on prepackaged foods?",
    "CFIA_RULES_COMMON_NAME_ALL": "Retreive all rules comprehensively from CFIA checklist or from the included source as applicable to common name requirements in a structured bulleted list",
    # "CFIA_RULES_BILINGUAL": "What are CFIA bilingual labeling requirements for consumer prepackaged foods?",
    # "CFIA_RULES_COUNTRY_OF_ORIGIN": "What CFIA requirements exist for the country of origin on prepackaged foods?",
    # "CFIA_RULES_DATE_MARKING_STORAGE": "What are the CFIA date marking and storage requirements for prepackaged foods?",
    # "CFIA_RULES_NAME_PRINCIPLE_PLACE_OF_BUSINESS": "What are the CFIA requirements for name and principal place of business on prepackaged foods?",
    # "CFIA_RULES_IRRADIATED_FOODS": "What are the CFIA requirements for labeling of irradiated foods?",
    # "CFIA_RULES_LEGIBILITY_LOCATION": "What are the CFIA legibility and location requirements for prepackaged foods?",
    # "CFIA_RULES_LIST_OF_INGREDIENTS_ALLERGENS": "What are the CFIA ingredient list and allergens requirements for prepackaged foods?",
    # "CFIA_RULES_NET_QUANTITY": "What are the CFIA net quantity declaration requirements for prepackaged foods?",
    # "CFIA_RULES_NUTRITION_FACTS": "What are the CFIA nutrition facts table requirements for prepackaged foods?",
    # "CFIA_RULES_SWEETENERS": "What are the CFIA sweeteners and aspartame labeling requirements for prepackaged foods?",
    # "CFIA_RULES_FOOD_ADDITIVES": "What are the CFIA food additives labeling requirements for prepackaged foods?",
    # "CFIA_RULES_FORTIFICATION": "What are the CFIA fortification labeling requirements for prepackaged foods?",
    # "CFIA_RULES_GRADES": "What are the CFIA grades labeling requirements for prepackaged foods?"
}

def main():
    if not os.environ.get("OPENAI_API_KEY"):
        print("WARNING: OPENAI_API_KEY not set — API calls will fail if not provided.")

    # Optional: load queries from a JSON file provided as first arg
    queries = MY_QUERIES
    if len(sys.argv) > 1:
        qpath = sys.argv[1]
        try:
            with open(qpath, "r", encoding="utf-8") as f:
                queries = json.load(f)
            if not isinstance(queries, dict):
                print("Query file must contain a JSON object of key: query_text pairs. Using defaults.")
                queries = DEFAULT_QUERIES
        except Exception as e:
            print(f"Failed to load {qpath}: {e}. Using default queries.")

    # context = "Product: Organic Maple Syrup; Country: Canada"
    context = "Product: Granola Bar; Country: Canada"
    allowed_sources = get_allowed_sources_env()

    print("Running queries:\n")
    for k, v in queries.items():
        print(f" - {k}: {v}")

    results = execute_queries(queries=queries, context=context, allowed_sources=allowed_sources)

    print("\nHuman-readable output:\n")
    print(format_results_text(results))

    print("\nStructured JSON output:\n")
    print(format_results_json(results))

    # Optionally save JSON to a unique file per run (UTC timestamp + short uuid)
    out_path = f"chatgpt_search2_results_{datetime.utcnow().strftime('%Y%m%dT%H%M%SZ')}_{uuid.uuid4().hex[:8]}.json"
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(format_results_json(results))
    print(f"\nSaved structured JSON to {out_path}")


if __name__ == "__main__":
    main()
