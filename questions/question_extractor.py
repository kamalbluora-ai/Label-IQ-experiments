"""
CFIA Question Extractor

Uses LLM to extract structured questions from the crawled CFIA checklist markdown.
This is step 2 of Pipeline 1: Question Extraction.

Usage:
    python question_extractor.py

Input:
    - cfia_checklist.md: Raw markdown from crawler

Output:
    - questions.json: Structured questions grouped by section
"""

import json
from pathlib import Path
from datetime import datetime
from openai import OpenAI
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Paths
QUESTIONS_DIR = Path(__file__).parent
INPUT_FILE = QUESTIONS_DIR / "cfia_checklist.md"
OUTPUT_FILE = QUESTIONS_DIR / "questions.json"

# LLM extraction prompt
EXTRACTION_PROMPT = """You are a regulatory document parser. Extract ALL compliance checklist questions from the CFIA (Canadian Food Inspection Agency) requirements checklist content below.

INSTRUCTIONS:
1. Identify each section (Common Name, Net Quantity, List of Ingredients, etc.)
2. For each section, extract ALL questions and sub-questions
3. Preserve the hierarchy (main questions and their sub-questions)
4. Include the exact question text as it appears
5. Use snake_case for section keys

OUTPUT FORMAT (JSON):
{
  "metadata": {
    "source": "CFIA Requirements Checklist",
    "extracted_at": "<timestamp>",
    "total_sections": <number>,
    "total_questions": <number>
  },
  "sections": {
    "common_name": {
      "title": "Common Name",
      "questions": [
        {
          "id": "CN-1",
          "text": "is a common name present?",
          "sub_questions": [
            "if not, is the product exempt from common name?"
          ]
        }
      ]
    },
    "net_quantity": {
      "title": "Net Quantity Declaration",
      "questions": [...]
    },
    "list_of_ingredients": {...},
    "name_and_address": {...},
    "date_markings": {...},
    "nutrition_facts_table": {...},
    "fop_nutrition_symbol": {...},
    "bilingual_requirements": {...},
    "irradiation": {...},
    "sweeteners": {...},
    "country_of_origin": {...}
  }
}

IMPORTANT:
- Extract EVERY question, do not summarize or skip any
- Keep sub-questions nested under their parent question
- Use lowercase for question text
- Generate unique IDs (CN-1, CN-2, NQ-1, etc.)

CFIA CHECKLIST CONTENT:
"""


def load_markdown(filepath: Path) -> str:
    """Load markdown content from file."""
    if not filepath.exists():
        raise FileNotFoundError(
            f"Input file not found: {filepath}\n"
            f"Please run cfia_crawler.py first."
        )
    
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()
    
    # Remove YAML frontmatter if present
    if content.startswith("---"):
        parts = content.split("---", 2)
        if len(parts) >= 3:
            content = parts[2].strip()
    
    return content


def extract_questions_with_llm(markdown_content: str) -> dict:
    """Use LLM to extract structured questions from markdown."""
    
    client = OpenAI()
    
    print("Calling LLM to extract questions...")
    
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {
                "role": "system",
                "content": "You are a precise document parser. Return only valid JSON."
            },
            {
                "role": "user", 
                "content": EXTRACTION_PROMPT + markdown_content
            }
        ],
        response_format={"type": "json_object"},
        temperature=0.1  # Low temperature for consistency
    )
    
    result = json.loads(response.choices[0].message.content)
    
    # Add extraction timestamp
    result["metadata"]["extracted_at"] = datetime.now().isoformat()
    
    return result


def save_questions(questions: dict, filepath: Path) -> None:
    """Save questions to JSON file."""
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(questions, f, indent=2, ensure_ascii=False)
    
    print(f"Saved to: {filepath}")


def print_summary(questions: dict) -> None:
    """Print extraction summary."""
    sections = questions.get("sections", {})
    
    print("\n" + "=" * 60)
    print("EXTRACTION SUMMARY")
    print("=" * 60)
    
    total_questions = 0
    for section_key, section_data in sections.items():
        q_count = len(section_data.get("questions", []))
        total_questions += q_count
        print(f"  {section_data.get('title', section_key)}: {q_count} questions")
    
    print("-" * 60)
    print(f"  TOTAL: {len(sections)} sections, {total_questions} questions")
    print("=" * 60)


def main():
    """Main function: Load markdown, extract questions, save JSON."""
    
    print("=" * 60)
    print("CFIA Question Extractor")
    print("=" * 60)
    
    # Load markdown
    print(f"\nLoading: {INPUT_FILE}")
    markdown_content = load_markdown(INPUT_FILE)
    print(f"Loaded {len(markdown_content)} characters")
    
    # Extract questions
    questions = extract_questions_with_llm(markdown_content)
    
    # Save
    save_questions(questions, OUTPUT_FILE)
    
    # Summary
    print_summary(questions)
    
    print("\nPipeline 1 complete!")
    print(f"Output: {OUTPUT_FILE}")
    print("\nPlease review questions.json before proceeding to Agents 2, 3, 4.")


if __name__ == "__main__":
    main()
