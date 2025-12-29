"""
Nutrition Attribute LLM Classifier
Step 3: Classify cleaned content into structured rules vs unstructured content.

Uses GPT-4o-mini to analyze clean_text and output:
  - structured_checklist.json   → Rules with thresholds, conditions, if-then logic
  - unstructured_checklist.json → Explanatory content, examples, rationale

Input: nutrition_cleaned_data.json (clean_text attribute)
Output: structured_checklist.json, unstructured_checklist.json
"""

import json
import os
from pathlib import Path
from typing import List, Dict, Tuple
from dataclasses import dataclass, asdict
from dotenv import load_dotenv
from openai import OpenAI

# Load environment variables
load_dotenv()

# ============================================================================
# CONFIGURATION
# ============================================================================

SCRIPT_DIR = Path(__file__).parent
INPUT_FILE = SCRIPT_DIR / "nutrition_cleaned_data.json"
STRUCTURED_OUTPUT = SCRIPT_DIR / "structured_checklist.json"
UNSTRUCTURED_OUTPUT = SCRIPT_DIR / "unstructured_checklist.json"

MODEL = "gpt-4o-mini"


# ============================================================================
# PROMPTS
# ============================================================================

CLASSIFICATION_SYSTEM_PROMPT = """You are a regulatory content classifier for Canadian food labeling rules.

Your task is to analyze text from Health Canada's front-of-package nutrition symbol guidance and classify each distinct rule or piece of information into one of two categories:

**STRUCTURED** - Content that can be turned into programmatic rules:
- Specific thresholds (e.g., "≥ 15% DV")
- Conditions with clear triggers (e.g., "if reference amount ≤ 30g")
- Lists of exempt or prohibited foods
- Yes/No determinations based on criteria
- Quantitative limits (e.g., "< 30% saturated fat")

**UNSTRUCTURED** - Content that is explanatory or contextual:
- Background information and rationale
- Examples illustrating rules
- General descriptions without specific thresholds
- Historical context or policy reasoning
- Definitions without actionable criteria

For each piece of content, extract and classify it."""

CLASSIFICATION_USER_PROMPT = """Analyze the following regulatory text and extract all distinct rules and content pieces.

For each item, provide:
1. A unique rule_id (snake_case, descriptive)
2. Classification: "structured" or "unstructured"
3. The content summary
4. For STRUCTURED rules, also extract:
   - nutrient (if applicable): saturated_fat, sugars, sodium, or null
   - threshold (if applicable): numeric value
   - unit (if applicable): percent_dv, grams, mg, etc.
   - condition: the triggering condition
   - action: what happens when condition is met

Return as JSON with two arrays: "structured" and "unstructured"

Example output format:
{{
  "structured": [
    {{
      "rule_id": "fop_satfat_threshold_default",
      "nutrient": "saturated_fat",
      "threshold": 15,
      "unit": "percent_dv",
      "condition": "reference amount > 30g or 30mL, not main dish",
      "action": "show_fop_symbol",
      "source_text": "≥ 15% DV triggers the FOP symbol for..."
    }}
  ],
  "unstructured": [
    {{
      "rule_id": "fop_background_dv_explanation",
      "category": "explanation",
      "summary": "Daily Values are the basis for FOP thresholds...",
      "source_text": "The thresholds for the FOP nutrition symbol are based on Daily Values..."
    }}
  ]
}}

TEXT TO ANALYZE:
---
{text}
---

Return ONLY valid JSON, no markdown formatting."""


# ============================================================================
# DATA CLASSES
# ============================================================================

@dataclass
class StructuredRule:
    """A structured rule that can be programmatically evaluated."""
    rule_id: str
    nutrient: str = None
    threshold: float = None
    unit: str = None
    condition: str = None
    action: str = None
    source_text: str = None


@dataclass 
class UnstructuredContent:
    """Unstructured content for RAG retrieval."""
    rule_id: str
    category: str  # explanation, example, definition, context
    summary: str
    source_text: str


# ============================================================================
# CLASSIFIER
# ============================================================================

