"""
Net Quantity Declaration Checklist Questions Extractor for CFIA Compliance.

This module extracts checklist questions from the CFIA Food Labelling
Requirements Checklist - Net Quantity Declaration section using:
1. Web scraper to fetch exact raw text
2. ChatGPT to structure the raw text into JSON questions

Source: https://inspection.canada.ca/en/food-labels/labelling/industry/requirements-checklist

Usage:
    python checklist_questions/net_quantity_declaration.py

Output:
    checklist_questions/net_quantity_declaration_questions.json
"""

import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv
load_dotenv()

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.scraper import scrape_section
from openai import OpenAI


# CFIA Source URL
CFIA_REQUIREMENTS_CHECKLIST_URL = "https://inspection.canada.ca/en/food-labels/labelling/industry/requirements-checklist"

# Output file path
OUTPUT_DIR = Path(__file__).parent
OUTPUT_FILE = OUTPUT_DIR / "net_quantity_declaration.json"


def extract_net_quantity_questions(
    api_key: Optional[str] = None,
    save_to_file: bool = True
) -> Dict[str, Any]:
    """
    Extract Net Quantity Declaration checklist questions from CFIA website.
    
    Uses a two-step process:
    1. Scrape the raw section text from the CFIA page
    2. Use ChatGPT to structure the raw text into JSON questions
    
    Args:
        api_key: OpenAI API key (uses OPENAI_API_KEY env var if not provided)
        save_to_file: If True, saves the result to JSON file
    
    Returns:
        Dictionary containing extracted questions and metadata
    """
    print("=" * 60)
    print("CFIA Net Quantity Declaration Checklist Questions Extractor")
    print("=" * 60)
    print(f"Source: {CFIA_REQUIREMENTS_CHECKLIST_URL}")
    print(f"Section: Net Quantity Declaration")
    print("-" * 60)
    
    # Step 1: Scrape the raw section text
    print("Step 1: Scraping raw section text...")
    raw_text = scrape_section("Net quantity declaration", "List of ingredients")
    print(f"✓ Scraped {len(raw_text)} characters")
    
    # Step 2: Use ChatGPT to structure the data
    print("Step 2: Structuring data with ChatGPT...")
    
    client = OpenAI(api_key=api_key)
    
    prompt = f"""
Below is the raw text scraped from the CFIA Food Labelling Requirements Checklist - Net Quantity Declaration section.

The text uses bullet markers:
• = main question
◦ = sub-question (nested under the main question)

RAW TEXT:
---
{raw_text}
---

INSTRUCTIONS:
1. Each line starting with • is a MAIN question
2. Each line starting with ◦ is a SUB-QUESTION that belongs to the previous main question
3. For question_text, include ONLY the main question text (up to the first ◦ or the next •)
4. Do NOT repeat sub-question text in the question_text field
5. Preserve exact wording including measurements and parenthetical notes

Return ONLY valid JSON in this format:
{{
    "questions": [
        {{
            "question_text": "main question only - do not include sub-questions here",
            "sub_questions": ["each nested ◦ item as a separate string"]
        }}
    ]
}}
"""

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {
                "role": "system",
                "content": "You are a precise text parser. Extract questions from the given text exactly as written. Output only valid JSON."
            },
            {
                "role": "user",
                "content": prompt
            }
        ],
        temperature=0,
    )
    
    response_text = response.choices[0].message.content
    
    # Parse the JSON response
    output = {
        "metadata": {
            "source_url": CFIA_REQUIREMENTS_CHECKLIST_URL,
            "section": "Net Quantity Declaration",
            "extracted_at": datetime.now().isoformat(),
            "raw_text_length": len(raw_text),
        },
        "questions": [],
        "raw_scraped_text": raw_text,
        "error": None
    }
    
    try:
        # Extract JSON from response
        json_start = response_text.find('{')
        json_end = response_text.rfind('}') + 1
        if json_start != -1 and json_end > json_start:
            json_str = response_text[json_start:json_end]
            parsed = json.loads(json_str)
            output["questions"] = parsed.get("questions", [])
    except json.JSONDecodeError as e:
        output["error"] = f"JSON parse error: {str(e)}"
        output["raw_response"] = response_text
    
    # Print summary
    print("-" * 60)
    if output["error"]:
        print(f" Error: {output['error']}")
    else:
        print(f"✓ Extracted {len(output['questions'])} question(s)")
    
    # Save to file
    if save_to_file:
        with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
            json.dump(output, f, indent=2, ensure_ascii=False)
        print(f"✓ Saved to: {OUTPUT_FILE}")
    
    print("=" * 60)
    
    return output


def load_questions_from_json() -> Dict[str, Any]:
    """
    Load previously extracted questions from JSON file.
    
    Returns:
        Dictionary containing questions, or empty dict if file doesn't exist
    """
    if OUTPUT_FILE.exists():
        with open(OUTPUT_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}


def get_questions() -> List[Dict[str, Any]]:
    """
    Get Net Quantity questions - loads from JSON if available, otherwise extracts fresh.
    
    Returns:
        List of question dictionaries
    """
    data = load_questions_from_json()
    if data and data.get("questions"):
        return data["questions"]
    
    # If no cached data, extract fresh
    print("No cached questions found. Extracting from CFIA website...")
    result = extract_net_quantity_questions(save_to_file=True)
    return result.get("questions", [])


def build_compliance_queries(questions: Optional[List[Dict]] = None) -> Dict[str, str]:
    """
    Build query dictionary for compliance checks.
    
    Args:
        questions: List of question dicts. If None, loads from JSON.
    
    Returns:
        Dictionary with question index as key and query text as value.
    """
    if questions is None:
        questions = get_questions()
    
    queries = {}
    for i, q in enumerate(questions):
        query_key = f"NQ_{i+1:03d}"
        query_text = q.get("question_text", "")
        
        sub_qs = q.get("sub_questions", [])
        if sub_qs:
            query_text += " " + " ".join(sub_qs)
        
        queries[query_key] = query_text
    
    return queries


if __name__ == "__main__":
    # Check for API key
    if not os.environ.get("OPENAI_API_KEY"):
        print("ERROR: OPENAI_API_KEY environment variable not set")
        print("Please set it before running this script:")
        print("  $env:OPENAI_API_KEY='your-api-key-here'")
        sys.exit(1)
    
    # Extract questions from CFIA website
    result = extract_net_quantity_questions()
    
    # Display extracted questions
    print("\nExtracted Questions:")
    print("-" * 40)
    for i, q in enumerate(result.get("questions", []), 1):
        print(f"\n{i}. {q.get('question_text', 'N/A')}")
        sub_qs = q.get('sub_questions', [])
        if sub_qs:
            for sq in sub_qs:
                print(f"   → {sq}")