def classify_content(client: OpenAI, text: str) -> Tuple[List[Dict], List[Dict]]:
    """
    Use GPT-4o-mini to classify content as structured or unstructured.
    
    Args:
        client: OpenAI client
        text: Clean text to classify
        
    Returns:
        Tuple of (structured_rules, unstructured_content)
    """
    print(f"   Sending {len(text):,} chars to {MODEL}...")
    
    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": CLASSIFICATION_SYSTEM_PROMPT},
            {"role": "user", "content": CLASSIFICATION_USER_PROMPT.format(text=text)}
        ],
        temperature=0.1,  # Low for consistency
        max_tokens=4096,
        response_format={"type": "json_object"}
    )
    
    result_text = response.choices[0].message.content
    result = json.loads(result_text)
    
    structured = result.get("structured", [])
    unstructured = result.get("unstructured", [])
    
    print(f"   Found {len(structured)} structured rules, {len(unstructured)} unstructured items")
    
    return structured, unstructured


def run_classifier(input_file: str = None, structured_output: str = None, 
                   unstructured_output: str = None) -> Dict:
    """
    Main classification pipeline.
    
    Args:
        input_file: Path to cleaned data JSON
        structured_output: Path for structured rules output
        unstructured_output: Path for unstructured content output
        
    Returns:
        Statistics about the classification
    """
    input_file = input_file or str(INPUT_FILE)
    structured_output = structured_output or str(STRUCTURED_OUTPUT)
    unstructured_output = unstructured_output or str(UNSTRUCTURED_OUTPUT)
    
    print("=" * 60)
    print("NUTRITION ATTRIBUTE LLM CLASSIFIER")
    print("=" * 60)
    print(f"\n📂 Input:  {input_file}")
    print(f"   Model:  {MODEL}")
    
    # Check API key
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("\n❌ OPENAI_API_KEY not found in environment")
        print("   Set it in your .env file")
        return {"error": "Missing API key"}
    
    # Initialize client
    client = OpenAI(api_key=api_key)
    
    # Load cleaned data
    with open(input_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    pages = data.get("pages", [])
    print(f"\n   Found {len(pages)} pages to classify")
    
    # Classify each page
    all_structured = []
    all_unstructured = []
    
    for i, page in enumerate(pages):
        url = page.get("url", "")
        clean_text = page.get("clean_text", "")
        
        if not clean_text:
            continue
            
        print(f"\n   [{i+1}/{len(pages)}] Classifying: {url[:50]}...")
        
        try:
            structured, unstructured = classify_content(client, clean_text)
            
            # Add source URL to each item
            for item in structured:
                item["source_url"] = url
            for item in unstructured:
                item["source_url"] = url
                
            all_structured.extend(structured)
            all_unstructured.extend(unstructured)
            
        except Exception as e:
            print(f"   ❌ Error: {e}")
            continue
    
    # Save outputs
    structured_data = {
        "source_file": input_file,
        "model": MODEL,
        "total_rules": len(all_structured),
        "rules": all_structured
    }
    
    unstructured_data = {
        "source_file": input_file,
        "model": MODEL,
        "total_items": len(all_unstructured),
        "items": all_unstructured
    }
    
    with open(structured_output, 'w', encoding='utf-8') as f:
        json.dump(structured_data, f, indent=2, ensure_ascii=False)
    
    with open(unstructured_output, 'w', encoding='utf-8') as f:
        json.dump(unstructured_data, f, indent=2, ensure_ascii=False)
    
    # Summary
    print(f"\n" + "=" * 60)
    print("CLASSIFICATION COMPLETE")
    print("=" * 60)
    print(f"   Structured rules:     {len(all_structured)}")
    print(f"   Unstructured content: {len(all_unstructured)}")
    print(f"\n✅ Saved to:")
    print(f"   {structured_output}")
    print(f"   {unstructured_output}")
    
    return {
        "structured_count": len(all_structured),
        "unstructured_count": len(all_unstructured)
    }


def main():
    """Main entry point."""
    if not INPUT_FILE.exists():
        print(f"❌ Input file not found: {INPUT_FILE}")
        print("   Run nutrition_attribute_clean.py first.")
        return
    
    run_classifier()
    print(f"\nNext step: Run chunk_data.py to split content for embedding")


if __name__ == "__main__":
    main()
